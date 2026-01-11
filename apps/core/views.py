from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import College, Department
from apps.rooms.models import Room
from apps.schedules.models import Schedule
from apps.calendar_app.models import Holiday
from apps.instructors.models import Instructor
from apps.subjects.models import Subject
from django.db.models import Count, Sum


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


def get_room_status(room, current_datetime=None):
    """
    حساب حالة القاعة:
    - free: متاحة
    - busy: مشغولة حالياً
    - soon: ستبدأ حصة خلال 60 دقيقة
    - holiday: عطلة
    """
    if current_datetime is None:
        current_datetime = timezone.localtime(timezone.now())
    
    current_day = get_arabic_day(current_datetime)
    current_time = current_datetime.time()
    current_date = current_datetime.date()
    
    # التحقق من العطل
    if Holiday.objects.filter(date=current_date).exists():
        return 'holiday', None
    
    # التحقق من الإشغال الحالي
    current_schedule = Schedule.objects.filter(
        room=room,
        day=current_day,
        start_time__lte=current_time,
        end_time__gt=current_time
    ).select_related('instructor', 'subject').first()
    
    if current_schedule:
        return 'busy', current_schedule
    
    # التحقق من حصة قريبة (خلال 60 دقيقة)
    soon_datetime = current_datetime + timedelta(minutes=60)
    soon_time = soon_datetime.time()
    
    upcoming = Schedule.objects.filter(
        room=room,
        day=current_day,
        start_time__gt=current_time,
        start_time__lte=soon_time
    ).select_related('instructor', 'subject').first()
    
    if upcoming:
        return 'soon', upcoming
    
    return 'free', None


def dashboard(request):
    """الصفحة الرئيسية - لوحة التحكم"""
    colleges = College.objects.all()
    departments = Department.objects.all()
    rooms = Room.objects.select_related('department', 'department__college').all()
    
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
    
    # حساب حالة كل قاعة
    current_datetime = timezone.localtime(timezone.now())
    rooms_with_status = []
    
    for room in rooms:
        status, schedule = get_room_status(room, current_datetime)
        
        if status_filter and status != status_filter:
            continue
        
        rooms_with_status.append({
            'room': room,
            'status': status,
            'schedule': schedule,
        })
    
    # إحصائيات
    stats = {
        'total': len(rooms_with_status),
        'free': len([r for r in rooms_with_status if r['status'] == 'free']),
        'busy': len([r for r in rooms_with_status if r['status'] == 'busy']),
        'soon': len([r for r in rooms_with_status if r['status'] == 'soon']),
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


def statistics_view(request):
    """عرض الإحصائيات الشاملة للنظام"""
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
    # ترتيب الأيام حسب اليوم الأسبوعي
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

    # نسبة إشغال القاعات الآن
    current_datetime = timezone.localtime(timezone.now())
    rooms = Room.objects.all()
    busy_count = 0
    for room in rooms:
        status, _ = get_room_status(room, current_datetime)
        if status == 'busy':
            busy_count += 1
    
    occupancy_rate = (busy_count / len(rooms) * 100) if rooms.exists() else 0

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
        'free_count': len(rooms) - busy_count,
    }

    return render(request, 'core/statistics.html', context)

