from django import forms
from django.core.exceptions import ValidationError
from .models import Schedule
from .validators import check_room_conflict, check_instructor_conflict, check_department_off_day


class ScheduleForm(forms.ModelForm):
    """نموذج الحصة"""
    
    class Meta:
        model = Schedule
        fields = ['room', 'instructor', 'subject', 'day', 'start_time', 'end_time', 'schedule_type', 'notes', 'is_active']
        widgets = {
            'room': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'instructor': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'day': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'time'
            }),
            'schedule_type': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        instructor = cleaned_data.get('instructor')
        day = cleaned_data.get('day')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if not all([room, instructor, day, start_time, end_time]):
            return cleaned_data
        
        # التحقق من الأوقات
        if start_time >= end_time:
            raise ValidationError({'end_time': 'وقت النهاية يجب أن يكون بعد وقت البداية'})
        
        exclude_id = self.instance.pk if self.instance.pk else None
        
        # التحقق من تعارض القاعة
        room_conflict = check_room_conflict(room, day, start_time, end_time, exclude_id)
        if room_conflict:
            raise ValidationError({
                'room': f'القاعة محجوزة في هذا الوقت للمادة: {room_conflict.subject.name}'
            })
        
        # التحقق من تعارض الأستاذ
        instructor_conflict = check_instructor_conflict(instructor, day, start_time, end_time, exclude_id)
        if instructor_conflict:
            raise ValidationError({
                'instructor': f'الأستاذ لديه حصة أخرى في هذا الوقت: {instructor_conflict.subject.name}'
            })
        
        # التحقق من يوم الراحة
        if check_department_off_day(room.department, day):
            raise ValidationError({
                'day': f'يوم {day} هو يوم راحة لقسم {room.department.name}'
            })
        
        return cleaned_data


class FindRoomForm(forms.Form):
    """نموذج البحث عن قاعة متاحة"""
    
    day = forms.ChoiceField(
        choices=Schedule.DAYS,
        label='اليوم',
        widget=forms.Select(attrs={
            'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        })
    )
    start_time = forms.TimeField(
        label='من الساعة',
        widget=forms.TimeInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'type': 'time'
        })
    )
    end_time = forms.TimeField(
        label='إلى الساعة',
        widget=forms.TimeInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'type': 'time'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        
        if start and end and start >= end:
            raise ValidationError({'end_time': 'وقت النهاية يجب أن يكون بعد وقت البداية'})
        
        return cleaned_data
