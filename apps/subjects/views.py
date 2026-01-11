from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse

from .models import Subject
from .forms import SubjectForm
from apps.core.models import College, Department


def subject_list(request):
    """عرض قائمة المواد"""
    subjects = Subject.objects.select_related('department', 'department__college').filter(is_active=True)
    
    # الفلاتر
    college_id = request.GET.get('college')
    department_id = request.GET.get('department')
    stage = request.GET.get('stage')
    search = request.GET.get('q', '')
    
    if college_id:
        subjects = subjects.filter(department__college_id=college_id)
    if department_id:
        subjects = subjects.filter(department_id=department_id)
    if stage:
        subjects = subjects.filter(stage=stage)
    if search:
        subjects = subjects.filter(name__icontains=search)
    
    context = {
        'subjects': subjects,
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'stages': Subject.STAGES,
        'selected_college': college_id,
        'selected_department': department_id,
        'selected_stage': stage,
        'search_query': search,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'subjects/partials/subject_table.html', context)
    
    return render(request, 'subjects/list.html', context)


def subject_create(request):
    """إنشاء مادة جديدة"""
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            messages.success(request, f'تم إضافة المادة "{subject.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'subjectsChanged'})
            return redirect('subjects:list')
    else:
        form = SubjectForm()
    
    context = {'form': form, 'title': 'إضافة مادة جديدة'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'subjects/partials/subject_form.html', context)
    
    return render(request, 'subjects/form.html', context)


def subject_edit(request, pk):
    """تعديل مادة"""
    subject = get_object_or_404(Subject, pk=pk)
    
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            subject = form.save()
            messages.success(request, f'تم تحديث المادة "{subject.name}" بنجاح')
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'subjectsChanged'})
            return redirect('subjects:list')
    else:
        form = SubjectForm(instance=subject)
    
    context = {'form': form, 'subject': subject, 'title': f'تعديل: {subject.name}'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'subjects/partials/subject_form.html', context)
    
    return render(request, 'subjects/form.html', context)


def subject_delete(request, pk):
    """حذف مادة"""
    subject = get_object_or_404(Subject, pk=pk)
    
    if request.method == 'POST':
        name = subject.name
        subject.delete()
        messages.success(request, f'تم حذف المادة "{name}" بنجاح')
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'subjectsChanged'})
        return redirect('subjects:list')
    
    context = {'subject': subject}
    
    if request.headers.get('HX-Request'):
        return render(request, 'subjects/partials/subject_delete_confirm.html', context)
    
    return render(request, 'subjects/delete.html', context)
