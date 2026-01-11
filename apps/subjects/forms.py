from django import forms
from .models import Subject


class SubjectForm(forms.ModelForm):
    """نموذج المادة"""
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'department', 'stage', 'hours_per_week', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'اسم المادة'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'CS101'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'stage': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'hours_per_week': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'min': 1,
                'max': 20
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'وصف المادة...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
        }
