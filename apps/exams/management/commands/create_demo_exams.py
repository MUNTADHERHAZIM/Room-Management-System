from django.core.management.base import BaseCommand
from datetime import datetime, time
import random

from apps.core.models import College, Department
from apps.rooms.models import Room
from apps.subjects.models import Subject
from apps.exams.models import Student, ExamSession, ExamSessionSubject, HallSetup

class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية لنظام التوزيع الذكي للامتحانات'

    def handle(self, *args, **kwargs):
        self.stdout.write('بدء إنشاء البيانات التجريبية للامتحانات...')

        # 1. التأكد من وجود أقسام وكليات
        college, _ = College.objects.get_or_create(name="كلية الهندسة التجريبية", defaults={'code': 'ENG-DEMO'})
        dept_sw, _ = Department.objects.get_or_create(name="هندسة البرمجيات", college=college, defaults={'code': 'SW'})
        dept_nw, _ = Department.objects.get_or_create(name="هندسة الشبكات", college=college, defaults={'code': 'NW'})

        # 2. إنشاء مواد دراسية
        sub1, _ = Subject.objects.get_or_create(name="هياكل البيانات", department=dept_sw, defaults={'stage': 'الثانية', 'code': 'DS-201'})
        sub2, _ = Subject.objects.get_or_create(name="أمن الشبكات", department=dept_nw, defaults={'stage': 'الثالثة', 'code': 'SEC-301'})
        sub3, _ = Subject.objects.get_or_create(name="الذكاء الاصطناعي", department=dept_sw, defaults={'stage': 'الرابعة', 'code': 'AI-401'})

        # 3. إنشاء طلاب بأسماء وألقاب (لاختبار تنافر العائلة)
        first_names = ['أحمد', 'محمد', 'علي', 'عمر', 'حسين', 'فاطمة', 'زينب', 'مريم', 'نور', 'هدى']
        families = ['التميمي', 'الشمري', 'الخفاجي', 'الموسوي', 'الدليمي', 'الربيعي']
        
        students_sw = []
        students_nw = []

        # مسح الطلاب التجريبيين السابقين إذا وجدوا
        Student.objects.filter(university_id__startswith='DEMO-').delete()

        # طلاب لهندسة البرمجيات (مواد: هياكل بيانات، ذكاء اصطناعي)
        for i in range(1, 41): # 40 طالب
            name = f"{random.choice(first_names)} {random.choice(first_names)} {random.choice(families)}"
            s = Student.objects.create(
                name=name,
                university_id=f"DEMO-SW-{i:03d}",
                department=dept_sw,
                stage=random.choice(['الثانية', 'الرابعة'])
            )
            students_sw.append(s)

        # طلاب لهندسة الشبكات (مادة: أمن الشبكات)
        for i in range(1, 31): # 30 طالب
            name = f"{random.choice(first_names)} {random.choice(first_names)} {random.choice(families)}"
            s = Student.objects.create(
                name=name,
                university_id=f"DEMO-NW-{i:03d}",
                department=dept_nw,
                stage='الثالثة'
            )
            students_nw.append(s)

        self.stdout.write(self.style.SUCCESS(f'تم إنشاء {len(students_sw) + len(students_nw)} طالب بنجاح.'))

        # 4. إعداد قاعات
        room1, _ = Room.objects.get_or_create(name="قاعة الخوارزمي المخصصة للامتحان", defaults={
            'room_type': 'قاعة', 'capacity': 60, 'department': dept_sw
        })
        room2, _ = Room.objects.get_or_create(name="قاعة الكندي المخصصة للامتحان", defaults={
            'room_type': 'قاعة', 'capacity': 50, 'department': dept_nw
        })

        # 5. إنشاء جلسة امتحانية
        session, created = ExamSession.objects.get_or_create(
            name="امتحانات نصف السنة (توضيحي)",
            defaults={
                'date': datetime.now().date(),
                'start_time': time(9, 0),
                'end_time': time(11, 0),
                'semester': '1'
            }
        )
        if not created:
            # إذا كانت موجودة، قم بحذف التوزيعات القديمة
            session.assignments.all().delete()
            session.exam_subjects.all().delete()
            session.hall_setups.all().delete()

        # 6. إضافة المواد للجلسة مع الطلاب
        es_sub1 = ExamSessionSubject.objects.create(session=session, subject=sub1, color_code='#3B82F6') # أزرق
        es_sub1.students.add(*[s for s in students_sw if s.stage == 'الثانية']) # حوالي 20 طالب

        es_sub2 = ExamSessionSubject.objects.create(session=session, subject=sub2, color_code='#EF4444') # أحمر
        es_sub2.students.add(*students_nw) # 30 طالب

        es_sub3 = ExamSessionSubject.objects.create(session=session, subject=sub3, color_code='#10B981') # أخضر
        es_sub3.students.add(*[s for s in students_sw if s.stage == 'الرابعة']) # حوالي 20 طالب

        self.stdout.write(self.style.SUCCESS('تم إضافة المواد والطلاب للجلسة.'))

        # 7. إضافة القاعات وإعداداتها (مهم جداً للتوزيع)
        # القاعة الأولى: 6 صفوف في 8 أعمدة = 48 مقعد كلي.
        # بالتباعد الشطرنجي سيكون المتاح 24 مقعد
        HallSetup.objects.create(
            session=session,
            room=room1,
            rows=6,
            columns=8,
            seat_type='منفصلة',
            spacing_mode='شطرنجي'
        )

        # القاعة الثانية: 8 صفوف في 8 أعمدة = 64 مقعد كلي.
        # بتباعد بدون تباعد (لحمل العدد الأكبر) سيكون المتاح 64 مقعد
        HallSetup.objects.create(
            session=session,
            room=room2,
            rows=8,
            columns=8,
            seat_type='مشتركة',
            spacing_mode='شطرنجي' # نغيره لشطرنجي فيكون المتاح 32 مقعد. الإجمالي = 24 + 32 = 56 مقعد. الطلاب = 70. سنحتاج لزيادة الحجم أو تغيير النمط.
        )
        
        # لنغير الإعدادات لتستوعب 70 طالباً
        hs2 = HallSetup.objects.get(session=session, room=room2)
        hs2.rows = 8
        hs2.columns = 10 
        hs2.spacing_mode = 'بدون_تباعد' # 80 مقعد متاح
        hs2.save()

        self.stdout.write(self.style.SUCCESS('تم إعداد القاعات بنجاح.'))
        self.stdout.write(self.style.SUCCESS(f'الآن يمكنك الذهاب لصفحة "الجلسات الامتحانية" وتنفيذ خوارزمية التوزيع للجلسة "{session.name}"'))
