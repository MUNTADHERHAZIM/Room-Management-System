import json
import openpyxl
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.db import transaction

from apps.core.decorators import editor_required, permission_required
from apps.core.models import College, Department
from apps.rooms.models import Room
from apps.subjects.models import Subject

from .models import (
    Student, ExamSession, ExamSessionSubject,
    HallSetup, SeatingAssignment
)
from .forms import (
    StudentForm, StudentImportForm, ExamSessionForm,
    HallSetupForm, AddSubjectToSessionForm, AddStudentsToSubjectForm,
    SUBJECT_COLORS
)
from .algorithm import smart_distribute, column_department_distribute


# ──────────────────────────────────────────────
# إدارة الطلاب
# ──────────────────────────────────────────────

@login_required
@permission_required('can_access_exams')
def student_list(request):
    """عرض قائمة الطلاب"""
    students = Student.objects.select_related('department', 'department__college').filter(is_active=True)

    # فلاتر
    department_id = request.GET.get('department')
    stage = request.GET.get('stage')
    search = request.GET.get('q', '')

    if department_id:
        students = students.filter(department_id=department_id)
    if stage:
        students = students.filter(stage=stage)
    if search:
        students = students.filter(
            Q(name__icontains=search) |
            Q(university_id__icontains=search) |
            Q(family_name__icontains=search)
        )

    context = {
        'students': students,
        'departments': Department.objects.all(),
        'stages': Subject.STAGES,
        'selected_department': department_id,
        'selected_stage': stage,
        'search_query': search,
        'total_count': students.count(),
    }
    return render(request, 'exams/student_list.html', context)


@editor_required
def student_create(request):
    """إضافة طالب جديد"""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'تم إضافة الطالب "{student.name}" بنجاح')
            return redirect('exams:student_list')
    else:
        form = StudentForm()

    return render(request, 'exams/student_form.html', {
        'form': form, 'title': 'إضافة طالب جديد'
    })


@editor_required
def student_edit(request, pk):
    """تعديل بيانات طالب"""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'تم تحديث بيانات الطالب "{student.name}"')
            return redirect('exams:student_list')
    else:
        form = StudentForm(instance=student)

    return render(request, 'exams/student_form.html', {
        'form': form, 'student': student, 'title': f'تعديل: {student.name}'
    })


@editor_required
def student_delete(request, pk):
    """حذف طالب"""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        name = student.name
        student.delete()
        messages.success(request, f'تم حذف الطالب "{name}"')
        return redirect('exams:student_list')
    return render(request, 'exams/student_confirm_delete.html', {'student': student})


