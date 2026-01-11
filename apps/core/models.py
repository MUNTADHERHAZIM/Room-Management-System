from django.db import models


class College(models.Model):
    """نموذج الكلية"""
    name = models.CharField(max_length=200, verbose_name='اسم الكلية')
    code = models.CharField(max_length=20, unique=True, verbose_name='رمز الكلية')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'كلية'
        verbose_name_plural = 'الكليات'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """نموذج القسم"""
    name = models.CharField(max_length=200, verbose_name='اسم القسم')
    code = models.CharField(max_length=20, verbose_name='رمز القسم')
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='departments',
        verbose_name='الكلية'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'قسم'
        verbose_name_plural = 'الأقسام'
        ordering = ['college', 'name']
        unique_together = ['college', 'code']

    def __str__(self):
        return f"{self.name} - {self.college.name}"
