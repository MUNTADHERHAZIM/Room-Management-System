from django import forms
from .models import Instructor


class InstructorForm(forms.ModelForm):
    """نموذج الأستاذ"""
    
    class Meta:
        model = Instructor
        fields = [
            'name', 'academic_title', 'department', 'specialization',
            'email', 'phone', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'اسم الأستاذ'
            }),
            'academic_title': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'التخصص الأكاديمي'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'example@email.com',
                'dir': 'ltr'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '07xxxxxxxxx',
                'dir': 'ltr'
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
