from django.db import models
from apps.core.models import Department


class Subject(models.Model):
    """نموذج المادة الدراسية"""
    
    STAGES = [
        ('الأولى', 'المرحلة الأولى'),
        ('الثانية', 'المرحلة الثانية'),
        ('الثالثة', 'المرحلة الثالثة'),
        ('الرابعة', 'المرحلة الرابعة'),
        ('الخامسة', 'المرحلة الخامسة'),
    ]
    
    name = models.CharField(max_length=200, unique=True, verbose_name='اسم المادة')
    code = models.CharField(max_length=20, blank=True, verbose_name='رمز المادة')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name='القسم'
    )
    stage = models.CharField(
        max_length=20,
        choices=STAGES,
        default='الأولى',
        verbose_name='المرحلة'
    )
    hours_per_week = models.PositiveIntegerField(default=3, verbose_name='ساعات أسبوعية')
    description = models.TextField(blank=True, verbose_name='الوصف')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'مادة'
        verbose_name_plural = 'المواد الدراسية'
        ordering = ['department', 'stage', 'name']
        indexes = [
            models.Index(fields=['department']),
            models.Index(fields=['stage']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_stage_display()})"
