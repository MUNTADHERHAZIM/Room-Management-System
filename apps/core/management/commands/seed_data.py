from django.core.management.base import BaseCommand
from apps.core.models import College, Department
from apps.instructors.models import Instructor
from apps.rooms.models import Room
from apps.subjects.models import Subject
from apps.exams.models import Student
import random

class Command(BaseCommand):
    help = 'Seeds the database with test data (instructors, subjects, rooms, students)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting database seed...')
        
        # 1. Create a College and Department if they don't exist
        college, _ = College.objects.get_or_create(
            name="كلية تكنولوجيا المعلومات",
            defaults={'code': 'IT'}
        )
        
        dept_cs, _ = Department.objects.get_or_create(
            name="علوم الحاسوب",
            college=college,
            defaults={'code': 'CS'}
        )
        
        dept_se, _ = Department.objects.get_or_create(
            name="هندسة البرمجيات",
            college=college,
            defaults={'code': 'SE'}
        )
        
        # 2. Create Instructors
        instructors_data = [
            ("د. علي العراقي", "أستاذ_مساعد", dept_cs),
            ("م. حسين قاسم", "مدرس", dept_se),
            ("م.م سارة سليم", "مدرس_مساعد", dept_cs),
        ]
        for name, title, dept in instructors_data:
            Instructor.objects.get_or_create(name=name, defaults={'academic_title': title, 'department': dept})
            
        # 3. Create Rooms
        rooms_data = [
            ("قاعة 1", dept_cs, 50, "قاعة_دراسية"),
            ("قاعة 2", dept_se, 40, "قاعة_دراسية"),
            ("مختبر الحاسوب 1", dept_cs, 30, "مختبر"),
        ]
        for name, dept, cap, rtype in rooms_data:
            Room.objects.get_or_create(name=name, department=dept, defaults={'capacity': cap, 'room_type': rtype, 'has_projector': True})
            
        # 4. Create Subjects
        subjects_data = [
            ("برمجة كينونية (OOP)", dept_cs, "الثانية"),
            ("ذكاء اصطناعي", dept_cs, "الثالثة"),
            ("هندسة متطلبات", dept_se, "الثالثة"),
            ("قواعد بيانات", dept_se, "الثانية"),
        ]
        for name, dept, stage in subjects_data:
            Subject.objects.get_or_create(name=name, department=dept, defaults={'stage': stage})
            
        # 5. Create Students
        students_names = [
            "أحمد جاسم محمد", "سجاد علي حسين", "فاطمة حيدر حسن", "مريم سعدون جابر", 
            "كرار عباس محمود", "زينب مرتضى كمال", "علي رضا طالب", "نور قاسم ياسين",
            "حسن مجيد طارق", "رسل عبد الرزاق"
        ]
        
        for i, name in enumerate(students_names):
            dept = dept_cs if i % 2 == 0 else dept_se
            stage = "الثانية" if i < 5 else "الثالثة"
            Student.objects.get_or_create(
                university_id=f"2023{str(i+1).zfill(4)}",
                defaults={
                    'name': name,
                    'department': dept,
                    'stage': stage
                }
            )
            
        self.stdout.write(self.style.SUCCESS('Successfully seeded database with test data!'))
