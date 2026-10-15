from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import College, Department
from apps.rooms.models import Room
from apps.schedules.models import Schedule
from apps.calendar_app.models import Holiday
from apps.instructors.models import Instructor
from apps.subjects.models import Subject
from django.db.models import Count, Sum, Q, Subquery, OuterRef, Exists


# أسماء الأيام بالعربية
DAY_NAMES = {
    5: 'السبت',
    6: 'الأحد',
    0: 'الإثنين',
    1: 'الثلاثاء',
    2: 'الأربعاء',
    3: 'الخميس',
    4: 'الجمعة',
}


def get_arabic_day(dt=None):
    """الحصول على اسم اليوم بالعربية"""
    if dt is None:
        dt = timezone.localtime(timezone.now())
    return DAY_NAMES.get(dt.weekday(), '')


def get_rooms_with_status_bulk(rooms_qs, current_datetime=None):
    """
    حساب حالة جميع القاعات دفعة واحدة بدلاً من قاعة قاعة (تحسين أداء جذري).
    يدعم الحصص الدراسية والجلسات الامتحانية.
    """
    if current_datetime is None:
        current_datetime = timezone.localtime(timezone.now())

    current_day = get_arabic_day(current_datetime)
    current_time = current_datetime.time()
    current_date = current_datetime.date()

    # 1. فحص العطلة مرة واحدة فقط
    is_holiday = Holiday.objects.filter(date=current_date).exists()

    if is_holiday:
        return [{'room': room, 'status': 'holiday', 'schedule': None, 'is_exam': False} for room in rooms_qs]

    # 2. جلب جميع الحصص الجارية حالياً لكل القاعات (استعلام واحد)
    busy_schedules = Schedule.objects.filter(
        room__in=rooms_qs,
        day=current_day,
        start_time__lte=current_time,
        end_time__gt=current_time,
        is_active=True,
    ).select_related('instructor', 'subject', 'room')

    busy_map = {}
    for s in busy_schedules:
        if s.room_id not in busy_map:
            busy_map[s.room_id] = s

    # 3. جلب جميع الحصص القادمة خلال 60 دقيقة (استعلام واحد)
    soon_time = (current_datetime + timedelta(minutes=60)).time()
    upcoming_schedules = Schedule.objects.filter(
        room__in=rooms_qs,
        day=current_day,
        start_time__gt=current_time,
        start_time__lte=soon_time,
        is_active=True,
    ).select_related('instructor', 'subject', 'room')

    soon_map = {}
    for s in upcoming_schedules:
        if s.room_id not in soon_map:
            soon_map[s.room_id] = s

    # 4. جلب إعدادات الجلسات الامتحانية المرتبطة بالقاعات
    from apps.exams.models import HallSetup
    exam_setups = HallSetup.objects.filter(
        room__in=rooms_qs,
    ).select_related('session', 'room').annotate(
        assigned_count=Count('assignments')
    ).order_by('-session__date', '-session__start_time')

    exam_busy_map = {}
    exam_soon_map = {}
    exam_today_map = {}
    latest_exam_map = {}

    for hs in exam_setups:
        sess = hs.session
        r_id = hs.room_id
        # حفظ أحدث/أقرب امتحان للقاعة دائماً للعرض
        if r_id not in latest_exam_map:
            latest_exam_map[r_id] = hs

        if sess.date == current_date:
            if sess.start_time <= current_time and sess.end_time > current_time:
                exam_busy_map[r_id] = hs
            elif current_time < sess.start_time <= soon_time:
                exam_soon_map[r_id] = hs
            elif r_id not in exam_today_map:
                exam_today_map[r_id] = hs

    # 5. تجميع النتائج
    results = []
    for room in rooms_qs:
        item = {
            'room': room,
            'is_exam': False,
            'exam_session': None,
            'exam_setup': None,
            'exam_assigned_count': 0,
            'today_exam': exam_today_map.get(room.id).session if room.id in exam_today_map else None,
            'today_exam_count': exam_today_map.get(room.id).assigned_count if room.id in exam_today_map else 0,
            'latest_exam': latest_exam_map.get(room.id).session if room.id in latest_exam_map else None,
            'latest_exam_count': latest_exam_map.get(room.id).assigned_count if room.id in latest_exam_map else 0,
        }

        # الأولوية 1: امتحان جاري الآن
        if room.id in exam_busy_map:
            hs = exam_busy_map[room.id]
            item.update({
                'status': 'busy',
                'is_exam': True,
                'exam_session': hs.session,
                'exam_setup': hs,
                'exam_assigned_count': hs.assigned_count,
                'schedule': None,
            })
        # الأولوية 2: حصة دراسية جارية الآن
        elif room.id in busy_map:
            item.update({
                'status': 'busy',
                'is_exam': False,
                'schedule': busy_map[room.id],
            })
        # الأولوية 3: امتحان قادم قريباً (خلال 60 دقيقة)
        elif room.id in exam_soon_map:
            hs = exam_soon_map[room.id]
            item.update({
                'status': 'soon',
                'is_exam': True,
                'exam_session': hs.session,
                'exam_setup': hs,
                'exam_assigned_count': hs.assigned_count,
                'schedule': None,
            })
        # الأولوية 4: حصة دراسية قادمة قريباً
        elif room.id in soon_map:
            item.update({
                'status': 'soon',
                'is_exam': False,
                'schedule': soon_map[room.id],
            })
        # متاح
        else:
            item.update({
                'status': 'free',
                'is_exam': False,
                'schedule': None,
            })

        results.append(item)

    return results


