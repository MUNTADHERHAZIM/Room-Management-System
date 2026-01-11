"""
منطق التحقق من التعارضات
Conflict detection logic
"""


def check_room_conflict(room, day, start_time, end_time, exclude_id=None):
    """
    التحقق من عدم وجود تعارض في القاعة
    قاعدة التداخل: a_start < b_end AND a_end > b_start
    
    Args:
        room: القاعة
        day: اليوم
        start_time: وقت البداية
        end_time: وقت النهاية
        exclude_id: معرف الحصة المستثناة (للتعديل)
    
    Returns:
        Schedule object if conflict exists, None otherwise
    """
    # التحقق من القيم الفارغة لتجنب أخطاء الاستعلام
    if room is None or day is None or start_time is None or end_time is None:
        return None
    
    from .models import Schedule
    
    conflicts = Schedule.objects.filter(
        room=room,
        day=day,
        start_time__lt=end_time,
        end_time__gt=start_time,
        is_active=True
    )
    
    if exclude_id:
        conflicts = conflicts.exclude(id=exclude_id)
    
    return conflicts.select_related('subject', 'instructor').first()


def check_instructor_conflict(instructor, day, start_time, end_time, exclude_id=None):
    """
    التحقق من عدم تعارض جدول الأستاذ
    
    Args:
        instructor: الأستاذ
        day: اليوم
        start_time: وقت البداية
        end_time: وقت النهاية
        exclude_id: معرف الحصة المستثناة (للتعديل)
    
    Returns:
        Schedule object if conflict exists, None otherwise
    """
    # التحقق من القيم الفارغة لتجنب أخطاء الاستعلام
    if instructor is None or day is None or start_time is None or end_time is None:
        return None
    
    from .models import Schedule
    
    conflicts = Schedule.objects.filter(
        instructor=instructor,
        day=day,
        start_time__lt=end_time,
        end_time__gt=start_time,
        is_active=True
    )
    
    if exclude_id:
        conflicts = conflicts.exclude(id=exclude_id)
    
    return conflicts.select_related('subject', 'room').first()


def check_department_off_day(department, day):
    """
    التحقق هل اليوم يوم راحة للقسم
    
    Args:
        department: القسم
        day: اليوم
    
    Returns:
        True if it's an off day, False otherwise
    """
    # التحقق من القيم الفارغة لتجنب أخطاء الاستعلام
    if department is None or day is None:
        return False
    
    from apps.calendar_app.models import DepartmentOffDay
    
    return DepartmentOffDay.objects.filter(
        department=department,
        day=day
    ).exists()


def get_available_rooms(day, start_time, end_time, department=None, room_type=None):
    """
    الحصول على القاعات المتاحة في وقت معين
    
    Args:
        day: اليوم
        start_time: وقت البداية
        end_time: وقت النهاية
        department: القسم (اختياري)
        room_type: نوع القاعة (اختياري)
    
    Returns:
        QuerySet of available rooms
    """
    from apps.rooms.models import Room
    from .models import Schedule
    
    # الحصص المتعارضة
    conflicting_schedules = Schedule.objects.filter(
        day=day,
        start_time__lt=end_time,
        end_time__gt=start_time,
        is_active=True
    ).values_list('room_id', flat=True)
    
    # القاعات المتاحة
    available_rooms = Room.objects.filter(is_active=True).exclude(
        id__in=conflicting_schedules
    )
    
    if department:
        available_rooms = available_rooms.filter(department=department)
    
    if room_type:
        available_rooms = available_rooms.filter(room_type=room_type)
    
    return available_rooms.select_related('department', 'department__college')
