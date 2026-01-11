from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q

from .models import Schedule
from .forms import ScheduleForm, FindRoomForm
from .validators import get_available_rooms
from apps.core.models import College, Department
from apps.rooms.models import Room
from apps.instructors.models import Instructor
from apps.subjects.models import Subject


DAY_ORDER = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
TIME_SLOTS = [f"{h:02d}:00" for h in range(7, 20)]  # 7:00 to 19:00


def schedule_list(request):
    """عرض قائمة الحصص"""
    schedules = Schedule.objects.select_related(
        'room', 'room__department', 'instructor', 'subject'
    ).filter(is_active=True)
    
    # الفلاتر
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    day = request.GET.get('day')
    instructor_id = request.GET.get('instructor')
    search = request.GET.get('q', '')
    
    if college_id:
        schedules = schedules.filter(room__department__college_id=college_id)
    if department_id:
        schedules = schedules.filter(room__department_id=department_id)
    if day:
        schedules = schedules.filter(day=day)
    if instructor_id:
        schedules = schedules.filter(instructor_id=instructor_id)
    if search:
        schedules = schedules.filter(
            Q(subject__name__icontains=search) |
            Q(instructor__name__icontains=search) |
            Q(room__name__icontains=search)
        )
    
    context = {
        'schedules': schedules.order_by('day', 'start_time'),
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'instructors': Instructor.objects.filter(is_active=True),
        'days': Schedule.DAYS,
        'selected_college': college_id,
        'selected_department': department_id,
        'selected_day': day,
        'selected_instructor': instructor_id,
        'search_query': search,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'schedules/partials/schedule_table.html', context)
    
    return render(request, 'schedules/list.html', context)


def schedule_create(request):
    """إنشاء حصة جديدة"""
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'تم إضافة الحصة بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'schedulesChanged'})
            return redirect('schedules:list')
    else:
        form = ScheduleForm()
    
    context = {
        'form': form,
        'title': 'إضافة حصة جديدة',
        'rooms': Room.objects.filter(is_active=True).select_related('department'),
        'instructors': Instructor.objects.filter(is_active=True),
        'subjects': Subject.objects.filter(is_active=True),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'schedules/partials/schedule_form.html', context)
    
    return render(request, 'schedules/form.html', context)


def schedule_edit(request, pk):
    """تعديل حصة"""
    schedule = get_object_or_404(Schedule, pk=pk)
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'تم تحديث الحصة بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'schedulesChanged'})
            return redirect('schedules:list')
    else:
        form = ScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
        'title': 'تعديل الحصة',
        'rooms': Room.objects.filter(is_active=True).select_related('department'),
        'instructors': Instructor.objects.filter(is_active=True),
        'subjects': Subject.objects.filter(is_active=True),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'schedules/partials/schedule_form.html', context)
    
    return render(request, 'schedules/form.html', context)


def schedule_delete(request, pk):
    """حذف حصة"""
    schedule = get_object_or_404(Schedule, pk=pk)
    
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'تم حذف الحصة بنجاح')
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'schedulesChanged'})
        return redirect('schedules:list')
    
    context = {'schedule': schedule}
    
    if request.headers.get('HX-Request'):
        return render(request, 'schedules/partials/schedule_delete_confirm.html', context)
    
    return render(request, 'schedules/delete.html', context)


def find_available_room(request):
    """البحث عن قاعات متاحة"""
    available_rooms = []
    searched = False
    
    if request.method == 'POST' or request.GET.get('day'):
        form = FindRoomForm(request.POST or request.GET)
        if form.is_valid():
            day = form.cleaned_data['day']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            
            available_rooms = get_available_rooms(day, start_time, end_time)
            searched = True
    else:
        form = FindRoomForm()
    
    context = {
        'form': form,
        'available_rooms': available_rooms,
        'searched': searched,
        'room_count': len(available_rooms) if searched else 0,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'schedules/partials/available_rooms.html', context)
    
    return render(request, 'schedules/find_room.html', context)


