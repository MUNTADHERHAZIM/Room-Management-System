from django import forms
from .models import Room
from apps.core.models import Department


class RoomForm(forms.ModelForm):
    """نموذج القاعة"""
    
    class Meta:
        model = Room
        fields = [
            'name', 'room_type', 'department', 'capacity', 'floor',
            'has_projector', 'has_computers', 'has_whiteboard', 'has_air_conditioning',
            'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'اسم القاعة'
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'min': 1
            }),
            'floor': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'الطابق الأول'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية...'
            }),
            'has_projector': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
            'has_computers': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
            'has_whiteboard': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
            'has_air_conditioning': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded text-blue-600 focus:ring-blue-500'
            }),
        }
