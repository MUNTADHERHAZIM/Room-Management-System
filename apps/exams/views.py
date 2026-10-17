import json
import re
from urllib.parse import quote
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.db import transaction

from apps.core.decorators import editor_required, permission_required
from apps.core.models import College, Department
from apps.core.search_utils import arabic_search_filter
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
from .algorithm import smart_distribute, column_department_distribute, column_single_department_distribute


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
            arabic_search_filter('name', search) |
            Q(university_id__icontains=search) |
            arabic_search_filter('family_name', search)
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
    exam_subjects = session.exam_subjects.select_related('subject').annotate(
        students_count=Count('students', distinct=True)
    ).prefetch_related('students')
    hall_setups = list(session.hall_setups.select_related('room').all())

    # إحصائيات الطلاب الفريدين (لمطابقة الخوارزمية)
    unique_student_ids = set()
    for es in exam_subjects:
        for student in es.students.all():
            unique_student_ids.add(student.id)
    
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
    department_id = request.GET.get('department') or request.POST.get('department')
    stage = request.GET.get('stage') or request.POST.get('stage')
    limit = request.GET.get('limit') or request.POST.get('limit')

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
    if limit and str(limit).isdigit():
        students = students.order_by('id')[:int(limit)]

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_selected':
            student_ids = request.POST.getlist('student_ids')
            if student_ids:
                exam_subject.students.add(*student_ids)
                messages.success(request, f'تم بنجاح إضافة {len(student_ids)} طالب للمادة')
            else:
                messages.warning(request, 'لم يتم تحديد أي طالب للإضافة')

        elif action == 'remove_selected':
            student_ids = request.POST.getlist('student_ids')
            if student_ids:
                exam_subject.students.remove(*student_ids)
                messages.success(request, f'تم إزالة {len(student_ids)} طالب')
            else:
                messages.warning(request, 'لم يتم تحديد أي طالب للإزالة')

        elif action == 'add_all_filtered':
            student_list = list(students)
            if student_list:
                exam_subject.students.add(*student_list)
                messages.success(request, f'تم بنجاح إضافة جميع الطلاب المفلترين ({len(student_list)} طالب)')
            else:
                messages.warning(request, 'لا يوجد طلاب مفلترين للإضافة')

        # المحافظة على الفلاتر عند إعادة التوجيه
        from urllib.parse import urlencode
        query_params = {}
        if department_id:
            query_params['department'] = department_id
        if stage:
            query_params['stage'] = stage
        if limit:
            query_params['limit'] = limit

        url = reverse('exams:manage_subject_students', kwargs={'session_pk': session_pk, 'es_pk': es_pk})
        if query_params:
            url += f"?{urlencode(query_params)}"
        return redirect(url)

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

            use_single_column_dist = any(hs.spacing_mode == 'عمودي_كامل' for hs in hall_setups)
            use_column_dist = any(hs.spacing_mode == 'عمودي_أقسام' for hs in hall_setups)
            if use_single_column_dist:
                result = column_single_department_distribute(session, hall_setups, exam_subjects_data)
            elif use_column_dist:
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
    assignments = list(session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all())

    # بناء خرائط القاعات
    halls_data = []
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]

        # بناء الشبكة
        grid = [[None] * hall.columns for _ in range(hall.rows)]
        for a in hall_assignments:
            if a.row < hall.rows and a.column < hall.columns:
                stage_val = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else '')
                stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ''
                grid[a.row][a.column] = {
                    'assignment_id': a.id,
                    'student_name': a.student.name,
                    'university_id': a.student.university_id,
                    'stage': stage_display,
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

    # بيانات المواد والمراحل للترميز اللوني
    exam_subjects = session.exam_subjects.select_related('subject').all()
    legend = []
    for es in exam_subjects:
        stage_val = es.subject.stage if es.subject else ''
        stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ''
        legend.append({
            'id': str(es.subject.id),
            'name': es.subject.name,
            'stage_only': stage_display or es.subject.name,
            'color': es.color_code
        })

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
        'total_assigned': len(assignments),
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
    assignments = list(session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all())

    # بناء بيانات القاعات مع قوائم الطلاب المرتبة حسب المقعد
    halls_data = []
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]

        # ترتيب حسب الصف ثم العمود (ترتيب المقاعد A1, A2, ... B1, B2, ...)
        hall_assignments.sort(key=lambda a: (a.row, a.column))

        students_list = []
        for a in hall_assignments:
            stage_val = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else '')
            stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ''
            students_list.append({
                'seat_label': a.seat_label,
                'student_name': a.student.name,
                'university_id': a.student.university_id,
                'department': a.student.department.name,
                'stage': stage_display,
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

    # بيانات المواد والمراحل
    exam_subjects = session.exam_subjects.select_related('subject').all()
    legend = []
    for es in exam_subjects:
        stage_val = es.subject.stage if es.subject else ''
        stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ''
        legend.append({
            'id': str(es.subject.id),
            'name': es.subject.name,
            'stage_only': stage_display or es.subject.name,
            'color': es.color_code
        })

    STAGE_ORDER = {
        'المرحلة الأولى': 1, 'الأولى': 1,
        'المرحلة الثانية': 2, 'الثانية': 2,
        'المرحلة الثالثة': 3, 'الثالثة': 3,
        'المرحلة الرابعة': 4, 'الرابعة': 4,
        'المرحلة الخامسة': 5, 'الخامسة': 5,
        'المرحلة السادسة': 6, 'السادسة': 6,
    }
    stages_set = set()
    for h_data in halls_data:
        for st in h_data['students_list']:
            if st.get('stage'):
                stages_set.add(st['stage'])

    stages_filter_list = sorted(list(stages_set), key=lambda x: STAGE_ORDER.get(x.strip(), 99))

    context = {
        'session': session,
        'halls_data': halls_data,
        'legend': legend,
        'stages_filter': stages_filter_list,
        'total_assigned': len(assignments),
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
    assignments = list(session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all())

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
        'total_assigned': len(assignments),
    }
    return render(request, 'exams/seat_cards.html', context)


@login_required
def department_attendance_lists(request, pk):
    """قوائم الطلاب لكل قسم مقسمة حسب القاعات بشكل منظم للطباعة والتوزيع على المراقبين"""
    session = get_object_or_404(ExamSession, pk=pk)
    assignments = session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all().order_by('student__department__name', 'hall_setup__room__name', 'row', 'column', 'student__name')

    # تجميع حسب القسم ثم حسب القاعة
    # لكي يحصل مراقب كل قاعة على قائمة مستقلة تماماً للقسم المتواجد في قاعته فقط
    departments_dict = {}
    halls_filter_dict = {}
    dept_filter_dict = {}

    for a in assignments:
        dept = a.student.department
        hall = a.hall_setup
        room_name = hall.room.name
        
        if hall.id not in halls_filter_dict:
            halls_filter_dict[hall.id] = room_name

        if dept.id not in departments_dict:
            departments_dict[dept.id] = {
                'id': dept.id,
                'name': dept.name,
                'halls': {},
                'total_students': 0,
            }
            dept_filter_dict[dept.id] = dept.name

        if hall.id not in departments_dict[dept.id]['halls']:
            departments_dict[dept.id]['halls'][hall.id] = {
                'hall_id': hall.id,
                'hall_name': room_name,
                'dept_id': dept.id,
                'dept_name': dept.name,
                'students': [],
            }

        stage_val = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else '')
        stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ''

        departments_dict[dept.id]['halls'][hall.id]['students'].append({
            'name': a.student.name,
            'university_id': a.student.university_id,
            'stage': stage_display or stage_val,
            'subject': a.exam_subject.subject.name if a.exam_subject else '',
            'color': a.exam_subject.color_code if a.exam_subject else '#4f46e5',
            'seat': a.seat_label,
            'hall': room_name,
            'row': a.row,
            'column': a.column,
        })
        departments_dict[dept.id]['total_students'] += 1

    # تحويل القواميس إلى قوائم منظمة
    departments_data = []
    for dept_id, dept_info in departments_dict.items():
        halls_list = list(dept_info['halls'].values())
        departments_data.append({
            'id': dept_info['id'],
            'name': dept_info['name'],
            'halls': halls_list,
            'total_students': dept_info['total_students'],
        })

    halls_filter_list = [{'id': hid, 'name': hname} for hid, hname in halls_filter_dict.items()]
    dept_filter_list = [{'id': did, 'name': dname} for did, dname in dept_filter_dict.items()]

    STAGE_ORDER = {
        'المرحلة الأولى': 1, 'الأولى': 1,
        'المرحلة الثانية': 2, 'الثانية': 2,
        'المرحلة الثالثة': 3, 'الثالثة': 3,
        'المرحلة الرابعة': 4, 'الرابعة': 4,
        'المرحلة الخامسة': 5, 'الخامسة': 5,
        'المرحلة السادسة': 6, 'السادسة': 6,
    }
    stages_set = set()
    for d_info in departments_data:
        for h_info in d_info['halls']:
            for s_info in h_info['students']:
                if s_info.get('stage'):
                    stages_set.add(s_info['stage'])

    stages_filter_list = sorted(list(stages_set), key=lambda x: STAGE_ORDER.get(x.strip(), 99))

    context = {
        'session': session,
        'departments': departments_data,
        'halls_filter': halls_filter_list,
        'dept_filter': dept_filter_list,
        'stages_filter': stages_filter_list,
        'total_assigned': assignments.count(),
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
            arabic_search_filter('student__name', search) |
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
    """تصدير خريطة الجلوس كـ PDF بتصميم احترافي ودعم كامل للغة العربية"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from apps.core.pdf_utils import register_arabic_fonts, reshape_arabic

    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = list(session.hall_setups.select_related('room').all())
    assignments = list(session.assignments.select_related(
        'student', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all())

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="seating_{session.pk}.pdf"'

    # هوامش محسوبة بدقة لاستغلال مساحة صفحة A4 بالعرض
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=0.8 * cm,
        leftMargin=0.8 * cm,
        topMargin=0.7 * cm,
        bottomMargin=0.7 * cm,
    )

    elements = []
    
    font_name = register_arabic_fonts()
    bold_font_name = 'ArabicFont-Bold' if font_name == 'ArabicFont' else font_name

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Title'],
        fontName=bold_font_name,
        alignment=1,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
    )
    subtitle_style = ParagraphStyle(
        'ArabicSubtitle',
        parent=styles['Normal'],
        fontName=font_name,
        alignment=1,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569'),
    )
    hall_title_style = ParagraphStyle(
        'ArabicHallTitle',
        parent=styles['Heading2'],
        fontName=bold_font_name,
        alignment=1,
        fontSize=11.5,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
    )
    board_style = ParagraphStyle(
        'ArabicBoard',
        parent=styles['Normal'],
        fontName=bold_font_name,
        alignment=1,
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName=bold_font_name,
        alignment=1,
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
    )
    cell_student_style = ParagraphStyle(
        'CellStudent',
        parent=styles['Normal'],
        fontName=bold_font_name,
        alignment=1,
        fontSize=6.8,
        leading=8,
        textColor=colors.HexColor('#0F172A'),
    )
    cell_empty_style = ParagraphStyle(
        'CellEmpty',
        parent=styles['Normal'],
        fontName=font_name,
        alignment=1,
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor('#94A3B8'),
    )
    legend_style_text = ParagraphStyle(
        'LegendText',
        parent=styles['Normal'],
        fontName=bold_font_name,
        alignment=1,
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor('#1E293B'),
    )
    hall_right_title_style = ParagraphStyle(
        'HallRightTitle',
        parent=styles['Normal'],
        fontName=bold_font_name,
        alignment=2,  # Right aligned
        fontSize=12.5,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
    )
    hall_right_sub_style = ParagraphStyle(
        'HallRightSub',
        parent=styles['Normal'],
        fontName=font_name,
        alignment=2,  # Right aligned
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#475569'),
    )
    title_left_style = ParagraphStyle(
        'TitleLeftStyle',
        parent=styles['Normal'],
        fontName=bold_font_name,
        alignment=0,  # Left aligned
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
    )
    subtitle_left_style = ParagraphStyle(
        'SubtitleLeftStyle',
        parent=styles['Normal'],
        fontName=font_name,
        alignment=0,  # Left aligned
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B'),
    )

    hide_names = request.GET.get('hide_names') == '1'
    hide_ids = request.GET.get('hide_ids') == '1'
    hide_labels = request.GET.get('hide_labels') == '1'
    hide_colors = request.GET.get('hide_colors') == '1'
    hide_stage = request.GET.get('hide_stage') == '1'
    hide_hall_info = request.GET.get('hide_hall_info') == '1'
    stage_filter = request.GET.get('stage')

    def check_student_stage(a, target):
        stg = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else '')
        stg_disp = stg if stg.startswith('المرحلة') else f"المرحلة {stg}" if stg else ''
        return stg.strip() == target.strip() or stg_disp.strip() == target.strip()

    if stage_filter and stage_filter != 'all':
        assignments = [a for a in assignments if check_student_stage(a, stage_filter)]

    rendered_halls_count = 0
    total_halls = len(hall_setups)

    for hall_idx, hall in enumerate(hall_setups):
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]
        if stage_filter and stage_filter != 'all' and not hall_assignments:
            continue

        rendered_halls_count += 1

        # ترويسة القاعة
        if not hide_hall_info:
            left_cell = [
                Paragraph(reshape_arabic(f"خريطة توزيع مقاعد الامتحان — {session.name}"), title_left_style),
                Paragraph(reshape_arabic(f"التاريخ: {session.date}   |   إجمالي الطلاب الموزعين: {len(hall_assignments)} طالب"), subtitle_left_style),
            ]
            right_cell = [
                Paragraph(reshape_arabic(f"القاعة الامتحانية: {hall.room.name}"), hall_right_title_style),
                Paragraph(reshape_arabic(f"الأبعاد: {hall.rows} صف × {hall.columns} عمود  ({hall.total_seats} مقعد)"), hall_right_sub_style),
            ]
            header_table = Table([[left_cell, right_cell]], colWidths=[17.1 * cm, 11.0 * cm])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
                ('BOX', (1, 0), (1, 0), 1.2, colors.HexColor('#0F172A')),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (1, 0), (1, 0), 8),
                ('LEFTPADDING', (1, 0), (1, 0), 8),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 0.25 * cm))

        # حساب الأبعاد المتجاوبة للجدول
        total_avail_w = 28.1 * cm
        row_hdr_w = 1.0 * cm
        col_w = min(4.4 * cm, (total_avail_w - row_hdr_w) / max(1, hall.columns))
        actual_table_w = row_hdr_w + (col_w * hall.columns)

        # شريط السبورة (اتجاه النظر)
        if not hide_hall_info:
            board_data = [[Paragraph(reshape_arabic("◄ السبورة (اتجاه النظر) ►"), board_style)]]
            board_table = Table(board_data, colWidths=[actual_table_w])
            board_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1E293B')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(board_table)
            elements.append(Spacer(1, 0.2 * cm))

        # بناء جدول الشبكة
        grid = [[None for _ in range(hall.columns + 1)] for _ in range(hall.rows + 1)]

        # رؤوس الأعمدة
        grid[0][0] = Paragraph("", header_cell_style)
        for c in range(hall.columns):
            grid[0][c + 1] = Paragraph(str(c + 1), header_cell_style)

        # رؤوس الصفوف
        for r in range(hall.rows):
            grid[r + 1][0] = Paragraph(chr(65 + r), header_cell_style)

        # تجهيز خريطة توزيع المقاعد
        assign_map = {(a.row, a.column): a for a in hall_assignments}

        # ملء المقاعد مع احترام كامل لخيارات الحجب
        for r in range(hall.rows):
            for c in range(hall.columns):
                a = assign_map.get((r, c))
                seat_label = f"{chr(65 + r)}{c + 1}"
                if a:
                    parts = []
                    if not hide_names:
                        parts.append(f"<b>{reshape_arabic(a.student.name)}</b>")
                    if not hide_ids:
                        parts.append(f"<font size=5.5 color='#334155'>{reshape_arabic(str(a.student.university_id))}</font>")
                    if not hide_labels:
                        parts.append(f"<font size=5 color='#64748B'>[{seat_label}]</font>")
                    if not hide_stage:
                        s_val = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else '')
                        s_disp = s_val if s_val.startswith('المرحلة') else f"المرحلة {s_val}" if s_val else ''
                        if s_disp:
                            parts.append(f"<font size=4.8 color='#475569'>{reshape_arabic(s_disp)}</font>")

                    cell_text = "<br/>".join(parts) if parts else reshape_arabic("—")
                    grid[r + 1][c + 1] = Paragraph(cell_text, cell_student_style)
                else:
                    if hide_labels:
                        grid[r + 1][c + 1] = Paragraph("<font size=5.5 color='#CBD5E1'>—</font>", cell_empty_style)
                    else:
                        grid[r + 1][c + 1] = Paragraph(f"<font size=5.5 color='#94A3B8'>{seat_label}</font>", cell_empty_style)

        row_h = min(1.6 * cm, max(1.05 * cm, (12.5 * cm) / max(1, hall.rows)))
        row_heights = [0.6 * cm] + [row_h] * hall.rows
        col_widths = [row_hdr_w] + [col_w] * hall.columns

        table = Table(grid, colWidths=col_widths, rowHeights=row_heights)

        style_commands = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor('#475569')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#1E293B')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]

        # تلوين المقاعد الشاغرة
        for r in range(hall.rows):
            for c in range(hall.columns):
                if (r, c) not in assign_map:
                    style_commands.append((
                        'BACKGROUND', (c + 1, r + 1), (c + 1, r + 1), colors.HexColor('#F8FAFC')
                    ))

        # تلوين المقاعد حسب المادة (فقط في حال عدم حجب الألوان)
        if not hide_colors:
            for a in hall_assignments:
                if a.exam_subject and a.exam_subject.color_code:
                    hex_color = a.exam_subject.color_code.strip()
                    try:
                        if hex_color.startswith('#') and len(hex_color) == 7:
                            r_val = int(hex_color[1:3], 16) / 255
                            g_val = int(hex_color[3:5], 16) / 255
                            b_val = int(hex_color[5:7], 16) / 255
                            bg = colors.Color(r_val, g_val, b_val, alpha=0.18)
                            style_commands.append((
                                'BACKGROUND', (a.column + 1, a.row + 1), (a.column + 1, a.row + 1), bg
                            ))
                    except Exception:
                        pass

        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        elements.append(Spacer(1, 0.4 * cm))

        # مفتاح المواد لكل قاعة
        hall_subjects = {}
        for a in hall_assignments:
            if a.exam_subject and a.exam_subject.subject:
                sub_id = a.exam_subject.subject.id
                if sub_id not in hall_subjects:
                    stage_val = a.student.stage or a.exam_subject.subject.stage or ''
                    stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ''
                    display_label = (stage_display if stage_display and not hide_stage else a.exam_subject.subject.name)
                    hall_subjects[sub_id] = {
                        'name': display_label,
                        'color': a.exam_subject.color_code,
                        'count': 0
                    }
                hall_subjects[sub_id]['count'] += 1

        if hall_subjects:
            legend_cells = []
            legend_styles = [
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]
            
            for idx, (sub_id, info) in enumerate(hall_subjects.items()):
                text = reshape_arabic(f"{info['name']} ({info['count']} طالب)")
                legend_cells.append(Paragraph(text, legend_style_text))
                if not hide_colors:
                    hex_color = info['color'] or '#3B82F6'
                    try:
                        if hex_color.startswith('#') and len(hex_color) == 7:
                            r_val = int(hex_color[1:3], 16) / 255
                            g_val = int(hex_color[3:5], 16) / 255
                            b_val = int(hex_color[5:7], 16) / 255
                            legend_styles.append((
                                'BACKGROUND', (idx, 0), (idx, 0),
                                colors.Color(r_val, g_val, b_val, alpha=0.22)
                            ))
                    except Exception:
                        pass

            legend_table = Table([legend_cells], colWidths=[actual_table_w / max(1, len(legend_cells))] * len(legend_cells))
            legend_table.setStyle(TableStyle(legend_styles))
            elements.append(legend_table)

        # فاصل صفحة بين القاعات
        if hall_idx < total_halls - 1:
            elements.append(PageBreak())

    if not elements:
        elements.append(Paragraph(reshape_arabic("لا توجد بيانات مطابقة لخيارات التصفية المختارة"), title_style))

    doc.build(elements)
    return response


# ──────────────────────────────────────────────
# تصدير بيانات الجلسة إلى Excel بشيتات متعددة فائقة الاحترافية
# ──────────────────────────────────────────────

@login_required
def session_excel_export(request, pk):
    """
    تصدير بيانات الجلسة الامتحانية إلى ملف Excel متقدم يحتوي على شيتات منفصلة:
    1. ملخص الجلسة والإحصائيات
    2. قائمة الحضور الشاملة
    3. شيت مخصص لكل قاعة امتحانية
    4. شيت مخصص لكل قسم علمي
    """
    session = get_object_or_404(ExamSession, pk=pk)
    hall_setups = list(session.hall_setups.select_related('room').all())
    assignments = list(session.assignments.select_related(
        'student', 'student__department', 'hall_setup', 'hall_setup__room',
        'exam_subject', 'exam_subject__subject'
    ).all().order_by('hall_setup__room__name', 'row', 'column', 'student__name'))

    # معايير الحجب والتصفية
    hide_names = request.GET.get('hide_names') == '1'
    hide_ids = request.GET.get('hide_ids') == '1'
    hide_labels = request.GET.get('hide_labels') == '1'
    hide_colors = request.GET.get('hide_colors') == '1'
    hide_stage = request.GET.get('hide_stage') == '1'
    hide_hall_info = request.GET.get('hide_hall_info') == '1'
    stage_filter = request.GET.get('stage')

    def check_student_stage(a, target):
        stg = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else '')
        stg_disp = stg if stg.startswith('المرحلة') else f"المرحلة {stg}" if stg else ''
        return stg.strip() == target.strip() or stg_disp.strip() == target.strip()

    if stage_filter and stage_filter != 'all':
        assignments = [a for a in assignments if check_student_stage(a, stage_filter)]

    wb = openpyxl.Workbook()
    
    # ── الأنماط والتنسيقات الموحدة ──
    FONT_NAME = "Segoe UI"
    
    title_font = Font(name=FONT_NAME, size=15, bold=True, color="FFFFFF")
    section_font = Font(name=FONT_NAME, size=12, bold=True, color="0F172A")
    tbl_hdr_font = Font(name=FONT_NAME, size=10, bold=True, color="FFFFFF")
    
    data_font = Font(name=FONT_NAME, size=10, color="1E293B")
    data_font_bold = Font(name=FONT_NAME, size=10, bold=True, color="0F172A")
    
    label_font = Font(name=FONT_NAME, size=10, bold=True, color="475569")
    value_font = Font(name=FONT_NAME, size=10, bold=True, color="0F172A")

    # الألوان والتعبئة
    fill_navy = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    fill_blue = PatternFill(start_color="1D4ED8", end_color="1D4ED8", fill_type="solid")
    fill_emerald = PatternFill(start_color="047857", end_color="047857", fill_type="solid")
    fill_purple = PatternFill(start_color="6D28D9", end_color="6D28D9", fill_type="solid")
    
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_seat = PatternFill(start_color="EEF2FF", end_color="EEF2FF", fill_type="solid")
    fill_subtle = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    # الحدود
    thin_gray = Side(style='thin', color='CBD5E1')
    medium_dark = Side(style='medium', color='0F172A')
    
    cell_border = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)
    header_border = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=medium_dark)

    # المحاذاة
    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    existing_titles = set()

    def sanitize_title(name, prefix=""):
        cleaned = re.sub(r'[\\/*?\[\]:]', '', str(name)).strip()
        full = f"{prefix}{cleaned}".strip()
        if not full:
            full = "ورقة"
        base = full[:28]
        cand = base
        count = 2
        while cand in existing_titles:
            cand = f"{base[:27]}_{count}"
            count += 1
        existing_titles.add(cand)
        return cand

    def format_sheet_view_and_widths(ws, min_w=10, max_w=45):
        ws.views.sheetView[0].rightToLeft = True
        ws.views.sheetView[0].showGridLines = True
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value is not None:
                    s_val = str(cell.value)
                    length = len(s_val)
                    if length > max_len:
                        max_len = length
            ws.column_dimensions[col_letter].width = max(min_w, min(max_len + 5, max_w))

    def get_soft_color(hex_str):
        """تحويل لون HEX إلى درجة باستيل ناعمة ومريحة للعين في الإكسل"""
        if not hex_str or not hex_str.startswith('#') or len(hex_str) != 7:
            return "EEF2FF"
        try:
            r = int(hex_str[1:3], 16)
            g = int(hex_str[3:5], 16)
            b = int(hex_str[5:7], 16)
            r_soft = int(r * 0.35 + 255 * 0.65)
            g_soft = int(g * 0.35 + 255 * 0.65)
            b_soft = int(b * 0.35 + 255 * 0.65)
            return f"{r_soft:02X}{g_soft:02X}{b_soft:02X}"
        except Exception:
            return "EEF2FF"

    def apply_print_setup(ws, orientation='portrait', fit_w=1, fit_h=0, title_rows=None):
        """تطبيق إعدادات الطباعة الرسمية A4 وضبط الصفحة والتكرار"""
        ws.page_setup.orientation = orientation
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = fit_w
        ws.page_setup.fitToHeight = fit_h
        ws.page_margins.left = 0.35
        ws.page_margins.right = 0.35
        ws.page_margins.top = 0.5
        ws.page_margins.bottom = 0.5
        ws.page_margins.header = 0.3
        ws.page_margins.footer = 0.3
        if title_rows:
            ws.print_title_rows = title_rows

    # ═════════════════════════════════════════════════════════════════
    # الشيت 1: ملخص الجلسة (Overview)
    # ═════════════════════════════════════════════════════════════════
    ws_summary = wb.active
    ws_summary.title = sanitize_title("ملخص الجلسة")
    ws_summary.sheet_properties.tabColor = "0F172A"

    # Banner الترويسة
    ws_summary.merge_cells("A1:G2")
    banner_cell = ws_summary["A1"]
    banner_cell.value = f"تقرير وملخص الجلسة الامتحانية — {session.name}"
    banner_cell.font = title_font
    banner_cell.fill = fill_navy
    banner_cell.alignment = align_center

    for r in range(1, 3):
        ws_summary.row_dimensions[r].height = 24
        for c in range(1, 8):
            cell = ws_summary.cell(row=r, column=c)
            cell.fill = fill_navy

    # جدول بيانات الجلسة العامة
    meta_info = [
        ("اسم الجلسة الامتحانية:", session.name, "تاريخ الامتحان:", session.date.strftime("%Y-%m-%d")),
        ("وقت بدء الامتحان:", session.start_time.strftime("%H:%M") if session.start_time else "—", 
         "وقت انتهاء الامتحان:", session.end_time.strftime("%H:%M") if session.end_time else "—"),
        ("إجمالي الطلاب الموزعين:", len(assignments), "عدد القاعات الامتحانية:", len(hall_setups)),
    ]

    curr_row = 4
    for row_data in meta_info:
        ws_summary.row_dimensions[curr_row].height = 24
        ws_summary.cell(row=curr_row, column=1, value=row_data[0]).font = label_font
        ws_summary.cell(row=curr_row, column=1).alignment = align_right
        
        ws_summary.cell(row=curr_row, column=2, value=str(row_data[1])).font = value_font
        ws_summary.cell(row=curr_row, column=2).alignment = align_right
        
        ws_summary.cell(row=curr_row, column=4, value=row_data[2]).font = label_font
        ws_summary.cell(row=curr_row, column=4).alignment = align_right
        
        ws_summary.cell(row=curr_row, column=5, value=str(row_data[3])).font = value_font
        ws_summary.cell(row=curr_row, column=5).alignment = align_right
        
        for c in range(1, 8):
            ws_summary.cell(row=curr_row, column=c).fill = fill_subtle if curr_row % 2 == 0 else fill_white
            ws_summary.cell(row=curr_row, column=c).border = cell_border
        curr_row += 1

    curr_row += 2

    # جدول 1: إحصائيات القاعات
    ws_summary.merge_cells(f"A{curr_row}:G{curr_row}")
    sec1 = ws_summary[f"A{curr_row}"]
    sec1.value = "🏛️ تفاصيل وإحصائيات القاعات الامتحانية"
    sec1.font = section_font
    sec1.alignment = align_right
    ws_summary.row_dimensions[curr_row].height = 26
    curr_row += 1

    hall_hdrs = ["ت", "اسم القاعة الامتحانية", "أبعاد القاعة (صفوف × أعمدة)", "السعة الكلية", "الطلاب الموزعون", "المقاعد الشاغرة", "نسبة الإشغال"]
    ws_summary.row_dimensions[curr_row].height = 28
    for col_idx, h_text in enumerate(hall_hdrs, 1):
        c = ws_summary.cell(row=curr_row, column=col_idx, value=h_text)
        c.font = tbl_hdr_font
        c.fill = fill_blue
        c.alignment = align_center
        c.border = header_border
    curr_row += 1

    total_cap = 0
    total_assigned_halls = 0

    for idx, hall in enumerate(hall_setups, 1):
        ws_summary.row_dimensions[curr_row].height = 22
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]
        h_assigned = len(hall_assignments)
        h_cap = hall.total_seats
        h_free = max(0, h_cap - h_assigned)
        h_rate = f"{(h_assigned / h_cap * 100):.1f}%" if h_cap > 0 else "0%"
        
        total_cap += h_cap
        total_assigned_halls += h_assigned

        row_vals = [idx, hall.room.name, f"{hall.rows} × {hall.columns}", h_cap, h_assigned, h_free, h_rate]
        row_fill = fill_zebra if idx % 2 == 0 else fill_white

        for col_idx, val in enumerate(row_vals, 1):
            c = ws_summary.cell(row=curr_row, column=col_idx, value=val)
            c.font = data_font_bold if col_idx in [2, 5] else data_font
            c.fill = row_fill
            c.border = cell_border
            c.alignment = align_right if col_idx == 2 else align_center
        curr_row += 1

    # سطر المجموع
    ws_summary.row_dimensions[curr_row].height = 24
    total_free = max(0, total_cap - total_assigned_halls)
    total_rate = f"{(total_assigned_halls / total_cap * 100):.1f}%" if total_cap > 0 else "0%"
    tot_vals = ["—", "الإجمالي الكلي للقاعات", "—", total_cap, total_assigned_halls, total_free, total_rate]
    for col_idx, val in enumerate(tot_vals, 1):
        c = ws_summary.cell(row=curr_row, column=col_idx, value=val)
        c.font = Font(name=FONT_NAME, size=10, bold=True, color="0F172A")
        c.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        c.border = header_border
        c.alignment = align_right if col_idx == 2 else align_center
    curr_row += 3

    # جدول 2: إحصائيات الأقسام والمواد
    ws_summary.merge_cells(f"A{curr_row}:E{curr_row}")
    sec2 = ws_summary[f"A{curr_row}"]
    sec2.value = "🏢 إحصائيات الأقسام العلمية والمواد"
    sec2.font = section_font
    sec2.alignment = align_right
    ws_summary.row_dimensions[curr_row].height = 26
    curr_row += 1

    dept_hdrs = ["ت", "القسم العلمي", "المرحلة الدراسية", "المادة الامتحانية", "عدد الطلاب الموزعين"]
    ws_summary.row_dimensions[curr_row].height = 28
    for col_idx, h_text in enumerate(dept_hdrs, 1):
        c = ws_summary.cell(row=curr_row, column=col_idx, value=h_text)
        c.font = tbl_hdr_font
        c.fill = fill_purple
        c.alignment = align_center
        c.border = header_border
    curr_row += 1

    # تجميع المواد والأقسام
    dept_sub_stats = {}
    for a in assignments:
        dept_name = a.student.department.name
        sub_name = a.exam_subject.subject.name if a.exam_subject and a.exam_subject.subject else "—"
        stage_val = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else "")
        stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else "—"
        
        key = (dept_name, stage_display, sub_name)
        dept_sub_stats[key] = dept_sub_stats.get(key, 0) + 1

    for idx, (key, count) in enumerate(dept_sub_stats.items(), 1):
        ws_summary.row_dimensions[curr_row].height = 22
        row_vals = [idx, key[0], key[1], key[2], count]
        row_fill = fill_zebra if idx % 2 == 0 else fill_white

        for col_idx, val in enumerate(row_vals, 1):
            c = ws_summary.cell(row=curr_row, column=col_idx, value=val)
            c.font = data_font_bold if col_idx in [2, 5] else data_font
            c.fill = row_fill
            c.border = cell_border
            c.alignment = align_right if col_idx in [2, 4] else align_center
        curr_row += 1

    format_sheet_view_and_widths(ws_summary)
    apply_print_setup(ws_summary, orientation='portrait', fit_w=1, fit_h=0)

    # ═════════════════════════════════════════════════════════════════
    # الشيتات 2+: خرائط الجلوس التفاعلية لكل قاعة (Visual Seating Grid Maps)
    # ═════════════════════════════════════════════════════════════════
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]
        hall_assignments_map = {(a.row, a.column): a for a in hall_assignments}

        ws_map = wb.create_sheet(title=sanitize_title(hall.room.name, prefix="خريطة-"))
        ws_map.sheet_properties.tabColor = "0284C7"
        ws_map.views.sheetView[0].rightToLeft = True
        ws_map.views.sheetView[0].showGridLines = True

        max_col_idx = hall.columns + 1
        last_col_letter = get_column_letter(max_col_idx)

        # 1. الترويسة الرئيسية للقاعة
        ws_map.merge_cells(f"A1:{last_col_letter}2")
        m_banner = ws_map["A1"]
        m_banner.value = f"خريطة توزيع مقاعد: {hall.room.name} — {session.name} ({session.date})"
        m_banner.font = Font(name=FONT_NAME, size=13, bold=True, color="FFFFFF")
        m_banner.fill = fill_navy
        m_banner.alignment = align_center

        for r in range(1, 3):
            ws_map.row_dimensions[r].height = 22
            for c in range(1, max_col_idx + 1):
                ws_map.cell(row=r, column=c).fill = fill_navy

        # 2. شريط السبورة (اتجاه النظر)
        ws_map.row_dimensions[4].height = 26
        ws_map.merge_cells(f"A4:{last_col_letter}4")
        board_c = ws_map["A4"]
        board_c.value = "◄ السبورة (اتجاه النظــــر) ►"
        board_c.font = Font(name=FONT_NAME, size=11, bold=True, color="FFFFFF")
        board_c.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        board_c.alignment = align_center
        for c in range(1, max_col_idx + 1):
            ws_map.cell(row=4, column=c).fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

        # 3. رؤوس الأعمدة
        ws_map.row_dimensions[5].height = 24
        hdr_cell = ws_map.cell(row=5, column=1, value="الصف \\ العمود")
        hdr_cell.font = Font(name=FONT_NAME, size=9, bold=True, color="475569")
        hdr_cell.fill = fill_subtle
        hdr_cell.alignment = align_center
        hdr_cell.border = header_border
        ws_map.column_dimensions["A"].width = 13

        for col_i in range(1, hall.columns + 1):
            c_cell = ws_map.cell(row=5, column=col_i + 1, value=f"العمود {col_i}")
            c_cell.font = Font(name=FONT_NAME, size=10, bold=True, color="0F172A")
            c_cell.fill = fill_subtle
            c_cell.alignment = align_center
            c_cell.border = header_border
            col_letter = get_column_letter(col_i + 1)
            ws_map.column_dimensions[col_letter].width = 25

        # 4. شبكة المقاعد
        for r_idx in range(hall.rows):
            excel_row = 6 + r_idx
            ws_map.row_dimensions[excel_row].height = 56
            row_letter = chr(65 + r_idx) if r_idx < 26 else f"R{r_idx + 1}"

            # تسمية الصف
            r_cell = ws_map.cell(row=excel_row, column=1, value=f"الصف {row_letter}")
            r_cell.font = Font(name=FONT_NAME, size=10, bold=True, color="0F172A")
            r_cell.fill = fill_subtle
            r_cell.alignment = align_center
            r_cell.border = cell_border

            # المقاعد
            for c_idx in range(hall.columns):
                excel_col = 2 + c_idx
                seat_cell = ws_map.cell(row=excel_row, column=excel_col)
                assign = hall_assignments_map.get((r_idx, c_idx))

                if assign:
                    st_name = assign.student.name
                    st_id = assign.student.university_id
                    seat_lbl = assign.seat_label
                    stage_val = assign.student.stage or (assign.exam_subject.subject.stage if assign.exam_subject and assign.exam_subject.subject else "")
                    stage_lbl = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ""

                    lines = []
                    if not hide_names:
                        lines.append(st_name)
                    if not hide_ids:
                        lines.append(f"🆔 {st_id}")
                    if not hide_labels:
                        lines.append(f"🪑 [{seat_lbl}]")
                    if not hide_stage and stage_lbl:
                        lines.append(f"🎓 {stage_lbl}")

                    seat_cell.value = "\n".join(lines) if lines else "—"
                    if not hide_colors:
                        soft_hex = get_soft_color(assign.exam_subject.color_code if assign.exam_subject else "#3B82F6")
                        seat_cell.fill = PatternFill(start_color=soft_hex, end_color=soft_hex, fill_type="solid")
                    else:
                        seat_cell.fill = fill_white
                    seat_cell.font = Font(name=FONT_NAME, size=9, bold=True, color="0F172A")
                    seat_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                else:
                    if hide_labels:
                        seat_cell.value = "— مقعد شاغر —"
                    else:
                        seat_cell.value = f"— مقعد شاغر —\n[{row_letter}{c_idx + 1}]"
                    seat_cell.fill = fill_zebra
                    seat_cell.font = Font(name=FONT_NAME, size=8, color="94A3B8")
                    seat_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

                seat_cell.border = cell_border

        # 5. مفتاح المواد أسفل الخريطة
        leg_row = 6 + hall.rows + 2
        ws_map.merge_cells(f"A{leg_row}:{last_col_letter}{leg_row}")
        leg_title = ws_map[f"A{leg_row}"]
        leg_title.value = "🎨 مفتاح المواد والمراحل الدراسية في هذه القاعة"
        leg_title.font = section_font
        leg_title.alignment = align_right
        ws_map.row_dimensions[leg_row].height = 24
        leg_row += 1

        hall_sub_counts = {}
        for a in hall_assignments:
            if a.exam_subject and a.exam_subject.subject:
                sid = a.exam_subject.subject.id
                if sid not in hall_sub_counts:
                    s_val = a.student.stage or a.exam_subject.subject.stage or ""
                    s_disp = s_val if s_val.startswith('المرحلة') else f"المرحلة {s_val}" if s_val else a.exam_subject.subject.name
                    hall_sub_counts[sid] = {
                        'name': a.exam_subject.subject.name,
                        'stage': s_disp,
                        'color': a.exam_subject.color_code,
                        'count': 0
                    }
                hall_sub_counts[sid]['count'] += 1

        for s_info in hall_sub_counts.values():
            ws_map.row_dimensions[leg_row].height = 22
            c_box = ws_map.cell(row=leg_row, column=1)
            soft_hex = get_soft_color(s_info['color']) if not hide_colors else "FFFFFF"
            c_box.fill = PatternFill(start_color=soft_hex, end_color=soft_hex, fill_type="solid")
            c_box.border = cell_border

            ws_map.merge_cells(f"B{leg_row}:{get_column_letter(min(4, max_col_idx))}{leg_row}")
            t_cell = ws_map.cell(row=leg_row, column=2, value=f"{s_info['stage']} - {s_info['name']} ({s_info['count']} طالب)")
            t_cell.font = data_font_bold
            t_cell.alignment = align_right
            leg_row += 1

        format_sheet_view_and_widths(ws_map, min_w=12, max_w=30)
        apply_print_setup(ws_map, orientation='landscape', fit_w=1, fit_h=1)

    # ═════════════════════════════════════════════════════════════════
    # الشيت التالي: بطاقات المقاعد الرسمية للطباعة والقص (Seat Cards)
    # ═════════════════════════════════════════════════════════════════
    ws_cards = wb.create_sheet(title=sanitize_title("بطاقات المقاعد"))
    ws_cards.sheet_properties.tabColor = "D97706"
    ws_cards.views.sheetView[0].rightToLeft = True
    ws_cards.views.sheetView[0].showGridLines = True

    ws_cards.column_dimensions["A"].width = 33
    ws_cards.column_dimensions["B"].width = 3
    ws_cards.column_dimensions["C"].width = 33
    ws_cards.column_dimensions["D"].width = 3
    ws_cards.column_dimensions["E"].width = 33

    ws_cards.merge_cells("A1:E2")
    c_banner = ws_cards["A1"]
    c_banner.value = f"بطاقات مقاعد الطلاب الرسمية — {session.name} ({session.date})"
    c_banner.font = title_font
    c_banner.fill = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")
    c_banner.alignment = align_center
    for r in range(1, 3):
        ws_cards.row_dimensions[r].height = 22
        for c in range(1, 6):
            ws_cards.cell(row=r, column=c).fill = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")

    card_border_side = Side(style='medium', color='0F172A')
    card_inner_side = Side(style='thin', color='CBD5E1')

    cards_assignments = list(assignments)
    cards_assignments.sort(key=lambda a: (a.hall_setup.room.name, a.row, a.column))

    col_map = [1, 3, 5]
    start_card_row = 4

    for idx, a in enumerate(cards_assignments):
        card_slot = idx % 3
        card_col = col_map[card_slot]
        card_row = start_card_row + (idx // 3) * 6

        stage_val = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else "")
        stage_display = stage_val if stage_val.startswith('المرحلة') else f"المرحلة {stage_val}" if stage_val else ""
        sub_name = a.exam_subject.subject.name if a.exam_subject and a.exam_subject.subject else "—"
        dept_name = a.student.department.name
        hall_name = a.hall_setup.room.name
        seat_lbl = a.seat_label

        soft_bg = get_soft_color(a.exam_subject.color_code if a.exam_subject else "#3B82F6") if not hide_colors else "FFFFFF"
        card_fill = PatternFill(start_color=soft_bg, end_color=soft_bg, fill_type="solid")

        ws_cards.row_dimensions[card_row].height = 24
        ws_cards.row_dimensions[card_row + 1].height = 24
        ws_cards.row_dimensions[card_row + 2].height = 20
        ws_cards.row_dimensions[card_row + 3].height = 20
        ws_cards.row_dimensions[card_row + 4].height = 18
        ws_cards.row_dimensions[card_row + 5].height = 14

        # 1. Header
        c1 = ws_cards.cell(row=card_row, column=card_col)
        h_parts = []
        if not hide_hall_info:
            h_parts.append(f"🏛️ {hall_name}")
        if not hide_labels:
            h_parts.append(f"🪑 المقعد: {seat_lbl}")
        c1.value = "   |   ".join(h_parts) if h_parts else "بطاقة مقعد"
        c1.font = Font(name=FONT_NAME, size=11, bold=True, color="FFFFFF")
        c1.fill = fill_navy
        c1.alignment = align_center
        c1.border = Border(left=card_border_side, right=card_border_side, top=card_border_side, bottom=card_inner_side)

        # 2. Student Name
        c2 = ws_cards.cell(row=card_row + 1, column=card_col)
        c2.value = f"👤 {a.student.name}" if not hide_names else "👤 [الاسم محجوب]"
        c2.font = Font(name=FONT_NAME, size=11, bold=True, color="0F172A")
        c2.fill = card_fill
        c2.alignment = align_center
        c2.border = Border(left=card_border_side, right=card_border_side, top=card_inner_side, bottom=card_inner_side)

        # 3. ID & Stage
        c3 = ws_cards.cell(row=card_row + 2, column=card_col)
        id_stg_parts = []
        if not hide_ids:
            id_stg_parts.append(f"🆔 {a.student.university_id}")
        if not hide_stage and stage_display:
            id_stg_parts.append(f"🎓 {stage_display}")
        c3.value = "   |   ".join(id_stg_parts) if id_stg_parts else "—"
        c3.font = Font(name=FONT_NAME, size=9.5, bold=True, color="1E293B")
        c3.fill = fill_white
        c3.alignment = align_center
        c3.border = Border(left=card_border_side, right=card_border_side, top=card_inner_side, bottom=card_inner_side)

        # 4. Subject & Dept
        c4 = ws_cards.cell(row=card_row + 3, column=card_col)
        c4.value = f"📚 {sub_name}   |   🏢 {dept_name}"
        c4.font = Font(name=FONT_NAME, size=8.5, bold=True, color="334155")
        c4.fill = fill_white
        c4.alignment = align_center
        c4.border = Border(left=card_border_side, right=card_border_side, top=card_inner_side, bottom=card_inner_side)

        # 5. Session Date
        c5 = ws_cards.cell(row=card_row + 4, column=card_col)
        c5.value = f"📅 {session.date.strftime('%Y-%m-%d')}   —   {session.name}"
        c5.font = Font(name=FONT_NAME, size=8, color="64748B")
        c5.fill = fill_subtle
        c5.alignment = align_center
        c5.border = Border(left=card_border_side, right=card_border_side, top=card_inner_side, bottom=card_border_side)

    apply_print_setup(ws_cards, orientation='portrait', fit_w=1, fit_h=0)

    # ═════════════════════════════════════════════════════════════════
    # بناء أعمدة الشيتات الجدولية بشكل ديناميكي حسب خيارات الحجب
    # ═════════════════════════════════════════════════════════════════
    def build_attendance_columns(include_hall=True):
        cols = [
            {"title": "ت", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: idx},
        ]
        if not hide_labels:
            cols.append({"title": "المقعد", "align": align_center, "bold": True, "fill_seat": True, "getter": lambda a, idx: a.seat_label})
        if not hide_names:
            cols.append({"title": "اسم الطالب الثلاثي واللقب", "align": align_right, "bold": True, "fill_seat": False, "getter": lambda a, idx: a.student.name})
        if not hide_ids:
            cols.append({"title": "الرقم الجامعي / الامتحاني", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: a.student.university_id})

        cols.append({"title": "القسم العلمي", "align": align_right, "bold": False, "fill_seat": False, "getter": lambda a, idx: a.student.department.name})

        if not hide_stage:
            def get_stg(a):
                s = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else "")
                return s if s.startswith('المرحلة') else f"المرحلة {s}" if s else "—"
            cols.append({"title": "المرحلة الدراسية", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: get_stg(a)})

        cols.append({"title": "المادة الامتحانية", "align": align_right, "bold": False, "fill_seat": False, "getter": lambda a, idx: (a.exam_subject.subject.name if a.exam_subject and a.exam_subject.subject else "—")})

        if include_hall and not hide_hall_info:
            cols.append({"title": "القاعة الامتحانية", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: a.hall_setup.room.name})

        cols.extend([
            {"title": "حالة الحضور", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: ""},
            {"title": "توقيع الطالب", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: ""},
            {"title": "ملاحظات", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: ""},
        ])
        return cols

    # ═════════════════════════════════════════════════════════════════
    # الشيت 2: قائمة الحضور الشاملة (All Students)
    # ═════════════════════════════════════════════════════════════════
    master_cols = build_attendance_columns(include_hall=True)
    total_cols = len(master_cols)
    last_col_letter_all = get_column_letter(total_cols)

    ws_all = wb.create_sheet(title=sanitize_title("قائمة الحضور الشاملة"))
    ws_all.sheet_properties.tabColor = "047857"

    # Banner
    ws_all.merge_cells(f"A1:{last_col_letter_all}2")
    ws_all["A1"] = f"قائمة الحضور الشاملة لجميع الطلاب — {session.name} ({session.date})"
    ws_all["A1"].font = title_font
    ws_all["A1"].fill = fill_emerald
    ws_all["A1"].alignment = align_center

    for r in range(1, 3):
        ws_all.row_dimensions[r].height = 24
        for c in range(1, total_cols + 1):
            ws_all.cell(row=r, column=c).fill = fill_emerald

    ws_all.row_dimensions[4].height = 28
    for col_idx, col_def in enumerate(master_cols, 1):
        c = ws_all.cell(row=4, column=col_idx, value=col_def["title"])
        c.font = tbl_hdr_font
        c.fill = fill_navy
        c.alignment = align_center
        c.border = header_border

    curr_row = 5
    for idx, a in enumerate(assignments, 1):
        ws_all.row_dimensions[curr_row].height = 24
        row_fill = fill_zebra if idx % 2 == 0 else fill_white

        for col_idx, col_def in enumerate(master_cols, 1):
            val = col_def["getter"](a, idx)
            c = ws_all.cell(row=curr_row, column=col_idx, value=val)
            c.font = data_font_bold if col_def["bold"] else data_font
            c.fill = fill_seat if (col_def["fill_seat"] and not hide_colors) else row_fill
            c.border = cell_border
            c.alignment = col_def["align"]
        curr_row += 1

    format_sheet_view_and_widths(ws_all)
    apply_print_setup(ws_all, orientation='landscape', fit_w=1, fit_h=0, title_rows='4:4')

    # ═════════════════════════════════════════════════════════════════
    # الشيتات 3+: شيت لكل قاعة امتحانية (Per-Hall Sheets)
    # ═════════════════════════════════════════════════════════════════
    hall_sheet_cols = build_attendance_columns(include_hall=False)
    total_hall_cols = len(hall_sheet_cols)
    last_col_letter_hall = get_column_letter(total_hall_cols)

    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a.hall_setup_id == hall.id]
        if stage_filter and stage_filter != 'all' and not hall_assignments:
            continue

        hall_assignments.sort(key=lambda a: (a.row, a.column))
        
        sheet_title = sanitize_title(hall.room.name, prefix="قاعة-")
        ws_hall = wb.create_sheet(title=sheet_title)
        ws_hall.sheet_properties.tabColor = "1D4ED8"

        # Banner
        ws_hall.merge_cells(f"A1:{last_col_letter_hall}2")
        ws_hall["A1"] = f"استمارة حضور وتوزيع القاعة الامتحانية: {hall.room.name}"
        ws_hall["A1"].font = title_font
        ws_hall["A1"].fill = fill_blue
        ws_hall["A1"].alignment = align_center

        for r in range(1, 3):
            ws_hall.row_dimensions[r].height = 24
            for c in range(1, total_hall_cols + 1):
                ws_hall.cell(row=r, column=c).fill = fill_blue

        # معلومات القاعة
        meta_row = 3
        ws_hall.row_dimensions[meta_row].height = 24
        ws_hall.cell(row=meta_row, column=1, value="الجلسة:").font = label_font
        ws_hall.cell(row=meta_row, column=2, value=session.name).font = value_font
        ws_hall.cell(row=meta_row, column=4, value="تاريخ الامتحان:").font = label_font
        ws_hall.cell(row=meta_row, column=5, value=session.date.strftime("%Y-%m-%d")).font = value_font
        ws_hall.cell(row=meta_row, column=7, value="عدد طلاب القاعة:").font = label_font
        ws_hall.cell(row=meta_row, column=8, value=f"{len(hall_assignments)} طالب").font = value_font

        for c in range(1, total_hall_cols + 1):
            ws_hall.cell(row=meta_row, column=c).fill = fill_subtle
            ws_hall.cell(row=meta_row, column=c).border = cell_border

        # ترويسة الجدول
        ws_hall.row_dimensions[5].height = 28
        for col_idx, col_def in enumerate(hall_sheet_cols, 1):
            c = ws_hall.cell(row=5, column=col_idx, value=col_def["title"])
            c.font = tbl_hdr_font
            c.fill = fill_navy
            c.alignment = align_center
            c.border = header_border

        curr_row = 6
        for idx, a in enumerate(hall_assignments, 1):
            ws_hall.row_dimensions[curr_row].height = 24
            row_fill = fill_zebra if idx % 2 == 0 else fill_white

            for col_idx, col_def in enumerate(hall_sheet_cols, 1):
                val = col_def["getter"](a, idx)
                c = ws_hall.cell(row=curr_row, column=col_idx, value=val)
                c.font = data_font_bold if col_def["bold"] else data_font
                c.fill = fill_seat if (col_def["fill_seat"] and not hide_colors) else row_fill
                c.border = cell_border
                c.alignment = col_def["align"]
            curr_row += 1

        # خانات التوقيع لمراقب القاعة
        curr_row += 2
        ws_hall.row_dimensions[curr_row].height = 26
        ws_hall.cell(row=curr_row, column=2, value="اسم وتوقيع مراقب القاعة: ................................................").font = Font(name=FONT_NAME, size=11, bold=True, color="0F172A")
        ws_hall.cell(row=curr_row, column=min(5, total_hall_cols), value="توقيع مسؤول اللجنة الامتحانية: ................................................").font = Font(name=FONT_NAME, size=11, bold=True, color="0F172A")

        format_sheet_view_and_widths(ws_hall)
        apply_print_setup(ws_hall, orientation='portrait', fit_w=1, fit_h=0, title_rows='5:5')

    # ═════════════════════════════════════════════════════════════════
    # الشيتات التالية: شيت لكل قسم علمي (Per-Department Sheets)
    # ═════════════════════════════════════════════════════════════════
    dept_groups = {}
    for a in assignments:
        d = a.student.department
        if d.id not in dept_groups:
            dept_groups[d.id] = {
                'name': d.name,
                'students': []
            }
        dept_groups[d.id]['students'].append(a)

    for dept_id, d_data in dept_groups.items():
        dept_students = d_data['students']
        dept_students.sort(key=lambda a: (a.hall_setup.room.name, a.row, a.column, a.student.name))

        sheet_title = sanitize_title(d_data['name'], prefix="قسم-")
        ws_dept = wb.create_sheet(title=sheet_title)
        ws_dept.sheet_properties.tabColor = "6D28D9"

        dept_cols_def = [
            {"title": "ت", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: idx},
        ]
        if not hide_names:
            dept_cols_def.append({"title": "اسم الطالب الثلاثي واللقب", "align": align_right, "bold": True, "fill_seat": False, "getter": lambda a, idx: a.student.name})
        if not hide_ids:
            dept_cols_def.append({"title": "الرقم الجامعي / الامتحاني", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: a.student.university_id})
        if not hide_stage:
            def get_stg_dept(a):
                s = a.student.stage or (a.exam_subject.subject.stage if a.exam_subject and a.exam_subject.subject else "")
                return s if s.startswith('المرحلة') else f"المرحلة {s}" if s else "—"
            dept_cols_def.append({"title": "المرحلة الدراسية", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: get_stg_dept(a)})
        if not hide_hall_info:
            dept_cols_def.append({"title": "القاعة الامتحانية", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: a.hall_setup.room.name})
        if not hide_labels:
            dept_cols_def.append({"title": "رقم المقعد", "align": align_center, "bold": True, "fill_seat": True, "getter": lambda a, idx: a.seat_label})

        dept_cols_def.extend([
            {"title": "المادة الامتحانية", "align": align_right, "bold": False, "fill_seat": False, "getter": lambda a, idx: (a.exam_subject.subject.name if a.exam_subject and a.exam_subject.subject else "—")},
            {"title": "توقيع الطالب", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: ""},
            {"title": "ملاحظات", "align": align_center, "bold": False, "fill_seat": False, "getter": lambda a, idx: ""},
        ])

        total_dept_cols = len(dept_cols_def)
        last_col_letter_dept = get_column_letter(total_dept_cols)

        # Banner
        ws_dept.merge_cells(f"A1:{last_col_letter_dept}2")
        ws_dept["A1"] = f"قوائم توزيع وحضور طلاب قسم: {d_data['name']}"
        ws_dept["A1"].font = title_font
        ws_dept["A1"].fill = fill_purple
        ws_dept["A1"].alignment = align_center

        for r in range(1, 3):
            ws_dept.row_dimensions[r].height = 24
            for c in range(1, total_dept_cols + 1):
                ws_dept.cell(row=r, column=c).fill = fill_purple

        # معلومات القسم
        meta_row = 3
        ws_dept.row_dimensions[meta_row].height = 24
        ws_dept.cell(row=meta_row, column=1, value="الجلسة:").font = label_font
        ws_dept.cell(row=meta_row, column=2, value=session.name).font = value_font
        ws_dept.cell(row=meta_row, column=4, value="تاريخ الامتحان:").font = label_font
        ws_dept.cell(row=meta_row, column=5, value=session.date.strftime("%Y-%m-%d")).font = value_font
        ws_dept.cell(row=meta_row, column=7, value="إجمالي طلاب القسم:").font = label_font
        ws_dept.cell(row=meta_row, column=8, value=f"{len(dept_students)} طالب").font = value_font

        for c in range(1, total_dept_cols + 1):
            ws_dept.cell(row=meta_row, column=c).fill = fill_subtle
            ws_dept.cell(row=meta_row, column=c).border = cell_border

        # ترويسة الجدول
        ws_dept.row_dimensions[5].height = 28
        for col_idx, col_def in enumerate(dept_cols_def, 1):
            c = ws_dept.cell(row=5, column=col_idx, value=col_def["title"])
            c.font = tbl_hdr_font
            c.fill = fill_navy
            c.alignment = align_center
            c.border = header_border

        curr_row = 6
        for idx, a in enumerate(dept_students, 1):
            ws_dept.row_dimensions[curr_row].height = 24
            row_fill = fill_zebra if idx % 2 == 0 else fill_white

            for col_idx, col_def in enumerate(dept_cols_def, 1):
                val = col_def["getter"](a, idx)
                c = ws_dept.cell(row=curr_row, column=col_idx, value=val)
                c.font = data_font_bold if col_def["bold"] else data_font
                c.fill = fill_seat if (col_def["fill_seat"] and not hide_colors) else row_fill
                c.border = cell_border
                c.alignment = col_def["align"]
            curr_row += 1

        # توقيع القسم واللجنة
        curr_row += 2
        ws_dept.row_dimensions[curr_row].height = 26
        ws_dept.cell(row=curr_row, column=2, value="توقيع رئيس القسم: ................................................").font = Font(name=FONT_NAME, size=11, bold=True, color="0F172A")
        ws_dept.cell(row=curr_row, column=min(5, total_dept_cols), value="توقيع مسؤول اللجنة الامتحانية: ................................................").font = Font(name=FONT_NAME, size=11, bold=True, color="0F172A")

        format_sheet_view_and_widths(ws_dept)
        apply_print_setup(ws_dept, orientation='portrait', fit_w=1, fit_h=0, title_rows='5:5')

    # ═════════════════════════════════════════════════════════════════
    # إعداد الاستجابة وإرسال ملف الإكسل
    # ═════════════════════════════════════════════════════════════════
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    raw_filename = f"جلسة_{session.id}_{session.name}.xlsx"
    encoded_filename = quote(raw_filename.encode('utf-8'))
    response['Content-Disposition'] = f'attachment; filename="Exam_Session_{session.id}.xlsx"; filename*=UTF-8\'\'{encoded_filename}'
    
    wb.save(response)
    return response
