from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone

from .models import Instructor
from .forms import InstructorForm
from apps.core.models import College, Department
from apps.schedules.models import Schedule


DAY_ORDER = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']


def instructor_list(request):
    """عرض قائمة الأساتذة"""
    instructors = Instructor.objects.select_related(
        'department', 'department__college'
    ).filter(is_active=True).annotate(
        schedule_count=Count('schedules')
    )
    
    # الفلاتر
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    title = request.GET.get('title')
    search = request.GET.get('q', '')
    
    if college_id:
        instructors = instructors.filter(department__college_id=college_id)
    if department_id:
        instructors = instructors.filter(department_id=department_id)
    if title:
        instructors = instructors.filter(academic_title=title)
    if search:
        instructors = instructors.filter(name__icontains=search)
    
    context = {
        'instructors': instructors,
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'academic_titles': Instructor.ACADEMIC_TITLES,
        'selected_college': college_id,
        'selected_department': department_id,
        'selected_title': title,
        'search_query': search,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'instructors/partials/instructor_table.html', context)
    
    return render(request, 'instructors/list.html', context)


def instructor_detail(request, pk):
    """عرض تفاصيل أستاذ"""
    instructor = get_object_or_404(
        Instructor.objects.select_related('department', 'department__college'),
        pk=pk
    )
    
    schedules = instructor.schedules.select_related('room', 'subject').order_by('day', 'start_time')
    
    context = {
        'instructor': instructor,
        'schedules': schedules,
    }
    return render(request, 'instructors/detail.html', context)


def instructor_create(request):
    """إنشاء أستاذ جديد"""
    if request.method == 'POST':
        form = InstructorForm(request.POST)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f'تم إضافة الأستاذ "{instructor.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'instructorsChanged'})
            return redirect('instructors:list')
    else:
        form = InstructorForm()
    
    context = {'form': form, 'title': 'إضافة أستاذ جديد'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'instructors/partials/instructor_form.html', context)
    
    return render(request, 'instructors/form.html', context)


def instructor_edit(request, pk):
    """تعديل أستاذ"""
    instructor = get_object_or_404(Instructor, pk=pk)
    
    if request.method == 'POST':
        form = InstructorForm(request.POST, instance=instructor)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f'تم تحديث الأستاذ "{instructor.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'instructorsChanged'})
            return redirect('instructors:list')
    else:
        form = InstructorForm(instance=instructor)
    
    context = {'form': form, 'instructor': instructor, 'title': f'تعديل: {instructor.name}'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'instructors/partials/instructor_form.html', context)
    
    return render(request, 'instructors/form.html', context)


def instructor_delete(request, pk):
    """حذف أستاذ"""
    instructor = get_object_or_404(Instructor, pk=pk)
    
    if request.method == 'POST':
        name = instructor.name
        instructor.delete()
        messages.success(request, f'تم حذف الأستاذ "{name}" بنجاح')
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'instructorsChanged'})
        return redirect('instructors:list')
    
    context = {'instructor': instructor}
    
    if request.headers.get('HX-Request'):
        return render(request, 'instructors/partials/instructor_delete_confirm.html', context)
    
    return render(request, 'instructors/delete.html', context)


def instructor_schedule(request, pk):
    """عرض جدول الأستاذ الأسبوعي"""
    instructor = get_object_or_404(
        Instructor.objects.select_related('department', 'department__college'),
        pk=pk
    )
    
    # جلب الحصص مجمعة حسب اليوم
    schedules = instructor.schedules.select_related('room', 'subject').order_by('start_time')
    
    # تنظيم الحصص حسب الأيام
    schedule_by_day = {day: [] for day in DAY_ORDER}
    for schedule in schedules:
        if schedule.day in schedule_by_day:
            schedule_by_day[schedule.day].append(schedule)
    
    context = {
        'instructor': instructor,
        'schedule_by_day': schedule_by_day,
        'days': DAY_ORDER,
        'title': f'جدول الحصص للأستاذ: {instructor.name}',
        'now': timezone.now(),
        'college_name': instructor.department.college.name,
        'department_name': instructor.department.name,
    }
    
    return render(request, 'instructors/schedule.html', context)
