from django import forms
from .models import Holiday, DepartmentOffDay


class HolidayForm(forms.ModelForm):
    """نموذج العطلة"""
    
    class Meta:
        model = Holiday
        fields = ['name', 'date', 'description', 'recurring']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'اسم العطلة'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'وصف العطلة...'
            }),
            'recurring': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
        }


class DepartmentOffDayForm(forms.ModelForm):
    """نموذج يوم الراحة"""
    
    class Meta:
        model = DepartmentOffDay
        fields = ['department', 'day', 'notes']
        widgets = {
            'department': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'day': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'ملاحظات...'
            }),
        }
