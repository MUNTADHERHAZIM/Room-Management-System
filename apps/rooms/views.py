from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from apps.core.decorators import editor_required

from .models import Room
from .forms import RoomForm
from apps.core.models import College, Department
from apps.core.views import get_room_status

from django.utils import timezone


def room_list(request):
    """عرض قائمة القاعات"""
    rooms = Room.objects.select_related('department', 'department__college').filter(is_active=True)
    
    # الفلاتر
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    room_type = request.GET.get('room_type')
    search = request.GET.get('q', '')
    
    if college_id:
        rooms = rooms.filter(department__college_id=college_id)
    if department_id:
        rooms = rooms.filter(department_id=department_id)
    if room_type:
        rooms = rooms.filter(room_type=room_type)
    if search:
        rooms = rooms.filter(name__icontains=search)
    
    context = {
        'rooms': rooms,
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'room_types': Room.ROOM_TYPES,
        'selected_college': college_id,
        'selected_department': department_id,
        'selected_room_type': room_type,
        'search_query': search,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'rooms/partials/room_table.html', context)
    
    return render(request, 'rooms/list.html', context)


def room_detail(request, pk):
    """عرض تفاصيل قاعة"""
    room = get_object_or_404(Room.objects.select_related('department', 'department__college'), pk=pk)
    status, schedule = get_room_status(room)
    
    # جلب الحصص
    schedules = room.schedules.select_related('instructor', 'subject').order_by('day', 'start_time')
    
    context = {
        'room': room,
        'status': status,
        'current_schedule': schedule,
        'schedules': schedules,
        'title': f'جدول إشغال القاعة: {room.name}',
        'now': timezone.now(),
        'college_name': room.department.college.name,
        'department_name': room.department.name,
    }
    return render(request, 'rooms/detail.html', context)


@editor_required
def room_create(request):
    """إنشاء قاعة جديدة"""
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            messages.success(request, f'تم إنشاء القاعة "{room.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'roomsChanged'})
            return redirect('rooms:list')
    else:
        form = RoomForm()
    
    context = {'form': form, 'title': 'إضافة قاعة جديدة'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'rooms/partials/room_form.html', context)
    
    return render(request, 'rooms/form.html', context)


@editor_required
def room_edit(request, pk):
    """تعديل قاعة"""
    room = get_object_or_404(Room, pk=pk)
    
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            room = form.save()
            messages.success(request, f'تم تحديث القاعة "{room.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'roomsChanged'})
            return redirect('rooms:list')
    else:
        form = RoomForm(instance=room)
    
    context = {'form': form, 'room': room, 'title': f'تعديل القاعة: {room.name}'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'rooms/partials/room_form.html', context)
    
    return render(request, 'rooms/form.html', context)


@editor_required
def room_delete(request, pk):
    """حذف قاعة"""
    room = get_object_or_404(Room, pk=pk)
    
    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f'تم حذف القاعة "{room_name}" بنجاح')
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'roomsChanged'})
        return redirect('rooms:list')
    
    context = {'room': room}
    
    if request.headers.get('HX-Request'):
        return render(request, 'rooms/partials/room_delete_confirm.html', context)
    
    return render(request, 'rooms/delete.html', context)


def room_map(request):
    """عرض خريطة القاعات حسب الكليات والأقسام"""
    colleges = College.objects.prefetch_related(
        'departments__rooms'
    ).all()
    
    current_datetime = timezone.now()
    
    # بناء الخريطة مع حالة كل قاعة
    college_map = []
    for college in colleges:
        departments_data = []
        for department in college.departments.all():
            rooms_data = []
            for room in department.rooms.filter(is_active=True):
                status, schedule = get_room_status(room, current_datetime)
                rooms_data.append({
                    'room': room,
                    'status': status,
                    'schedule': schedule,
                })
            if rooms_data:
                departments_data.append({
                    'department': department,
                    'rooms': rooms_data,
                })
        if departments_data:
            college_map.append({
                'college': college,
                'departments': departments_data,
            })
    
    context = {
        'college_map': college_map,
        'current_time': current_datetime,
    }
    
    return render(request, 'rooms/map.html', context)