# دالة قديمة تبقى للاستخدام في حالات معينة (قاعة واحدة فقط)
def get_room_status(room, current_datetime=None):
    """حساب حالة قاعة واحدة (استخدم get_rooms_with_status_bulk للقوائم)"""
    if current_datetime is None:
        current_datetime = timezone.localtime(timezone.now())

    current_day = get_arabic_day(current_datetime)
    current_time = current_datetime.time()
    current_date = current_datetime.date()

    if Holiday.objects.filter(date=current_date).exists():
        return 'holiday', None

    current_schedule = Schedule.objects.filter(
        room=room, day=current_day,
        start_time__lte=current_time, end_time__gt=current_time,
        is_active=True,
    ).select_related('instructor', 'subject').first()

    if current_schedule:
        return 'busy', current_schedule

    soon_time = (current_datetime + timedelta(minutes=60)).time()
    upcoming = Schedule.objects.filter(
        room=room, day=current_day,
        start_time__gt=current_time, start_time__lte=soon_time,
        is_active=True,
    ).select_related('instructor', 'subject').first()

    if upcoming:
        return 'soon', upcoming

    return 'free', None


@login_required
def dashboard(request):
    """الصفحة الرئيسية - لوحة التحكم (محسّنة)"""
    colleges = College.objects.all()
    departments = Department.objects.all()
    rooms = Room.objects.select_related('department', 'department__college').filter(is_active=True)

    # الفلاتر
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    room_type = request.GET.get('room_type')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q', '')

    if college_id:
        rooms = rooms.filter(department__college_id=college_id)
        departments = departments.filter(college_id=college_id)

    if department_id:
        rooms = rooms.filter(department_id=department_id)

    if room_type:
        rooms = rooms.filter(room_type=room_type)

    if search_query:
        rooms = rooms.filter(name__icontains=search_query)

    # ✅ حساب حالة كل القاعات دفعة واحدة (3 استعلامات بدل مئات)
    current_datetime = timezone.localtime(timezone.now())
    all_rooms_status = get_rooms_with_status_bulk(rooms, current_datetime)

    # تطبيق فلتر الحالة
    if status_filter == 'exam':
        rooms_with_status = [
            r for r in all_rooms_status
            if r.get('is_exam') or r.get('today_exam') or r.get('latest_exam')
        ]
    elif status_filter:
        rooms_with_status = [r for r in all_rooms_status if r['status'] == status_filter]
    else:
        rooms_with_status = all_rooms_status

    # إحصائيات
    stats = {
        'total': len(all_rooms_status),
        'free': sum(1 for r in all_rooms_status if r['status'] == 'free'),
        'busy': sum(1 for r in all_rooms_status if r['status'] == 'busy'),
        'soon': sum(1 for r in all_rooms_status if r['status'] == 'soon'),
        'exams': sum(1 for r in all_rooms_status if r.get('is_exam') or r.get('today_exam') or r.get('latest_exam')),
    }

    context = {
        'rooms_with_status': rooms_with_status,
        'colleges': colleges,
        'departments': departments,
        'room_types': Room.ROOM_TYPES,
        'stats': stats,
        'current_time': current_datetime,
        'current_day': get_arabic_day(current_datetime),
        'selected_college': college_id,
        'selected_department': department_id,
        'selected_room_type': room_type,
        'selected_status': status_filter,
        'search_query': search_query,
    }

    # HTMX partial response
    if request.headers.get('HX-Request'):
        return render(request, 'dashboard/partials/room_cards.html', context)

    return render(request, 'dashboard/index.html', context)


def get_departments(request, college_id):
    """API للحصول على أقسام كلية معينة"""
    departments = Department.objects.filter(college_id=college_id).values('id', 'name')
    return JsonResponse(list(departments), safe=False)


