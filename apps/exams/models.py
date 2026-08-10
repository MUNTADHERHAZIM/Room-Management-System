import uuid
from django.db import models
from apps.core.models import Department
from apps.rooms.models import Room
from apps.subjects.models import Subject


class Student(models.Model):
    """نموذج الطالب"""

    name = models.CharField(max_length=200, verbose_name='اسم الطالب الكامل')
    university_id = models.CharField(
        max_length=50, unique=True, verbose_name='الرقم الجامعي'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name='القسم'
    )
    stage = models.CharField(
        max_length=20,
        choices=Subject.STAGES,
        default='الأولى',
        verbose_name='المرحلة'
    )
    family_name = models.CharField(
        max_length=100, blank=True, verbose_name='اللقب العائلي',
        help_text='يُستخدم لمنع تجاور الأقارب'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'طالب'
        verbose_name_plural = 'الطلاب'
        ordering = ['department', 'stage', 'name']
        indexes = [
            models.Index(fields=['university_id']),
            models.Index(fields=['department']),
            models.Index(fields=['stage']),
            models.Index(fields=['family_name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.university_id})"

    def save(self, *args, **kwargs):
        """استخلاص اللقب العائلي تلقائياً من الاسم الكامل"""
        if not self.family_name and self.name:
            parts = self.name.strip().split()
            if len(parts) >= 2:
                self.family_name = parts[-1]
        super().save(*args, **kwargs)


class ExamSession(models.Model):
    """جلسة امتحانية — تمثل فترة زمنية واحدة يمتحن فيها عدة مواد"""

    SEMESTERS = [
        ('1', 'الفصل الدراسي الأول'),
        ('2', 'الفصل الدراسي الثاني'),
        ('صيفي', 'الفصل الصيفي'),
    ]

    name = models.CharField(
        max_length=200, verbose_name='اسم الجلسة',
        help_text='مثال: امتحانات نهاية الفصل الأول 2026'
    )
    date = models.DateField(verbose_name='تاريخ الامتحان')
    start_time = models.TimeField(verbose_name='وقت البداية')
    end_time = models.TimeField(verbose_name='وقت النهاية')
    semester = models.CharField(
        max_length=10, choices=SEMESTERS, default='1',
        verbose_name='الفصل الدراسي'
    )
    halls = models.ManyToManyField(
        Room, through='HallSetup', related_name='exam_sessions',
        verbose_name='القاعات'
    )
    is_distributed = models.BooleanField(
        default=False, verbose_name='تم التوزيع',
        help_text='يتم تفعيله تلقائياً بعد تشغيل الخوارزمية'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'جلسة امتحانية'
        verbose_name_plural = 'الجلسات الامتحانية'
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.name} - {self.date}"

    @property
    def total_students(self):
        return Student.objects.filter(
            exam_subjects__session=self
        ).distinct().count()

    @property
    def total_capacity(self):
        return sum(
            hs.effective_capacity for hs in self.hall_setups.all()
        )


class ExamSessionSubject(models.Model):
    """ربط مادة بجلسة امتحانية مع قائمة الطلاب"""

    session = models.ForeignKey(
        ExamSession, on_delete=models.CASCADE,
        related_name='exam_subjects', verbose_name='الجلسة'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE,
        related_name='exam_sessions_link', verbose_name='المادة'
    )
    students = models.ManyToManyField(
        Student, related_name='exam_subjects', blank=True,
        verbose_name='الطلاب المسجلون'
    )
    color_code = models.CharField(
        max_length=7, default='#3B82F6', verbose_name='لون التمييز',
        help_text='لون المادة في خريطة الجلوس (HEX)'
    )

    class Meta:
        verbose_name = 'مادة في جلسة'
        verbose_name_plural = 'المواد في الجلسات'
        unique_together = ['session', 'subject']

    def __str__(self):
        return f"{self.subject.name} — {self.session.name}"


class HallSetup(models.Model):
    """إعداد قاعة لجلسة امتحانية — مخطط الجلوس"""

    SEAT_TYPES = [
        ('منفصلة', 'طاولات منفصلة'),
        ('مشتركة', 'مقاعد مشتركة'),
        ('مدرج', 'مدرج ثابت'),
    ]

    SPACING_MODES = [
        ('شطرنجي', 'توزيع شطرنجي (مقعد نعم ومقعد لا)'),
        ('مقعد_فارغ', 'ترك مقعد فارغ بين كل طالبين'),
        ('بدون_تباعد', 'بدون تباعد (مع تنافر المواد فقط)'),
        ('عمودي_أقسام', 'توزيع عمودي بالأقسام (قسمان في كل عمود بدون فراغات)'),
    ]

    session = models.ForeignKey(
        ExamSession, on_delete=models.CASCADE,
        related_name='hall_setups', verbose_name='الجلسة'
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE,
        related_name='hall_setups', verbose_name='القاعة'
    )
    rows = models.PositiveIntegerField(
        default=5, verbose_name='عدد الصفوف'
    )
    columns = models.PositiveIntegerField(
        default=6, verbose_name='عدد الأعمدة'
    )
    seat_type = models.CharField(
        max_length=20, choices=SEAT_TYPES, default='منفصلة',
        verbose_name='نوع المقاعد'
    )
    spacing_mode = models.CharField(
        max_length=20, choices=SPACING_MODES, default='شطرنجي',
        verbose_name='نمط التباعد'
    )
    prevent_same_subject_adjacent = models.BooleanField(
        default=True, verbose_name='منع تجاور طلاب نفس المادة'
    )
    prevent_same_department_adjacent = models.BooleanField(
        default=True, verbose_name='منع تجاور طلاب نفس القسم'
    )
    prevent_same_family_adjacent = models.BooleanField(
        default=True, verbose_name='منع تجاور الأقارب (نفس اللقب)'
    )

    class Meta:
        verbose_name = 'إعداد قاعة امتحانية'
        verbose_name_plural = 'إعدادات القاعات الامتحانية'
        unique_together = ['session', 'room']

    def __str__(self):
        return f"{self.room.name} — {self.session.name}"

    @property
    def total_seats(self):
        return self.rows * self.columns

    @property
    def effective_capacity(self):
        """السعة الفعلية بعد تطبيق نمط التباعد"""
        total = self.total_seats
        if self.spacing_mode == 'شطرنجي':
            return (total + 1) // 2
        elif self.spacing_mode == 'مقعد_فارغ':
            return (self.columns + 1) // 2 * self.rows
        elif self.spacing_mode == 'عمودي_أقسام':
            return total  # يملأ القاعة كاملاً بدون فراغات
        return total  # بدون تباعد


class SeatingAssignment(models.Model):
    """نتيجة التوزيع — مقعد واحد لطالب واحد"""

    session = models.ForeignKey(
        ExamSession, on_delete=models.CASCADE,
        related_name='assignments', verbose_name='الجلسة'
    )
    hall_setup = models.ForeignKey(
        HallSetup, on_delete=models.CASCADE,
        related_name='assignments', verbose_name='القاعة'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE,
        related_name='seat_assignments', verbose_name='الطالب'
    )
    exam_subject = models.ForeignKey(
        ExamSessionSubject, on_delete=models.CASCADE,
        related_name='assignments', verbose_name='المادة',
        null=True
    )
    row = models.PositiveIntegerField(verbose_name='الصف')
    column = models.PositiveIntegerField(verbose_name='العمود')
    seat_label = models.CharField(
        max_length=20, verbose_name='رقم المقعد',
        help_text='مثال: A1, B3, C5'
    )

    class Meta:
        verbose_name = 'توزيع مقعد'
        verbose_name_plural = 'توزيعات المقاعد'
        unique_together = [
            ('session', 'student'),  # طالب واحد في مقعد واحد فقط
            ('hall_setup', 'row', 'column'),  # مقعد واحد لطالب واحد فقط
        ]
        indexes = [
            models.Index(fields=['session', 'hall_setup']),
            models.Index(fields=['student']),
        ]

    def __str__(self):
        return f"{self.student.name} → {self.hall_setup.room.name} [{self.seat_label}]"