def timeline_view(request):
    """عرض الجدول الزمني (Timeline)"""
    rooms = Room.objects.filter(is_active=True).select_related('department')
    schedules = Schedule.objects.filter(is_active=True).select_related(
        'room', 'instructor', 'subject'
    )
    
    # الفلاتر
    day = request.GET.get('day', 'السبت')
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    
    if college_id:
        rooms = rooms.filter(department__college_id=college_id)
        schedules = schedules.filter(room__department__college_id=college_id)
    if department_id:
        rooms = rooms.filter(department_id=department_id)
        schedules = schedules.filter(room__department_id=department_id)
    
    schedules = schedules.filter(day=day)
    
    # تنظيم الحصص حسب القاعات
    room_schedules = {}
    for room in rooms:
        room_schedules[room.id] = {
            'room': room,
            'schedules': []
        }
    
    for schedule in schedules:
        if schedule.room_id in room_schedules:
            room_schedules[schedule.room_id]['schedules'].append(schedule)
    
    context = {
        'room_schedules': room_schedules.values(),
        'time_slots': TIME_SLOTS,
        'days': Schedule.DAYS,
        'selected_day': day,
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'selected_college': college_id,
        'selected_department': department_id,
    }
    
    return render(request, 'schedules/timeline.html', context)


def grid_view(request):
    """عرض الجدول الشبكي الأسبوعي"""
    rooms = Room.objects.filter(is_active=True).select_related('department', 'department__college')
    schedules = Schedule.objects.filter(is_active=True).select_related(
        'room', 'instructor', 'subject'
    )
    
    # الفلاتر
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    room_id = request.GET.get('room')
    
    if college_id:
        rooms = rooms.filter(department__college_id=college_id)
        schedules = schedules.filter(room__department__college_id=college_id)
    if department_id:
        rooms = rooms.filter(department_id=department_id)
        schedules = schedules.filter(room__department_id=department_id)
    if room_id:
        rooms = rooms.filter(id=room_id)
        schedules = schedules.filter(room_id=room_id)
    
    # تنظيم الحصص في شبكة
    grid_data = {}
    for room in rooms:
        grid_data[room.id] = {
            'room': room,
            'days': {day: [] for day in DAY_ORDER}
        }
    
    for schedule in schedules:
        if schedule.room_id in grid_data and schedule.day in grid_data[schedule.room_id]['days']:
            grid_data[schedule.room_id]['days'][schedule.day].append(schedule)
    
    context = {
        'grid_data': grid_data.values(),
        'days': DAY_ORDER,
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'rooms': Room.objects.filter(is_active=True),
        'selected_college': college_id,
        'selected_department': department_id,
        'selected_room': room_id,
    }
    
    return render(request, 'schedules/grid.html', context)

def day_schedule(request):
    """عرض الجدول الشامل لليوم (لكافة القاعات) - مخصص للطباعة"""
    from django.utils import timezone
    from apps.core.views import get_arabic_day
    
    current_day = get_arabic_day(timezone.now())
    day = request.GET.get('day', current_day)
    college_id = request.GET.get('college')
    
    rooms = Room.objects.filter(is_active=True).select_related('department', 'department__college')
    if college_id:
        rooms = rooms.filter(department__college_id=college_id)
        
    schedules = Schedule.objects.filter(
        is_active=True, 
        day=day
    ).select_related('room', 'instructor', 'subject').order_by('start_time')
    
    if college_id:
        schedules = schedules.filter(room__department__college_id=college_id)

    # تنظيم البيانات: قاعة -> حصص
    room_data = []
    for room in rooms:
        room_schedules = [s for s in schedules if s.room_id == room.id]
        room_data.append({
            'room': room,
            'schedules': room_schedules
        })
    
    context = {
        'day': day,
        'room_data': room_data,
        'days': DAY_ORDER,
        'colleges': College.objects.all(),
        'selected_college': college_id,
        'title': f'تقرير الجدول اليومي الشامل: يوم {day}',
        'now': timezone.now(),
    }
    
    return render(request, 'schedules/day_schedule.html', context)
