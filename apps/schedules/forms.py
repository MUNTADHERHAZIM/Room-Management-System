from django import forms
from django.core.exceptions import ValidationError
from .models import Schedule
from .validators import check_room_conflict, check_instructor_conflict, check_department_off_day
from apps.rooms.models import Room


# مدد المحاضرات المتاحة
DURATION_CHOICES = [
    ('', 'اختر المدة أو أدخل وقت النهاية يدوياً'),
    ('30', '30 دقيقة'),
    ('45', '45 دقيقة'),
    ('60', 'ساعة واحدة'),
    ('90', 'ساعة ونصف'),
    ('120', 'ساعتان'),
    ('150', 'ساعتان ونصف'),
    ('180', '3 ساعات'),
]


class ScheduleForm(forms.ModelForm):
    """نموذج الحصة"""
    
    # حقل مدة المحاضرة
    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        required=False,
        label='مدة المحاضرة',
        widget=forms.Select(attrs={
            'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'id': 'id_duration'
        })
    )
    
    class Meta:
        model = Schedule
        fields = ['room', 'instructor', 'subject', 'day', 'start_time', 'end_time', 'semester', 'schedule_type', 'notes', 'is_active']
        widgets = {
            'room': forms.Select(attrs={
                'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'instructor': forms.Select(attrs={
                'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'subject': forms.Select(attrs={
                'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'day': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'time',
                'id': 'id_start_time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'time',
                'id': 'id_end_time'
            }),
            'semester': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
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
        semester = cleaned_data.get('semester', '1')
        
        if not all([room, instructor, day, start_time, end_time]):
            return cleaned_data
        
        # التحقق من الأوقات
        if start_time >= end_time:
            raise ValidationError({'end_time': 'وقت النهاية يجب أن يكون بعد وقت البداية'})
        
        exclude_id = self.instance.pk if self.instance.pk else None
        
        # التحقق من تعارض القاعة
        room_conflict = check_room_conflict(room, day, start_time, end_time, semester, exclude_id)
        if room_conflict:
            raise ValidationError({
                'room': f'القاعة محجوزة في هذا الوقت للمادة: {room_conflict.subject.name}'
            })
        
        # التحقق من تعارض الأستاذ
        instructor_conflict = check_instructor_conflict(instructor, day, start_time, end_time, semester, exclude_id)
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
    semester = forms.ChoiceField(
        choices=Schedule.SEMESTERS,
        label='الفصل الدراسي',
        initial='1',
        widget=forms.Select(attrs={
            'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        })
    )
    start_time = forms.TimeField(
        label='من الساعة',
        widget=forms.TimeInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'type': 'time',
            'id': 'id_start_time_search'
        })
    )
    
    # حقل مدة المحاضرة للبحث
    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        required=False,
        label='مدة المحاضرة',
        widget=forms.Select(attrs={
            'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'id': 'id_duration_search'
        })
    )
    
    end_time = forms.TimeField(
        label='إلى الساعة',
        widget=forms.TimeInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'type': 'time',
            'id': 'id_end_time_search'
        })
    )
    
    # فلاتر البحث المتقدم
    floor = forms.ChoiceField(
        required=False,
        label='الطابق',
        widget=forms.Select(attrs={
            'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    min_capacity = forms.IntegerField(
        required=False,
        label='الحد الأدنى للسعة',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'مثال: 30'
        })
    )
    
    max_capacity = forms.IntegerField(
        required=False,
        label='الحد الأقصى للسعة',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'مثال: 100'
        })
    )
    
    room_type = forms.ChoiceField(
        required=False,
        label='نوع القاعة',
        widget=forms.Select(attrs={
            'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    has_projector = forms.BooleanField(
        required=False,
        label='بروجكتر',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
        })
    )
    
    has_computers = forms.BooleanField(
        required=False,
        label='حاسبات',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
        })
    )
    
    has_air_conditioning = forms.BooleanField(
        required=False,
        label='تكييف',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
        })
    )
    
    has_audio_system = forms.BooleanField(
        required=False,
        label='صوتيات',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحميل خيارات الطوابق من القاعات الموجودة (بدون تكرار)
        floors = Room.objects.exclude(floor='').exclude(floor__isnull=True).values_list('floor', flat=True)
        unique_floors = sorted(set(floors))  # إزالة التكرارات وترتيبها
        floor_choices = [('', 'جميع الطوابق')] + [(f, f) for f in unique_floors]
        self.fields['floor'].choices = floor_choices
        
        # خيارات أنواع القاعات
        room_type_choices = [('', 'جميع الأنواع')] + list(Room.ROOM_TYPES)
        self.fields['room_type'].choices = room_type_choices
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        min_cap = cleaned_data.get('min_capacity')
        max_cap = cleaned_data.get('max_capacity')
        
        if start and end and start >= end:
            raise ValidationError({'end_time': 'وقت النهاية يجب أن يكون بعد وقت البداية'})
        
        if min_cap and max_cap and min_cap > max_cap:
            raise ValidationError({'max_capacity': 'الحد الأقصى يجب أن يكون أكبر من الحد الأدنى'})
        
        return cleaned_data