def server_time(request):
    """API للحصول على وقت الخادم"""
    now = timezone.localtime(timezone.now())

    if request.headers.get('HX-Request'):
        return render(request, 'core/partials/server_time.html', {
            'current_time': now,
            'current_day': get_arabic_day(now),
        })

    return JsonResponse({
        'time': now.strftime('%H:%M:%S'),
        'date': now.strftime('%Y-%m-%d'),
        'day': get_arabic_day(now),
        'timestamp': now.isoformat(),
    })


@login_required
def statistics_view(request):
    """عرض الإحصائيات الشاملة للنظام (محسّنة)"""
    # الإحصائيات الأساسية
    stats = {
        'rooms_count': Room.objects.count(),
        'instructors_count': Instructor.objects.count(),
        'subjects_count': Subject.objects.count(),
        'schedules_count': Schedule.objects.count(),
        'colleges_count': College.objects.count(),
        'departments_count': Department.objects.count(),
    }

    # توزيع القاعات حسب النوع
    room_types_data = Room.objects.values('room_type').annotate(count=Count('id'))
    room_types_labels = [dict(Room.ROOM_TYPES).get(item['room_type'], item['room_type']) for item in room_types_data]
    room_types_values = [item['count'] for item in room_types_data]

    # توزيع الحصص حسب الأيام
    days_data = Schedule.objects.values('day').annotate(count=Count('id'))
    day_order = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    days_labels = day_order
    days_dict = {item['day']: item['count'] for item in days_data}
    days_values = [days_dict.get(day, 0) for day in day_order]

    # أكثر الأقسام نشاطاً (حسب عدد الحصص)
    dept_activity = Department.objects.annotate(
        schedule_count=Count('rooms__schedules')
    ).order_by('-schedule_count')[:5]
    dept_labels = [dept.name for dept in dept_activity]
    dept_values = [dept.schedule_count for dept in dept_activity]

    # أكثر الأساتذة إعطاءً للحصص
    top_instructors = Instructor.objects.annotate(
        sessions=Count('schedules')
    ).order_by('-sessions')[:5]

    # ✅ نسبة إشغال القاعات الآن (محسّنة: استعلام واحد بدل حلقة)
    current_datetime = timezone.localtime(timezone.now())
    current_day = get_arabic_day(current_datetime)
    current_time = current_datetime.time()
    
    total_rooms = Room.objects.filter(is_active=True).count()
    busy_count = Schedule.objects.filter(
        is_active=True,
        day=current_day,
        start_time__lte=current_time,
        end_time__gt=current_time,
    ).values('room_id').distinct().count()

    occupancy_rate = (busy_count / total_rooms * 100) if total_rooms > 0 else 0

    stats_cards = [
        ('إجمالي القاعات', stats['rooms_count'], 'blue', '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5"/></svg>'),
        ('الأساتذة', stats['instructors_count'], 'indigo', '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>'),
        ('المواد', stats['subjects_count'], 'emerald', '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>'),
        ('الحصص المجدولة', stats['schedules_count'], 'amber', '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>'),
        ('الكليات', stats['colleges_count'], 'rose', '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>'),
        ('الأقسام', stats['departments_count'], 'purple', '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg>'),
    ]

    context = {
        'stats': stats,
        'stats_cards': stats_cards,
        'room_types_labels': room_types_labels,
        'room_types_values': room_types_values,
        'days_labels': days_labels,
        'days_values': days_values,
        'dept_labels': dept_labels,
        'dept_values': dept_values,
        'top_instructors': top_instructors,
        'occupancy_rate': round(occupancy_rate, 1),
        'busy_count': busy_count,
        'free_count': total_rooms - busy_count,
    }

    return render(request, 'core/statistics.html', context)


