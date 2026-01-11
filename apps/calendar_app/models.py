from django.db import models
from apps.core.models import Department


class Holiday(models.Model):
    """نموذج العطلة الرسمية"""
    
    name = models.CharField(max_length=200, verbose_name='اسم العطلة')
    date = models.DateField(verbose_name='التاريخ')
    description = models.TextField(blank=True, verbose_name='الوصف')
    recurring = models.BooleanField(default=False, verbose_name='سنوية متكررة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'عطلة'
        verbose_name_plural = 'العطل الرسمية'
        ordering = ['date']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.date})"


class DepartmentOffDay(models.Model):
    """نموذج أيام الراحة للقسم"""
    
    DAYS = [
        ('السبت', 'السبت'),
        ('الأحد', 'الأحد'),
        ('الإثنين', 'الإثنين'),
        ('الثلاثاء', 'الثلاثاء'),
        ('الأربعاء', 'الأربعاء'),
        ('الخميس', 'الخميس'),
        ('الجمعة', 'الجمعة'),
    ]
    
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='off_days',
        verbose_name='القسم'
    )
    day = models.CharField(
        max_length=20,
        choices=DAYS,
        verbose_name='اليوم'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'يوم راحة'
        verbose_name_plural = 'أيام الراحة'
        ordering = ['department', 'day']
        unique_together = ['department', 'day']

    def __str__(self):
        return f"{self.department.name} - {self.day}"
