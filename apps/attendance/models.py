from django.db import models
from apps.exams.models import Student
from apps.schedules.models import Schedule
from apps.subjects.models import Subject
from apps.instructors.models import Instructor
from apps.rooms.models import Room


class AttendanceSession(models.Model):
    """جلسة الحضور المخصصة لمحاضرة معينة في تاريخ محدد"""
    SESSION_TYPES = [
        ('مجدولة', 'مجدولة'),
        ('استثنائية', 'استثنائية (Ad-hoc)'),
    ]
    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPES,
        default='مجدولة',
        verbose_name="نوع الجلسة"
    )
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
        verbose_name="الحصة الدراسية (مجدولة)",
        null=True, blank=True
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="adhoc_attendance_sessions",
        verbose_name="المادة",
        null=True, blank=True
    )
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name="adhoc_attendance_sessions",
        verbose_name="الأستاذ",
        null=True, blank=True
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="adhoc_attendance_sessions",
        verbose_name="القاعة",
        null=True, blank=True
    )
    date = models.DateField(verbose_name="تاريخ المحاضرة")
    session_token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="رمز الجلسة الأمني"
    )
    session_pin = models.CharField(
        max_length=6,
        unique=True,
        null=True,
        blank=True,
        verbose_name="رمز التحضير اليدوي (PIN)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="مفتوحة للتسجيل"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التحديث"
    )

    def save(self, *args, **kwargs):
        # Generate a short 5-character alphanumeric PIN if it doesn't exist
        if not self.session_pin:
            import random
            import string
            # Excluding confusing characters: O, 0, I, 1, L
            chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
            while True:
                new_pin = ''.join(random.choices(chars, k=5))
                if not AttendanceSession.objects.filter(session_pin=new_pin).exists():
                    self.session_pin = new_pin
                    break
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "جلسة تحضير"
        verbose_name_plural = "جلسات التحضير"
        ordering = ["-date", "-created_at"]

    @property
    def get_subject_name(self):
        if self.session_type == 'مجدولة' and self.schedule:
            return self.schedule.subject.name
        return self.subject.name if self.subject else "غير محدد"

    @property
    def get_room_name(self):
        if self.session_type == 'مجدولة' and self.schedule:
            return self.schedule.room.name
        return self.room.name if self.room else "غير محدد"

    @property
    def get_instructor_name(self):
        if self.session_type == 'مجدولة' and self.schedule:
            return self.schedule.instructor.name
        return self.instructor.name if self.instructor else "غير محدد"

    def __str__(self):
        if self.session_type == 'مجدولة' and self.schedule:
            return f"جلسة {self.schedule.subject.name} - {self.date}"
        elif self.subject:
            return f"جلسة (سريعة) {self.subject.name} - {self.date}"
        return f"جلسة حضور - {self.date}"


class AttendanceRecord(models.Model):
    """سجل حضور كل طالب للمحاضرة"""
    STATUS_CHOICES = [
        ("حاضر", "حاضر"),
        ("غائب", "غائب"),
        ("مستأذن", "مستأذن"),
        ("متأخر", "متأخر"),
    ]

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records",
        verbose_name="جلسة التحضير"
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="الطالب"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="حاضر",
        verbose_name="حالة الحضور"
    )
    scanned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="وقت التحضير"
    )
    device_fingerprint = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="بصمة جهاز الطالب"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات"
    )

    class Meta:
        verbose_name = "سجل حضور طالب"
        verbose_name_plural = "سجلات حضور الطلاب"
        ordering = ["student__name"]
        unique_together = [("session", "student")]

    def __str__(self):
        return f"{self.student.name} - {self.status}"
