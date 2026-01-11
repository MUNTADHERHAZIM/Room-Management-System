from django.db import models
from apps.core.models import Department


class Instructor(models.Model):
    """نموذج الأستاذ"""
    
    ACADEMIC_TITLES = [
        ('أستاذ', 'أستاذ'),
        ('أستاذ_مساعد', 'أستاذ مساعد'),
        ('مدرس', 'مدرس'),
        ('مدرس_مساعد', 'مدرس مساعد'),
        ('معيد', 'معيد'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='اسم الأستاذ')
    academic_title = models.CharField(
        max_length=50,
        choices=ACADEMIC_TITLES,
        default='مدرس',
        verbose_name='اللقب العلمي'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='instructors',
        verbose_name='القسم'
    )
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    specialization = models.CharField(max_length=200, blank=True, verbose_name='التخصص')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'أستاذ'
        verbose_name_plural = 'الأساتذة'
        ordering = ['department', 'name']
        indexes = [
            models.Index(fields=['department']),
            models.Index(fields=['academic_title']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.get_academic_title_display()} {self.name}"
    
    @property
    def full_title(self):
        return f"{self.get_academic_title_display()} {self.name}"