@editor_required
def student_import(request):
    """استيراد طلاب من ملف Excel"""
    if request.method == 'POST':
        form = StudentImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            default_dept = form.cleaned_data.get('department')

            try:
                wb = openpyxl.load_workbook(file)
                ws = wb.active

                created_count = 0
                updated_count = 0
                errors = []

                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if not row or not row[0]:
                        continue

                    name = str(row[0]).strip()
                    university_id = str(row[1]).strip() if len(row) > 1 and row[1] else ''

                    if not name or not university_id:
                        errors.append(f'سطر {row_idx}: الاسم أو الرقم الجامعي فارغ')
                        continue

                    # القسم
                    dept = default_dept
                    if len(row) > 2 and row[2]:
                        dept_name = str(row[2]).strip()
                        dept_obj = Department.objects.filter(name__icontains=dept_name).first()
                        if dept_obj:
                            dept = dept_obj

                    if not dept:
                        errors.append(f'سطر {row_idx}: لم يتم تحديد القسم للطالب {name}')
                        continue

                    # المرحلة
                    stage = 'الأولى'
                    if len(row) > 3 and row[3]:
                        stage_val = str(row[3]).strip()
                        # تطبيع: حذف "المرحلة " من البداية إذا وُجدت
                        stage_val = stage_val.replace('المرحلة ', '').replace('مرحلة ', '').strip()
                        valid_stages = [s[0] for s in Subject.STAGES]
                        # خريطة أسماء العرض → القيم المخزونة
                        display_map = {s[1].replace('المرحلة ', ''): s[0] for s in Subject.STAGES}
                        display_map.update({s[1]: s[0] for s in Subject.STAGES})
                        if stage_val in valid_stages:
                            stage = stage_val
                        elif stage_val in display_map:
                            stage = display_map[stage_val]

                    # اللقب العائلي
                    family_name = ''
                    if len(row) > 4 and row[4]:
                        family_name = str(row[4]).strip()

                    # إنشاء أو تحديث
                    student, created = Student.objects.update_or_create(
                        university_id=university_id,
                        defaults={
                            'name': name,
                            'department': dept,
                            'stage': stage,
                            'family_name': family_name,
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                msg = f'تم استيراد {created_count} طالب جديد و تحديث {updated_count} طالب'
                if errors:
                    msg += f' مع {len(errors)} خطأ'
                messages.success(request, msg)

                if errors:
                    for err in errors[:5]:
                        messages.warning(request, err)

                return redirect('exams:student_list')

            except Exception as e:
                messages.error(request, f'خطأ في قراءة الملف: {str(e)}')
    else:
        form = StudentImportForm()

    return render(request, 'exams/student_import.html', {'form': form})


# ──────────────────────────────────────────────
# الجلسات الامتحانية
# ──────────────────────────────────────────────

@login_required
@permission_required('can_access_exams')
def session_list(request):
    """قائمة الجلسات الامتحانية"""
    sessions = ExamSession.objects.annotate(
        subjects_count=Count('exam_subjects'),
    ).order_by('-date')

    context = {
        'sessions': sessions,
    }
    return render(request, 'exams/session_list.html', context)


@editor_required
def session_create(request):
    """إنشاء جلسة امتحانية"""
    if request.method == 'POST':
        form = ExamSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f'تم إنشاء الجلسة "{session.name}" بنجاح')
            return redirect('exams:session_detail', pk=session.pk)
    else:
        form = ExamSessionForm()

    return render(request, 'exams/session_form.html', {
        'form': form, 'title': 'إنشاء جلسة امتحانية جديدة'
    })


@editor_required
def session_edit(request, pk):
    """تعديل جلسة"""
    session = get_object_or_404(ExamSession, pk=pk)
    if request.method == 'POST':
        form = ExamSessionForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save()
            messages.success(request, f'تم تحديث الجلسة "{session.name}"')
            return redirect('exams:session_detail', pk=session.pk)
    else:
        form = ExamSessionForm(instance=session)

    return render(request, 'exams/session_form.html', {
        'form': form, 'session': session, 'title': f'تعديل: {session.name}'
    })


@login_required
def session_detail(request, pk):
    """تفاصيل جلسة امتحانية"""
    session = get_object_or_404(ExamSession, pk=pk)
    exam_subjects = session.exam_subjects.select_related('subject').prefetch_related('students')
    hall_setups = session.hall_setups.select_related('room')

    # إحصائيات الطلاب الفريدين (لمطابقة الخوارزمية)
    unique_student_ids = set()
    for es in exam_subjects:
        for student in es.students.all().values_list('id', flat=True):
            unique_student_ids.add(student)
    
    total_students = len(unique_student_ids)

    total_capacity = sum(hs.effective_capacity for hs in hall_setups)

    context = {
        'session': session,
        'exam_subjects': exam_subjects,
        'hall_setups': hall_setups,
        'total_students': total_students,
        'total_capacity': total_capacity,
        'subject_form': AddSubjectToSessionForm(),
        'hall_form': HallSetupForm(),
        'rooms': Room.objects.filter(is_active=True),
    }
    return render(request, 'exams/session_detail.html', context)


@editor_required
def session_delete(request, pk):
    """حذف جلسة"""
    session = get_object_or_404(ExamSession, pk=pk)
    if request.method == 'POST':
        name = session.name
        session.delete()
        messages.success(request, f'تم حذف الجلسة "{name}"')
        return redirect('exams:session_list')
    return render(request, 'exams/session_confirm_delete.html', {'session': session})


# ──────────────────────────────────────────────
# إضافة مواد وقاعات للجلسة
# ──────────────────────────────────────────────

@editor_required
def add_subject_to_session(request, session_pk):
    """إضافة مادة لجلسة"""
    session = get_object_or_404(ExamSession, pk=session_pk)

    if request.method == 'POST':
        form = AddSubjectToSessionForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            color = form.cleaned_data['color_code']

            # تعيين لون ذكي غير مكرر إذا ترك المستخدم اللون الافتراضي الأزرق
            if color.upper() == '#3B82F6':
                used_colors = set(c.upper() for c in session.exam_subjects.values_list('color_code', flat=True) if c)
                # محاولة إيجاد لون جديد من القائمة
                for fallback_color in SUBJECT_COLORS:
                    if fallback_color.upper() not in used_colors:
                        color = fallback_color
                        break
                else:
                    # إذا استُنفدت كل الألوان، نأخذ لوناً عشوائياً أو نكرر بناءً على العدد
                    existing_count = session.exam_subjects.count()
                    color = SUBJECT_COLORS[existing_count % len(SUBJECT_COLORS)]

            es, created = ExamSessionSubject.objects.get_or_create(
                session=session,
                subject=subject,
                defaults={'color_code': color}
            )
            if created:
                messages.success(request, f'تم إضافة المادة "{subject.name}"')
            else:
                messages.info(request, f'المادة "{subject.name}" مضافة مسبقاً')

    return redirect('exams:session_detail', pk=session_pk)


@editor_required
def remove_subject_from_session(request, session_pk, es_pk):
    """إزالة مادة من جلسة"""
    es = get_object_or_404(ExamSessionSubject, pk=es_pk, session_id=session_pk)
    if request.method == 'POST':
        es.delete()
        messages.success(request, 'تم إزالة المادة من الجلسة')
    return redirect('exams:session_detail', pk=session_pk)


@editor_required
def add_hall_to_session(request, session_pk):
    """إضافة قاعة لجلسة"""
    session = get_object_or_404(ExamSession, pk=session_pk)

    if request.method == 'POST':
        form = HallSetupForm(request.POST)
        if form.is_valid():
            hall = form.save(commit=False)
            hall.session = session
            try:
                hall.save()
                messages.success(request, f'تم إضافة القاعة "{hall.room.name}"')
            except Exception:
                messages.error(request, 'هذه القاعة مضافة مسبقاً لهذه الجلسة')

    return redirect('exams:session_detail', pk=session_pk)


@editor_required
def remove_hall_from_session(request, session_pk, hall_pk):
    """إزالة قاعة من جلسة"""
    hall = get_object_or_404(HallSetup, pk=hall_pk, session_id=session_pk)
    if request.method == 'POST':
        hall.delete()
        messages.success(request, 'تم إزالة القاعة من الجلسة')
    return redirect('exams:session_detail', pk=session_pk)


@editor_required
def edit_hall(request, session_pk, hall_pk):
    """تعديل إعدادات قاعة موجودة دون حذفها"""
    session = get_object_or_404(ExamSession, pk=session_pk)
    hall = get_object_or_404(HallSetup, pk=hall_pk, session=session)

    if request.method == 'POST':
        form = HallSetupForm(request.POST, instance=hall)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث إعدادات قاعة "{hall.room.name}" بنجاح')
            if session.is_distributed:
                messages.warning(request, '⚠ تم تغيير إعدادات القاعة — يُنصح بإعادة توليد التوزيع')
            return redirect('exams:session_detail', pk=session_pk)
    else:
        form = HallSetupForm(instance=hall)

    return render(request, 'exams/hall_edit_form.html', {
        'form': form,
        'hall': hall,
        'session': session,
    })


# ──────────────────────────────────────────────
# إدارة طلاب المادة
# ──────────────────────────────────────────────

@editor_required
def manage_subject_students(request, session_pk, es_pk):
    """إدارة الطلاب المسجلين في مادة"""
    session = get_object_or_404(ExamSession, pk=session_pk)
    exam_subject = get_object_or_404(ExamSessionSubject, pk=es_pk, session=session)

    # فلاتر
    department_id = request.GET.get('department')
    stage = request.GET.get('stage')
    limit = request.GET.get('limit')

    students = Student.objects.filter(is_active=True).select_related('department')
    if department_id:
        students = students.filter(department_id=department_id)
    if stage:
        students = students.filter(stage=stage)

    current_student_ids = set(exam_subject.students.values_list('id', flat=True))

    # استبعاد الطلاب الذين لديهم امتحان في نفس اليوم
    if session.date:
        busy_student_ids = ExamSessionSubject.objects.filter(
            session__date=session.date
        ).exclude(
            session=session
        ).values_list('students__id', flat=True)
        
        busy_in_same_session = ExamSessionSubject.objects.filter(
            session=session
        ).exclude(
            id=es_pk
        ).values_list('students__id', flat=True)

        busy_ids = set(busy_student_ids) | set(busy_in_same_session)
        from django.db.models import Q
        students = students.exclude(Q(id__in=busy_ids) & ~Q(id__in=current_student_ids))
        
    # تفعيل خيار تحديد عدد من الطلاب
    if limit and limit.isdigit():
        students = students.order_by('id')[:int(limit)]

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_selected':
            student_ids = request.POST.getlist('student_ids')
            exam_subject.students.add(*student_ids)
            messages.success(request, f'تم إضافة {len(student_ids)} طالب')

        elif action == 'remove_selected':
            student_ids = request.POST.getlist('student_ids')
            exam_subject.students.remove(*student_ids)
            messages.success(request, f'تم إزالة {len(student_ids)} طالب')

        elif action == 'add_all_filtered':
            exam_subject.students.add(*list(students))
            messages.success(request, f'تم إضافة جميع الطلاب المفلترين')

        return redirect('exams:manage_subject_students',
                        session_pk=session_pk, es_pk=es_pk)

    context = {
        'session': session,
        'exam_subject': exam_subject,
        'students': students,
        'current_student_ids': current_student_ids,
        'departments': Department.objects.all(),
        'stages': Subject.STAGES,
        'selected_department': department_id,
        'selected_stage': stage,
        'limit': limit,
    }
    return render(request, 'exams/manage_students.html', context)


# ──────────────────────────────────────────────
# توليد التوزيع
# ──────────────────────────────────────────────

@editor_required
def generate_seating(request, pk):
    """لوحة تحكم تشغيل الخوارزمية"""
    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = list(session.hall_setups.select_related('room').all())
    exam_subjects = session.exam_subjects.select_related('subject').prefetch_related('students')

    if request.method == 'POST':
        # الحصول على القيود من النموذج
        constraints = {
            'prevent_same_subject': request.POST.get('prevent_same_subject') == 'on',
            'prevent_same_department': request.POST.get('prevent_same_department') == 'on',
            'prevent_same_family': request.POST.get('prevent_same_family') == 'on',
        }

        if not hall_setups:
            messages.error(request, 'يجب إضافة قاعة واحدة على الأقل')
            return redirect('exams:session_detail', pk=pk)

        # تجهيز بيانات الطلاب
        exam_subjects_data = []
        processed_students = set()

        for es in exam_subjects:
            students_data = []
            for student in es.students.all():
                if student.id in processed_students:
                    continue
                processed_students.add(student.id)

                students_data.append({
                    'student_id': student.id,
                    'department_id': student.department_id,
                    'family_name': student.family_name or '',
                    'subject_id': es.subject_id,
                    'exam_subject_id': es.id,
                    'name': student.name,
                })
            
            exam_subjects_data.append({
                'exam_subject_id': es.id,
                'subject_id': es.subject_id,
                'students': students_data,
            })

        total_students = sum(len(esd['students']) for esd in exam_subjects_data)
        if total_students == 0:
            messages.error(request, 'لا يوجد طلاب مسجلون في أي مادة')
            return redirect('exams:session_detail', pk=pk)

        # تشغيل الخوارزمية
        with transaction.atomic():
            SeatingAssignment.objects.filter(session=session).delete()

            use_column_dist = any(hs.spacing_mode == 'عمودي_أقسام' for hs in hall_setups)
            if use_column_dist:
                result = column_department_distribute(session, hall_setups, exam_subjects_data)
            else:
                result = smart_distribute(session, hall_setups, exam_subjects_data, constraints)

            assignments_to_create = [
                SeatingAssignment(
                    session=session,
                    hall_setup_id=a['hall_setup_id'],
                    student_id=a['student_id'],
                    exam_subject_id=a['exam_subject_id'],
                    row=a['row'],
                    column=a['column'],
                    seat_label=a['seat_label'],
                ) for a in result['assignments']
            ]
            SeatingAssignment.objects.bulk_create(assignments_to_create)

            session.is_distributed = True
            session.save()

        if result['success']:
            messages.success(request, f'✅ تم التوزيع بنجاح! تم توزيع {result["stats"]["assigned"]} طالب.')
        else:
            messages.warning(request, f'⚠ تم توزيع {result["stats"]["assigned"]} طالب، لكن {result["stats"]["unassigned"]} طالب لم يتم توزيعهم.')

        return redirect('exams:seating_map', pk=pk)

    # بيانات للوحة التحكم (GET)
    unique_student_ids = set()
    for es in exam_subjects:
        for s_id in es.students.all().values_list('id', flat=True):
            unique_student_ids.add(s_id)
    
    total_students = len(unique_student_ids)
    total_capacity = sum(hs.effective_capacity for hs in hall_setups)

    context = {
        'session': session,
        'total_students': total_students,
        'total_capacity': total_capacity,
        'hall_count': len(hall_setups),
        'subject_count': exam_subjects.count(),
        'hall_setups': hall_setups,
    }
    return render(request, 'exams/generate_dashboard.html', context)


@editor_required
def swap_seats(request, session_pk):
    """
    API: تبديل أو نقل طالب من مقعد لآخر يدوياً.
    POST JSON: {"from_assignment_id": X, "to_row": R, "to_col": C, "to_hall_setup_id": H}
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST only'}, status=405)

    session = get_object_or_404(ExamSession, pk=session_pk)
    try:
        data = json.loads(request.body)
        from_id = int(data['from_assignment_id'])
        to_row = int(data['to_row'])
        to_col = int(data['to_col'])
        to_hall_id = int(data['to_hall_setup_id'])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': f'بيانات غير صالحة: {e}'}, status=400)

    with transaction.atomic():
        from_assignment = get_object_or_404(SeatingAssignment, pk=from_id, session=session)
        hall = get_object_or_404(HallSetup, pk=to_hall_id, session=session)

        # فحص صلاحية الإحداثيات
        if not (0 <= to_row < hall.rows and 0 <= to_col < hall.columns):
            return JsonResponse({'success': False, 'error': 'إحداثيات المقعد خارج حدود القاعة'}, status=400)

        # هل يوجد طالب في المقعد الهدف؟
        existing = SeatingAssignment.objects.filter(
            hall_setup=hall, row=to_row, column=to_col
        ).exclude(pk=from_id).first()

        if existing:
            # تبادل: ننقل الطالب الموجود لمكان الطالب الأصلي
            old_row, old_col = from_assignment.row, from_assignment.column
            old_hall = from_assignment.hall_setup
            old_label = from_assignment.seat_label

            existing.row = old_row
            existing.column = old_col
            existing.hall_setup = old_hall
            existing.seat_label = old_label
            existing.save()

            from_assignment.row = to_row
            from_assignment.column = to_col
            from_assignment.hall_setup = hall
            from_assignment.seat_label = f"{chr(65 + to_row)}{to_col + 1}"
            from_assignment.save()

            return JsonResponse({
                'success': True,
                'action': 'swap',
                'moved_student': from_assignment.student.name,
                'swapped_with': existing.student.name,
                'new_seat': from_assignment.seat_label,
            })
        else:
            # نقل لمقعد فارغ
            from_assignment.row = to_row
            from_assignment.column = to_col
            from_assignment.hall_setup = hall
            from_assignment.seat_label = f"{chr(65 + to_row)}{to_col + 1}"
            from_assignment.save()

            return JsonResponse({
                'success': True,
                'action': 'move',
                'moved_student': from_assignment.student.name,
                'new_seat': from_assignment.seat_label,
            })

    # GET — عرض صفحة التأكيد
    exam_subjects = session.exam_subjects.select_related('subject').prefetch_related('students')
    hall_setups = session.hall_setups.select_related('room')

    total_students = 0
    for es in exam_subjects:
        total_students += es.students.count()

    total_capacity = sum(hs.effective_capacity for hs in hall_setups)

    context = {
        'session': session,
        'exam_subjects': exam_subjects,
        'hall_setups': hall_setups,
        'total_students': total_students,
        'total_capacity': total_capacity,
    }
    return render(request, 'exams/seating_config.html', context)


# ──────────────────────────────────────────────
# خريطة الجلوس التفاعلية
# ──────────────────────────────────────────────

@login_required
def seating_map(request, pk):
    """عرض خريطة الجلوس التفاعلية"""
    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = session.hall_setups.select_related('room').all()
    assignments = session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all()

    # بناء خرائط القاعات
    halls_data = []
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]

        # بناء الشبكة
        grid = [[None] * hall.columns for _ in range(hall.rows)]
        for a in hall_assignments:
            if a.row < hall.rows and a.column < hall.columns:
                grid[a.row][a.column] = {
                    'assignment_id': a.id,
                    'student_name': a.student.name,
                    'university_id': a.student.university_id,
                    'subject_name': a.exam_subject.subject.name if a.exam_subject else '',
                    'subject_id': str(a.exam_subject.subject.id) if a.exam_subject else '',
                    'department': a.student.department.name,
                    'department_id': str(a.student.department.id),
                    'seat_label': a.seat_label,
                    'color': a.exam_subject.color_code if a.exam_subject else '#6B7280',
                }

        halls_data.append({
            'hall': hall,
            'grid': grid,
            'assigned_count': len(hall_assignments),
            'rows_range': range(hall.rows),
            'cols_range': range(hall.columns),
        })

    # بيانات المواد للترميز اللوني
    exam_subjects = session.exam_subjects.select_related('subject').all()
    legend = [
        {'id': str(es.subject.id), 'name': es.subject.name, 'color': es.color_code}
        for es in exam_subjects
    ]

    # جلب الأقسام الموجودة في التوزيعة لغرض الفلترة
    departments_dict = {}
    for a in assignments:
        if a.student.department:
            departments_dict[str(a.student.department.id)] = a.student.department.name
    
    departments_filter = [{'id': k, 'name': v} for k, v in departments_dict.items()]

    context = {
        'session': session,
        'halls_data': halls_data,
        'legend': legend,
        'departments_filter': departments_filter,
        'total_assigned': assignments.count(),
    }
    return render(request, 'exams/seating_map.html', context)


# ──────────────────────────────────────────────
# قوائم الطلاب لكل قاعة (للطباعة واللصق)
# ──────────────────────────────────────────────

@login_required
def hall_student_lists(request, pk):
    """قوائم الطلاب لكل قاعة بشكل منظم للطباعة"""
    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = session.hall_setups.select_related('room').all()
    assignments = session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all()

    # بناء بيانات القاعات مع قوائم الطلاب المرتبة حسب المقعد
    halls_data = []
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]

        # ترتيب حسب الصف ثم العمود (ترتيب المقاعد A1, A2, ... B1, B2, ...)
        hall_assignments.sort(key=lambda a: (a.row, a.column))

        students_list = []
        for a in hall_assignments:
            students_list.append({
                'seat_label': a.seat_label,
                'student_name': a.student.name,
                'university_id': a.student.university_id,
                'department': a.student.department.name,
                'subject_name': a.exam_subject.subject.name if a.exam_subject else '',
                'color': a.exam_subject.color_code if a.exam_subject else '#6B7280',
                'row': a.row,
                'column': a.column,
            })

        halls_data.append({
            'hall': hall,
            'students_list': students_list,
            'assigned_count': len(hall_assignments),
        })

    # بيانات المواد
    exam_subjects = session.exam_subjects.select_related('subject').all()
    legend = [
        {'id': str(es.subject.id), 'name': es.subject.name, 'color': es.color_code}
        for es in exam_subjects
    ]

    context = {
        'session': session,
        'halls_data': halls_data,
        'legend': legend,
        'total_assigned': assignments.count(),
    }
    return render(request, 'exams/hall_student_lists.html', context)


# ──────────────────────────────────────────────
# بطاقات المقاعد (A4 — 3×7)
# ──────────────────────────────────────────────

CARDS_PER_PAGE = 21  # 3 أعمدة × 7 صفوف


@login_required
def seat_cards(request, pk):
    """بطاقات المقاعد للطباعة على ورق A4 — 3 أعمدة × 7 صفوف"""
    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = session.hall_setups.select_related('room').all()
    assignments = session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all()

    halls_data = []
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]
        hall_assignments.sort(key=lambda a: (a.row, a.column))

        # تجهيز بيانات البطاقات
        cards = []
        for a in hall_assignments:
            cards.append({
                'seat_label': a.seat_label,
                'student_name': a.student.name,
                'university_id': a.student.university_id,
                'department': a.student.department.name,
                'hall_name': hall.room.name,
                'subject_name': a.exam_subject.subject.name if a.exam_subject else 'بدون مادة',
                'exam_date': session.date.strftime('%Y-%m-%d') if session.date else '',
                'color': a.exam_subject.color_code if a.exam_subject else '#6B7280',
            })

        # تقسيم البطاقات إلى صفحات (21 بطاقة لكل صفحة)
        card_pages = []
        for i in range(0, len(cards), CARDS_PER_PAGE):
            page = cards[i:i + CARDS_PER_PAGE]
            # ملء الصفحة الأخيرة ببطاقات فارغة حتى 21
            while len(page) < CARDS_PER_PAGE:
                page.append(None)
            card_pages.append(page)

        # إذا لم يوجد طلاب، لا نعرض القاعة
        if not cards:
            continue

        halls_data.append({
            'hall': hall,
            'card_pages': card_pages,
            'assigned_count': len(cards),
        })

    context = {
        'session': session,
        'halls_data': halls_data,
        'total_assigned': assignments.count(),
    }
    return render(request, 'exams/seat_cards.html', context)


@login_required
def department_attendance_lists(request, pk):
    """قوائم الطلاب لكل قسم بشكل منظم للطباعة"""
    session = get_object_or_404(ExamSession, pk=pk)
    assignments = session.assignments.select_related(
        'student', 'student__department', 'exam_subject', 'exam_subject__subject'
    ).all().order_by('student__department__name', 'student__stage', 'student__name')

    # تجميع حسب القسم
    # سننشئ قائمة من الأقسام، وكل قسم يحتوي على قائمة طلابه
    departments_dict = {}
    for a in assignments:
        dept = a.student.department
        if dept.id not in departments_dict:
            departments_dict[dept.id] = {
                'name': dept.name,
                'students': []
            }
        
        departments_dict[dept.id]['students'].append({
            'name': a.student.name,
            'university_id': a.student.university_id,
            'stage': a.student.stage,
            'subject': a.exam_subject.subject.name if a.exam_subject else '',
            'hall': a.hall_setup.room.name,
            'seat': a.seat_label
        })

    context = {
        'session': session,
        'departments': departments_dict.values(),
    }
    return render(request, 'exams/department_attendance_lists.html', context)


# ──────────────────────────────────────────────
# بحث الطالب عن مقعده
# ──────────────────────────────────────────────

@login_required
def student_lookup(request, pk):
    """بحث الطالب عن مقعده"""
    session = get_object_or_404(ExamSession, pk=pk)
    result = None
    search = request.GET.get('q', '')

    if search:
        assignment = SeatingAssignment.objects.filter(
            session=session
        ).filter(
            Q(student__name__icontains=search) |
            Q(student__university_id__icontains=search)
        ).select_related(
            'student', 'hall_setup__room',
            'exam_subject__subject'
        ).first()

        if assignment:
            result = {
                'found': True,
                'student_name': assignment.student.name,
                'university_id': assignment.student.university_id,
                'room_name': assignment.hall_setup.room.name,
                'seat_label': assignment.seat_label,
                'subject_name': assignment.exam_subject.subject.name if assignment.exam_subject else '',
                'row': assignment.row + 1,
                'column': assignment.column + 1,
            }
        else:
            result = {'found': False}

    context = {
        'session': session,
        'result': result,
        'search_query': search,
    }
    return render(request, 'exams/student_lookup.html', context)


# ──────────────────────────────────────────────
# تصدير PDF
# ──────────────────────────────────────────────

@login_required
def seating_pdf(request, pk):
    """تصدير خريطة الجلوس كـ PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import arabic_reshaper
    from bidi.algorithm import get_display

    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = session.hall_setups.select_related('room').all()
    assignments = session.assignments.select_related(
        'student', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="seating_{session.pk}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    elements = []
    
    # تسجيل خط يدعم اللغة العربية
    import os
    font_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
    else:
        # Fallback in case Arial is somehow missing
        pass

    styles = getSampleStyleSheet()
    
    # تعديل الأنماط لاستخدام الخط العربي
    styles['Normal'].fontName = 'ArabicFont' if os.path.exists(font_path) else 'Helvetica'
    styles['Title'].fontName = 'ArabicFont' if os.path.exists(font_path) else 'Helvetica'
    styles['Heading2'].fontName = 'ArabicFont' if os.path.exists(font_path) else 'Helvetica'
    styles['Heading3'].fontName = 'ArabicFont' if os.path.exists(font_path) else 'Helvetica'

    def reshape_arabic(text):
        """تحويل النص العربي لعرضه في PDF"""
        if not text:
            return ""
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except Exception:
            return str(text)

    # عنوان
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Title'],
        alignment=1,
        fontSize=16,
    )
    elements.append(Paragraph(reshape_arabic(f"خريطة الجلوس — {session.name}"), title_style))
    elements.append(Paragraph(reshape_arabic(f"التاريخ: {session.date}"), styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))

    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]

        # عنوان القاعة
        elements.append(Paragraph(
            reshape_arabic(f"القاعة: {hall.room.name} ({hall.rows}×{hall.columns})"),
            styles['Heading2']
        ))

        # بناء جدول الشبكة
        grid = [['' for _ in range(hall.columns + 1)] for _ in range(hall.rows + 1)]

        # رؤوس الأعمدة
        grid[0][0] = ''
        for c in range(hall.columns):
            grid[0][c + 1] = str(c + 1)

        # رؤوس الصفوف
        for r in range(hall.rows):
            grid[r + 1][0] = chr(65 + r)


        # ملء البيانات
        hide_names = request.GET.get('hide_names') == '1'
        hide_ids = request.GET.get('hide_ids') == '1'

        for a in hall_assignments:
            parts = []
            if not hide_names:
                parts.append(str(a.student.name))
            if not hide_ids:
                parts.append(str(a.student.university_id))
            
            cell_text = reshape_arabic("\n".join(parts))
            
            if a.row + 1 < len(grid) and a.column + 1 < len(grid[0]):
                grid[a.row + 1][a.column + 1] = cell_text

        # إنشاء الجدول
        col_width = max(2.5 * cm, (25 * cm) / (hall.columns + 1))
        table = Table(grid, colWidths=[1.5 * cm] + [col_width] * hall.columns)

        style_commands = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.2, 0.3, 0.5)),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'ArabicFont' if os.path.exists(font_path) else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]

        # تلوين المقاعد حسب المادة
        for a in hall_assignments:
            if a.exam_subject:
                hex_color = a.exam_subject.color_code
                try:
                    r_val = int(hex_color[1:3], 16) / 255
                    g_val = int(hex_color[3:5], 16) / 255
                    b_val = int(hex_color[5:7], 16) / 255
                    bg = colors.Color(r_val, g_val, b_val, alpha=0.2)
                    style_commands.append((
                        'BACKGROUND',
                        (a.column + 1, a.row + 1),
                        (a.column + 1, a.row + 1),
                        bg
                    ))
                except Exception:
                    pass

        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        elements.append(Spacer(1, 1 * cm))

    # بناء مفتاح الألوان
    exam_subjects = session.exam_subjects.select_related('subject').all()
    if exam_subjects:
        elements.append(Paragraph(reshape_arabic("مفتاح المواد:"), styles['Heading3']))
        legend_data = [[
            reshape_arabic(es.subject.name) for es in exam_subjects
        ]]
        legend_table = Table(legend_data)
        legend_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'ArabicFont' if os.path.exists(font_path) else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]
        for i, es in enumerate(exam_subjects):
            try:
                hex_color = es.color_code
                r_val = int(hex_color[1:3], 16) / 255
                g_val = int(hex_color[3:5], 16) / 255
                b_val = int(hex_color[5:7], 16) / 255
                legend_style.append((
                    'BACKGROUND', (i, 0), (i, 0),
                    colors.Color(r_val, g_val, b_val, alpha=0.3)
                ))
            except Exception:
                pass
        legend_table.setStyle(TableStyle(legend_style))
        elements.append(legend_table)

    doc.build(elements)
    return response
