from django.db import models
from apps.core.models import Department


class Room(models.Model):
    """نموذج القاعة"""
    
    ROOM_TYPES = [
        ('قاعة', 'قاعة دراسية'),
        ('مختبر_حاسوب', 'مختبر حاسوب'),
        ('مختبر_علمي', 'مختبر علمي'),
        ('قاعة_مؤتمرات', 'قاعة مؤتمرات'),
        ('مكتبة', 'مكتبة'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='اسم القاعة')
    room_type = models.CharField(
        max_length=50,
        choices=ROOM_TYPES,
        default='قاعة',
        verbose_name='نوع القاعة'
    )
    capacity = models.PositiveIntegerField(default=30, verbose_name='السعة')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='rooms',
        verbose_name='القسم'
    )
    floor = models.CharField(max_length=50, blank=True, verbose_name='الطابق')
    has_projector = models.BooleanField(default=False, verbose_name='يحتوي على بروجكتر')
    has_computers = models.BooleanField(default=False, verbose_name='يحتوي على حاسبات')
    has_whiteboard = models.BooleanField(default=True, verbose_name='يحتوي على سبورة')
    has_air_conditioning = models.BooleanField(default=False, verbose_name='يحتوي على تكييف')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'قاعة'
        verbose_name_plural = 'القاعات'
        ordering = ['department', 'name']
        indexes = [
            models.Index(fields=['department']),
            models.Index(fields=['room_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    @property
    def college(self):
        return self.department.college
