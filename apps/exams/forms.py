from django import forms
from .models import Student, ExamSession, ExamSessionSubject, HallSetup


SUBJECT_COLORS = [
    '#2563EB',  # أزرق ملكي متوازن
    '#DC2626',  # قرمزي أنيق
    '#059669',  # زمردي راقي
    '#D97706',  # كهرماني دافئ
    '#7C3AED',  # بنفسجي عصري
    '#DB2777',  # وردي أنيق
    '#0891B2',  # تركواز بحري
    '#EA580C',  # برتقالي محروق
    '#4F46E5',  # نيلي مميز
    '#475569',  # رمادي صخري أنيق
]



class StudentForm(forms.ModelForm):
    """نموذج إضافة/تعديل طالب"""

    class Meta:
        model = Student
        fields = ['name', 'university_id', 'department', 'stage', 'family_name', 'phone', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'الاسم الكامل'
            }),
            'university_id': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'الرقم الجامعي'
            }),
            'department': forms.Select(attrs={
                'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'stage': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'family_name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'اللقب العائلي (اختياري)'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'رقم الهاتف'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'ملاحظات...'
            }),
        }


class StudentImportForm(forms.Form):
    """نموذج استيراد طلاب من Excel"""

    file = forms.FileField(
        label='ملف Excel',
        help_text='يجب أن يحتوي على أعمدة: الاسم، الرقم الجامعي، القسم، المرحلة',
        widget=forms.FileInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300',
            'accept': '.xlsx,.xls,.csv'
        })
    )
    department = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='القسم (اختياري — لتعيين قسم افتراضي)',
        widget=forms.Select(attrs={
            'class': 'tom-select w-full rounded-lg border-gray-300'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.core.models import Department
        self.fields['department'].queryset = Department.objects.all()


class ExamSessionForm(forms.ModelForm):
    """نموذج جلسة امتحانية"""

    class Meta:
        model = ExamSession
        fields = ['name', 'date', 'start_time', 'end_time', 'semester', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'مثال: امتحان نهاية الفصل الأول'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'time'
            }),
            'semester': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'ملاحظات...'
            }),
        }


class HallSetupForm(forms.ModelForm):
    """نموذج تهيئة قاعة لجلسة امتحانية"""

    class Meta:
        model = HallSetup
        fields = [
            'room', 'rows', 'columns', 'seat_type', 'spacing_mode',
            'prevent_same_subject_adjacent', 'prevent_same_department_adjacent',
            'prevent_same_family_adjacent'
        ]
        widgets = {
            'room': forms.Select(attrs={
                'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'rows': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'min': 1, 'max': 50
            }),
            'columns': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'min': 1, 'max': 50
            }),
            'seat_type': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'spacing_mode': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'prevent_same_subject_adjacent': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
            'prevent_same_department_adjacent': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
            'prevent_same_family_adjacent': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
        }


class AddSubjectToSessionForm(forms.Form):
    """إضافة مادة لجلسة امتحانية"""

    subject = forms.ModelChoiceField(
        queryset=None,
        label='المادة',
        widget=forms.Select(attrs={
            'class': 'tom-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        })
    )
    color_code = forms.CharField(
        max_length=7,
        initial='#3B82F6',
        label='لون التمييز',
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full rounded-lg border-gray-300',
            'type': 'color'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.subjects.models import Subject
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True)


class AddStudentsToSubjectForm(forms.Form):
    """إضافة طلاب لمادة في جلسة"""

    students = forms.ModelMultipleChoiceField(
        queryset=None,
        label='الطلاب',
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox rounded text-blue-600'
        })
    )

    def __init__(self, *args, department=None, stage=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Student.objects.filter(is_active=True)
        if department:
            qs = qs.filter(department=department)
        if stage:
            qs = qs.filter(stage=stage)
        self.fields['students'].queryset = qs
