from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from apps.core.decorators import editor_required
from django.utils import timezone
from datetime import date, timedelta
import calendar

from .models import Holiday, DepartmentOffDay
from .forms import HolidayForm, DepartmentOffDayForm
from apps.core.models import Department
from apps.schedules.models import Schedule


def calendar_view(request):
    """عرض التقويم الشهري"""
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # التحقق من صحة الشهر
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    # الحصول على أيام الشهر
    cal = calendar.Calendar(firstweekday=5)  # السبت أول الأسبوع
    month_days = cal.monthdayscalendar(year, month)
    
    # الحصول على العطل في هذا الشهر
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    holidays = Holiday.objects.filter(date__range=[first_day, last_day])
    holiday_dates = {h.date.day: h for h in holidays}
    
    # الحصول على الحصص لكل يوم
    schedules = Schedule.objects.filter(is_active=True).select_related(
        'room', 'subject', 'instructor'
    )
    
    # أسماء الأيام بالعربية
    day_names = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']
    month_names = [
        '', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]
    
    # بناء بيانات التقويم
    calendar_data = []
    for week in month_days:
        week_data = []
        for day_num in week:
            if day_num == 0:
                week_data.append({'day': None, 'schedules': [], 'holiday': None})
            else:
                day_date = date(year, month, day_num)
                day_of_week = day_names[day_date.weekday() + 2 if day_date.weekday() < 5 else day_date.weekday() - 5]
                day_schedules = list(schedules.filter(day=day_of_week)[:3])
                more_count = schedules.filter(day=day_of_week).count() - 3
                
                week_data.append({
                    'day': day_num,
                    'date': day_date,
                    'schedules': day_schedules,
                    'more_count': max(0, more_count),
                    'holiday': holiday_dates.get(day_num),
                    'is_today': day_date == today,
                })
        calendar_data.append(week_data)
    
    # Navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'calendar_data': calendar_data,
        'day_names': day_names,
        'month': month,
        'year': year,
        'month_name': month_names[month],
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': today,
    }
    
    return render(request, 'calendar_app/calendar.html', context)


def holiday_list(request):
    """عرض قائمة العطل"""
    holidays = Holiday.objects.all().order_by('-date')
    
    context = {
        'holidays': holidays,
    }
    
    return render(request, 'calendar_app/holidays.html', context)


@editor_required
def holiday_create(request):
    """إضافة عطلة جديدة"""
    if request.method == 'POST':
        form = HolidayForm(request.POST)
        if form.is_valid():
            holiday = form.save()
            messages.success(request, f'تم إضافة العطلة "{holiday.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'holidaysChanged'})
            return redirect('calendar_app:holidays')
    else:
        form = HolidayForm()
    
    context = {'form': form, 'title': 'إضافة عطلة جديدة'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'calendar_app/partials/holiday_form.html', context)
    
    return render(request, 'calendar_app/holiday_form.html', context)


@editor_required
def holiday_edit(request, pk):
    """تعديل عطلة"""
    holiday = get_object_or_404(Holiday, pk=pk)
    
    if request.method == 'POST':
        form = HolidayForm(request.POST, instance=holiday)
        if form.is_valid():
            holiday = form.save()
            messages.success(request, f'تم تعديل العطلة "{holiday.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'holidaysChanged'})
            return redirect('calendar_app:holidays')
    else:
        form = HolidayForm(instance=holiday)
    
    context = {'form': form, 'title': 'تعديل العطلة', 'holiday': holiday}
    
    if request.headers.get('HX-Request'):
        return render(request, 'calendar_app/partials/holiday_form.html', context)
    
    return render(request, 'calendar_app/holiday_form.html', context)


@editor_required
def holiday_delete(request, pk):
    """حذف عطلة"""
    holiday = get_object_or_404(Holiday, pk=pk)
    
    if request.method == 'POST':
        name = holiday.name
        holiday.delete()
        messages.success(request, f'تم حذف العطلة "{name}" بنجاح')
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'holidaysChanged'})
        return redirect('calendar_app:holidays')
    
    context = {'holiday': holiday}
    return render(request, 'calendar_app/holiday_delete.html', context)


def off_day_list(request):
    """عرض أيام الراحة للأقسام"""
    off_days = DepartmentOffDay.objects.select_related(
        'department', 'department__college'
    ).all()
    
    # تجميع حسب القسم
    departments = {}
    for off_day in off_days:
        if off_day.department_id not in departments:
            departments[off_day.department_id] = {
                'department': off_day.department,
                'days': []
            }
        departments[off_day.department_id]['days'].append(off_day)
    
    context = {
        'departments': departments.values(),
        'all_off_days': off_days,
    }
    
    return render(request, 'calendar_app/off_days.html', context)


@editor_required
def off_day_create(request):
    """إضافة يوم راحة"""
    if request.method == 'POST':
        form = DepartmentOffDayForm(request.POST)
        if form.is_valid():
            off_day = form.save()
            messages.success(request, f'تم إضافة يوم الراحة بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'offDaysChanged'})
            return redirect('calendar_app:off_days')
    else:
        form = DepartmentOffDayForm()
    
    context = {'form': form, 'title': 'إضافة يوم راحة'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'calendar_app/partials/off_day_form.html', context)
    
    return render(request, 'calendar_app/off_day_form.html', context)


@editor_required
def off_day_delete(request, pk):
    """حذف يوم راحة"""
    off_day = get_object_or_404(DepartmentOffDay, pk=pk)
    
    if request.method == 'POST':
        off_day.delete()
        messages.success(request, 'تم حذف يوم الراحة بنجاح')
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'offDaysChanged'})
        return redirect('calendar_app:off_days')
    
    context = {'off_day': off_day}
    return render(request, 'calendar_app/off_day_delete.html', context)
