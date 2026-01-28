from django.db import models
from apps.rooms.models import Room
from apps.instructors.models import Instructor
from apps.subjects.models import Subject


class Schedule(models.Model):
    """نموذج الحصة/الجدول"""
    
    DAYS = [
        ('السبت', 'السبت'),
        ('الأحد', 'الأحد'),
        ('الإثنين', 'الإثنين'),
        ('الثلاثاء', 'الثلاثاء'),
        ('الأربعاء', 'الأربعاء'),
        ('الخميس', 'الخميس'),
    ]
    
    SCHEDULE_TYPES = [
        ('محاضرة', 'محاضرة'),
        ('مختبر', 'مختبر'),
        ('امتحان', 'امتحان'),
        ('اجتماع', 'اجتماع'),
        ('أخرى', 'أخرى'),
    ]
    
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='القاعة'
    )
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='الأستاذ'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='المادة'
    )
    day = models.CharField(
        max_length=20,
        choices=DAYS,
        verbose_name='اليوم'
    )
    start_time = models.TimeField(verbose_name='وقت البداية')
    end_time = models.TimeField(verbose_name='وقت النهاية')
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPES,
        default='محاضرة',
        verbose_name='نوع الحصة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'حصة'
        verbose_name_plural = 'الحصص'
        ordering = ['day', 'start_time']
        indexes = [
            models.Index(fields=['room', 'day']),
            models.Index(fields=['instructor', 'day']),
            models.Index(fields=['day', 'start_time', 'end_time']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        try:
            return f"{self.subject.name} - {self.day} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
        except:
            return f"حصة غير مكتملة ({self.id})"
    
    def clean(self):
        """التحقق من عدم وجود تعارضات"""
        from django.core.exceptions import ValidationError, ObjectDoesNotExist
        from .validators import check_room_conflict, check_instructor_conflict, check_department_off_day
        
        errors = {}
        
        # التأكد من وجود كافة الحقول المطلوبة قبل فحص التعارضات
        # استخدام IDs لتجنب RelatedObjectDoesNotExist
        if not all([self.room_id, self.instructor_id, self.subject_id, self.day, self.start_time, self.end_time]):
            return

        try:
            room = self.room
            instructor = self.instructor
        except ObjectDoesNotExist:
            return

        # التحقق من أن وقت البداية قبل النهاية
        if self.start_time >= self.end_time:
            errors['end_time'] = 'وقت النهاية يجب أن يكون بعد وقت البداية'
        
        # التحقق من تعارض القاعة
        room_conflict = check_room_conflict(
            room, self.day, self.start_time, self.end_time,
            exclude_id=self.pk
        )
        if room_conflict:
            errors['room'] = f'القاعة محجوزة في هذا الوقت ({room_conflict.subject.name})'
        
        # التحقق من تعارض الأستاذ
        instructor_conflict = check_instructor_conflict(
            instructor, self.day, self.start_time, self.end_time,
            exclude_id=self.pk
        )
        if instructor_conflict:
            errors['instructor'] = f'الأستاذ لديه حصة أخرى في هذا الوقت ({instructor_conflict.subject.name})'
        
        # التحقق من يوم الراحة للقسم
        if check_department_off_day(room.department, self.day):
            errors['day'] = f'يوم {self.day} هو يوم راحة لقسم {room.department.name}'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        # نقوم بالتحقق فقط إذا لم يكن هناك أخطاء سابقة (مثلاً من الفورم)
        # أو نترك الفورم يعالجها. ولكن للسلامة في الـ API أو الـ Shell:
        self.full_clean()
        super().save(*args, **kwargs)
