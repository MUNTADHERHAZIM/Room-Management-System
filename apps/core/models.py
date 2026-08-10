from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


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

class SystemSettings(models.Model):
    """إعدادات النظام العامة"""
    show_management_buttons = models.BooleanField(
        default=True, 
        verbose_name='إظهار أزرار الإضافة والتعديل والحذف'
    )
    is_maintenance_mode = models.BooleanField(
        default=False,
        verbose_name='وضع الصيانة'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'إعدادات النظام'
        verbose_name_plural = 'إعدادات النظام'

    def __str__(self):
        return "إعدادات النظام العامة"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton pattern
        super().save(*args, **kwargs)
        # ✅ مسح الكاش فوراً عند تغيير الإعدادات
        from django.core.cache import cache
        cache.delete('system_settings')

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class UserProfile(models.Model):
    """ملف المستخدم والصلاحيات المخصصة للنظام"""
    ROLE_CHOICES = [
        ('admin', 'مدير النظام (صلاحيات كاملة)'),
        ('supervisor', 'مشرف (صلاحيات واسعة)'),
        ('data_entry', 'مدخل بيانات'),
        ('viewer', 'مشاهد / مطلع فقط'),
        ('custom', 'صلاحيات مخصصة'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='المستخدم'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='data_entry',
        verbose_name='الرتبة / الدور'
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ملاحظات / الوظيفة'
    )

    # 🔑 Granular Permissions Flags
    can_view_schedules = models.BooleanField(default=True, verbose_name='رؤية الجداول والتقويم والقاعات')
    can_manage_schedules = models.BooleanField(default=True, verbose_name='إضافة وتعديل الجداول والحصص')

    can_access_attendance = models.BooleanField(default=True, verbose_name='دخول بوابة الحضور والانصراف')
    can_manage_attendance = models.BooleanField(default=True, verbose_name='إشراف وتعديل جلسات الحضور والتقارير')

    can_access_exams = models.BooleanField(default=True, verbose_name='إدارة الجلسات الامتحانية وتوزيع الطلاب')

    can_manage_rooms = models.BooleanField(default=True, verbose_name='إضافة وتعديل القاعات والكليات والأقسام')
    can_manage_instructors = models.BooleanField(default=True, verbose_name='إضافة وتعديل بيانات الأساتذة')
    can_manage_subjects = models.BooleanField(default=True, verbose_name='إضافة وتعديل المواد الدراسية')

    can_manage_users = models.BooleanField(default=False, verbose_name='إدارة الحسابات والصلاحيات')

    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'ملف المستخدم والصلاحيات'
        verbose_name_plural = 'ملفات المستخدمين والصلاحيات'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def has_perm(self, perm_code):
        """فحص الصلاحية بمرونة"""
        if self.user.is_superuser or self.user.is_staff or self.role == 'admin':
            return True
        return getattr(self, perm_code, False)

    def apply_role_defaults(self):
        """تطبيق الصلاحيات التلقائية حسب الدور المحدد"""
        if self.role == 'admin':
            self.can_view_schedules = True
            self.can_manage_schedules = True
            self.can_access_attendance = True
            self.can_manage_attendance = True
            self.can_access_exams = True
            self.can_manage_rooms = True
            self.can_manage_instructors = True
            self.can_manage_subjects = True
            self.can_manage_users = True
        elif self.role == 'supervisor':
            self.can_view_schedules = True
            self.can_manage_schedules = True
            self.can_access_attendance = True
            self.can_manage_attendance = True
            self.can_access_exams = True
            self.can_manage_rooms = False
            self.can_manage_instructors = False
            self.can_manage_subjects = False
            self.can_manage_users = False
        elif self.role == 'data_entry':
            self.can_view_schedules = True
            self.can_manage_schedules = True
            self.can_access_attendance = True
            self.can_manage_attendance = True
            self.can_access_exams = True
            self.can_manage_rooms = True
            self.can_manage_instructors = True
            self.can_manage_subjects = True
            self.can_manage_users = False
        elif self.role == 'viewer':
            self.can_view_schedules = True
            self.can_manage_schedules = False
            self.can_access_attendance = False
            self.can_manage_attendance = False
            self.can_access_exams = False
            self.can_manage_rooms = False
            self.can_manage_instructors = False
            self.can_manage_subjects = False
            self.can_manage_users = False




@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """إنشاء أو تحديث ملف المستخدم تلقائياً عند إنشاء حساب جديد"""
    profile, p_created = UserProfile.objects.get_or_create(user=instance)
    if p_created:
        if instance.is_superuser:
            profile.role = 'admin'
            profile.apply_role_defaults()
            profile.save()