def login_view(request):
    """تسجيل الدخول للمسؤولين"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'أهلاً بك يا {user.get_full_name() or user.username}')
                return redirect('core:dashboard')
            else:
                messages.error(request, 'خطأ في اسم المستخدم أو كلمة المرور')
        else:
            messages.error(request, 'بيانات تسجيل الدخول غير صحيحة')
    else:
        form = AuthenticationForm()
        
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """تسجيل الخروج"""
    logout(request)
    messages.info(request, 'تم تسجيل الخروج بنجاح')
    return redirect('core:login')


# ==========================================
# 🔑 بوابة إدارة الحسابات والصلاحيات (RBAC Portal)
# ==========================================

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from .decorators import permission_required


@login_required
@permission_required('can_manage_users')
def user_list_view(request):
    """عرض قائمة جميع الحسابات والصلاحيات"""
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    
    # الإحصائيات
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    blocked_users = users.filter(is_active=False).count()
    admin_users = UserProfile.objects.filter(role='admin').count()

    context = {
        'users_list': users,
        'total_users': total_users,
        'active_users': active_users,
        'blocked_users': blocked_users,
        'admin_users': admin_users,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    return render(request, 'core/users/list.html', context)


@login_required
@permission_required('can_manage_users')
def create_user_view(request):
    """إنشاء حساب مستخدم جديد وتعيين الصلاحيات"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'data_entry')
        notes = request.POST.get('notes', '').strip()

        if not username or not password:
            messages.error(request, 'يرجى إدخال اسم المستخدم وكلمة المرور.')
            return redirect('core:user_list')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'اسم المستخدم "{username}" مستخدم بالفعل.')
            return redirect('core:user_list')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.notes = notes

        if role != 'custom':
            profile.apply_role_defaults()
        else:
            profile.can_view_schedules = request.POST.get('can_view_schedules') == 'on'
            profile.can_manage_schedules = request.POST.get('can_manage_schedules') == 'on'
            profile.can_access_attendance = request.POST.get('can_access_attendance') == 'on'
            profile.can_manage_attendance = request.POST.get('can_manage_attendance') == 'on'
            profile.can_access_exams = request.POST.get('can_access_exams') == 'on'
            profile.can_manage_rooms = request.POST.get('can_manage_rooms') == 'on'
            profile.can_manage_instructors = request.POST.get('can_manage_instructors') == 'on'
            profile.can_manage_subjects = request.POST.get('can_manage_subjects') == 'on'
            profile.can_manage_users = request.POST.get('can_manage_users') == 'on'

        profile.save()

        messages.success(request, f'تم إنشاء الحساب "{username}" بنجاح وتعيين الصلاحيات.')
        return redirect('core:user_list')

    return redirect('core:user_list')


@login_required
@permission_required('can_manage_users')
def update_user_permissions_view(request, user_id):
    """تحديث صلاحيات مستخدم محدد"""
    target_user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        role = request.POST.get('role', profile.role)
        profile.role = role
        profile.notes = request.POST.get('notes', profile.notes)

        first_name = request.POST.get('first_name', target_user.first_name)
        last_name = request.POST.get('last_name', target_user.last_name)
        email = request.POST.get('email', target_user.email)
        target_user.first_name = first_name
        target_user.last_name = last_name
        target_user.email = email
        target_user.save()

        if role != 'custom':
            profile.apply_role_defaults()
        else:
            profile.can_view_schedules = request.POST.get('can_view_schedules') == 'on'
            profile.can_manage_schedules = request.POST.get('can_manage_schedules') == 'on'
            profile.can_access_attendance = request.POST.get('can_access_attendance') == 'on'
            profile.can_manage_attendance = request.POST.get('can_manage_attendance') == 'on'
            profile.can_access_exams = request.POST.get('can_access_exams') == 'on'
            profile.can_manage_rooms = request.POST.get('can_manage_rooms') == 'on'
            profile.can_manage_instructors = request.POST.get('can_manage_instructors') == 'on'
            profile.can_manage_subjects = request.POST.get('can_manage_subjects') == 'on'
            profile.can_manage_users = request.POST.get('can_manage_users') == 'on'

        profile.save()
        messages.success(request, f'تم تحديث صلاحيات الحساب "{target_user.username}" بنجاح.')
        return redirect('core:user_list')

    return redirect('core:user_list')


@login_required
@permission_required('can_manage_users')
def toggle_user_status_view(request, user_id):
    """تفعيل أو حظر حساب مستخدم"""
    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, 'لا يمكنك حظر حسابك الحالي.')
        return redirect('core:user_list')

    target_user.is_active = not target_user.is_active
    target_user.save()

    status_str = "تفعيل" if target_user.is_active else "حظر"
    messages.success(request, f'تم {status_str} حساب "{target_user.username}" بنجاح.')
    return redirect('core:user_list')


@login_required
@permission_required('can_manage_users')
def reset_user_password_view(request, user_id):
    """إعادة تعيين كلمة مرور مستخدم"""
    target_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        if not new_password or len(new_password) < 4:
            messages.error(request, 'كلمة المرور يجب أن لا تقل عن 4 أحرف.')
            return redirect('core:user_list')

        target_user.set_password(new_password)
        target_user.save()
        messages.success(request, f'تم تعيين كلمة المرور الجديدة للحساب "{target_user.username}" بنجاح.')
        return redirect('core:user_list')

    return redirect('core:user_list')


@login_required
@permission_required('can_manage_users')
def delete_user_view(request, user_id):
    """حذف حساب مستخدم"""
    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, 'لا يمكنك حذف حسابك الحالي.')
        return redirect('core:user_list')

    username = target_user.username
    target_user.delete()
    messages.success(request, f'تم حذف الحساب "{username}" نهائياً من النظام.')
    return redirect('core:user_list')
