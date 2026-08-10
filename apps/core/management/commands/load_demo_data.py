"""
أمر لتحميل بيانات تجريبية شاملة للنظام
Comprehensive demo data loader management command
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import random
from datetime import time, timedelta, datetime


class Command(BaseCommand):
    help = 'يحمّل بيانات تجريبية شاملة لنظام إدارة القاعات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='مسح جميع البيانات قبل التحميل',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_all_data()
        
        self.stdout.write(self.style.NOTICE('🚀 بدء تحميل البيانات التجريبية...'))
        
        # إنشاء الكليات والأقسام
        colleges = self.create_colleges_and_departments()
        
        # إنشاء القاعات
        rooms = self.create_rooms(colleges)
        
        # إنشاء الأساتذة
        instructors = self.create_instructors(colleges)
        
        # إنشاء المواد
        subjects = self.create_subjects(colleges)
        
        # إنشاء الحصص
        schedules = self.create_schedules(rooms, instructors, subjects)
        
        self.stdout.write(self.style.SUCCESS('✅ تم تحميل البيانات التجريبية بنجاح!'))
        self.print_summary()

    def clear_all_data(self):
        """مسح جميع البيانات"""
        from apps.schedules.models import Schedule
        from apps.rooms.models import Room
        from apps.instructors.models import Instructor
        from apps.subjects.models import Subject
        from apps.core.models import Department, College
        
        self.stdout.write(self.style.WARNING('⚠️ جاري مسح جميع البيانات...'))
        
        Schedule.objects.all().delete()
        Room.objects.all().delete()
        Instructor.objects.all().delete()
        Subject.objects.all().delete()
        Department.objects.all().delete()
        College.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('✅ تم مسح جميع البيانات'))

    def create_colleges_and_departments(self):
        """إنشاء الكليات والأقسام"""
        from apps.core.models import College, Department
        
        self.stdout.write('📚 إنشاء الكليات والأقسام...')
        
        colleges_data = [
            {
                'name': 'كلية الهندسة',
                'code': 'ENG',
                'departments': [
                    ('قسم هندسة الحاسوب', 'CS'),
                    ('قسم الهندسة الكهربائية', 'EE'),
                    ('قسم الهندسة المدنية', 'CE'),
                    ('قسم الهندسة الميكانيكية', 'ME'),
                    ('قسم هندسة البرمجيات', 'SE'),
                ]
            },
            {
                'name': 'كلية العلوم',
                'code': 'SCI',
                'departments': [
                    ('قسم الرياضيات', 'MATH'),
                    ('قسم الفيزياء', 'PHY'),
                    ('قسم الكيمياء', 'CHEM'),
                    ('قسم علوم الحاسوب', 'CS'),
                    ('قسم الأحياء', 'BIO'),
                ]
            },
            {
                'name': 'كلية الإدارة والاقتصاد',
                'code': 'BUS',
                'departments': [
                    ('قسم إدارة الأعمال', 'BA'),
                    ('قسم المحاسبة', 'ACC'),
                    ('قسم الاقتصاد', 'ECO'),
                    ('قسم التسويق', 'MKT'),
                ]
            },
            {
                'name': 'كلية الآداب',
                'code': 'ART',
                'departments': [
                    ('قسم اللغة العربية', 'AR'),
                    ('قسم اللغة الإنجليزية', 'EN'),
                    ('قسم التاريخ', 'HIS'),
                    ('قسم الإعلام', 'MED'),
                ]
            },
            {
                'name': 'كلية الطب',
                'code': 'MED',
                'departments': [
                    ('قسم الطب العام', 'GM'),
                    ('قسم الجراحة', 'SRG'),
                    ('قسم التشريح', 'ANA'),
                ]
            }
        ]
        
        colleges = {}
        for college_data in colleges_data:
            college, created = College.objects.get_or_create(
                code=college_data['code'],
                defaults={'name': college_data['name']}
            )
            colleges[college.code] = {
                'college': college,
                'departments': []
            }
            
            for dept_name, dept_code in college_data['departments']:
                dept, created = Department.objects.get_or_create(
                    code=dept_code,
                    college=college,
                    defaults={'name': dept_name}
                )
                colleges[college.code]['departments'].append(dept)
        
        total_depts = sum(len(c['departments']) for c in colleges.values())
        self.stdout.write(f'   ✓ تم إنشاء {len(colleges)} كليات و {total_depts} قسم')
        
        return colleges

    def create_rooms(self, colleges):
        """إنشاء القاعات"""
        from apps.rooms.models import Room
        
        self.stdout.write('🏛️ إنشاء القاعات...')
        
        rooms = []
        room_counter = 1
        
        floors = ['الطابق الأرضي', 'الطابق الأول', 'الطابق الثاني', 'الطابق الثالث', 'الطابق الرابع']
        
        room_types = [
            ('قاعة', 'قاعة دراسية'),
            ('مختبر_حاسوب', 'مختبر حاسوب'),
            ('مختبر_علمي', 'مختبر علمي'),
            ('قاعة_مؤتمرات', 'قاعة مؤتمرات'),
        ]
        
        for college_code, college_data in colleges.items():
            for dept in college_data['departments']:
                # إنشاء 3-5 قاعات لكل قسم
                num_rooms = random.randint(3, 5)
                for i in range(num_rooms):
                    floor = random.choice(floors)
                    room_type = random.choice(room_types)[0]
                    
                    # تحديد السعة حسب نوع القاعة
                    if room_type == 'قاعة_مؤتمرات':
                        capacity = random.choice([100, 150, 200, 250])
                    elif room_type in ['مختبر_حاسوب', 'مختبر_علمي']:
                        capacity = random.choice([20, 25, 30])
                    else:
                        capacity = random.choice([30, 40, 50, 60, 80])
                    
                    room, created = Room.objects.get_or_create(
                        name=f'قاعة {room_counter}',
                        defaults={
                            'room_type': room_type,
                            'capacity': capacity,
                            'department': dept,
                            'floor': floor,
                            'has_projector': random.choice([True, True, False]),
                            'has_computers': room_type == 'مختبر_حاسوب',
                            'has_whiteboard': True,
                            'has_air_conditioning': random.choice([True, True, True, False]),
                            'has_audio_system': random.choice([True, False, True]), # حقل الصوتيات الجديد
                            'is_active': True,
                            'notes': f"قاعة مجهزة بنظام تكييف وسبورة عرض حديثة تابعة لقسم {dept.name}",
                        }
                    )
                    rooms.append(room)
                    room_counter += 1
        
        self.stdout.write(f'   ✓ تم إنشاء {len(rooms)} قاعة')
        return rooms

    def create_instructors(self, colleges):
        """إنشاء الأساتذة"""
        from apps.instructors.models import Instructor
        
        self.stdout.write('👨‍🏫 إنشاء الأساتذة...')
        
        first_names = [
            'أحمد', 'محمد', 'علي', 'حسين', 'عباس', 'كريم', 'سامر', 'فاضل', 'جعفر', 'حيدر',
            'مصطفى', 'حسن', 'عمر', 'خالد', 'سالم', 'ياسر', 'عادل', 'ماجد', 'نبيل', 'رائد',
            'فاطمة', 'زينب', 'مريم', 'نور', 'سارة', 'هدى', 'آلاء', 'رنا', 'دعاء', 'إيمان'
        ]
        
        last_names = [
            'الموسوي', 'العلوي', 'الحسيني', 'الجبوري', 'الشمري', 'الربيعي', 'الطائي', 
            'البغدادي', 'الكربلائي', 'النجفي', 'السعدي', 'الحمداني', 'الزيدي', 'العبادي',
            'العامري', 'المالكي', 'الكوفي', 'الهاشمي', 'الكاظمي', 'السامرائي'
        ]
        
        titles = ['أستاذ', 'أستاذ_مساعد', 'مدرس', 'مدرس_مساعد', 'معيد']
        title_weights = [10, 20, 35, 25, 10]
        
        specializations = [
            'البرمجة وهندسة البرمجيات', 'الذكاء الاصطناعي', 'قواعد البيانات', 'الشبكات',
            'الرياضيات التطبيقية', 'الفيزياء النظرية', 'الكيمياء العضوية', 'علم الأحياء الجزيئي',
            'إدارة المشاريع', 'التحليل المالي', 'الاقتصاد الكلي', 'التسويق الرقمي',
            'اللغويات', 'الأدب العربي', 'التاريخ الإسلامي', 'الإعلام الرقمي',
            'الطب الباطني', 'الجراحة العامة', 'علم التشريح'
        ]
        
        instructors = []
        used_names = set()
        
        for college_code, college_data in colleges.items():
            for dept in college_data['departments']:
                # إنشاء 4-7 أساتذة لكل قسم
                num_instructors = random.randint(4, 7)
                for i in range(num_instructors):
                    # إنشاء اسم فريد
                    while True:
                        first_name = random.choice(first_names)
                        last_name = random.choice(last_names)
                        full_name = f'{first_name} {last_name}'
                        if full_name not in used_names:
                            used_names.add(full_name)
                            break
                    
                    title = random.choices(titles, weights=title_weights)[0]
                    
                    instructor, created = Instructor.objects.get_or_create(
                        name=full_name,
                        defaults={
                            'academic_title': title,
                            'department': dept,
                            'email': f'{first_name.lower()}.{last_name.lower()[2:]}@university.edu.iq',
                            'phone': f'077{random.randint(10000000, 99999999)}',
                            'specialization': random.choice(specializations),
                            'is_active': True,
                        }
                    )
                    instructors.append(instructor)
        
        self.stdout.write(f'   ✓ تم إنشاء {len(instructors)} أستاذ')
        return instructors

    def create_subjects(self, colleges):
        """إنشاء المواد الدراسية"""
        from apps.subjects.models import Subject
        
        self.stdout.write('📖 إنشاء المواد الدراسية...')
        
        subjects_by_field = {
            'هندسة': [
                'البرمجة بلغة Python', 'هياكل البيانات', 'قواعد البيانات', 'تحليل وتصميم النظم',
                'هندسة البرمجيات', 'الشبكات الحاسوبية', 'الذكاء الاصطناعي', 'أمن المعلومات',
                'الدوائر الكهربائية', 'الإلكترونيات', 'نظم التحكم', 'معالجة الإشارات',
                'ميكانيكا المواد', 'ديناميكا حرارية', 'تصميم الآلات', 'هندسة الإنتاج',
                'مقاومة المواد', 'الهندسة الإنشائية', 'هيدروليك', 'إدارة المشاريع الهندسية'
            ],
            'علوم': [
                'التحليل الرياضي', 'الجبر الخطي', 'الإحصاء والاحتمالات', 'المعادلات التفاضلية',
                'الفيزياء العامة', 'الميكانيكا الكلاسيكية', 'الفيزياء الحديثة', 'البصريات',
                'الكيمياء العامة', 'الكيمياء العضوية', 'الكيمياء التحليلية', 'الكيمياء الفيزيائية',
                'علم الأحياء العام', 'علم الوراثة', 'علم البيئة', 'الأحياء الدقيقة'
            ],
            'إدارة': [
                'مبادئ الإدارة', 'إدارة الموارد البشرية', 'إدارة العمليات', 'الإدارة الاستراتيجية',
                'المحاسبة المالية', 'محاسبة التكاليف', 'المراجعة والتدقيق', 'الضرائب',
                'مبادئ الاقتصاد', 'الاقتصاد الجزئي', 'الاقتصاد الكلي', 'اقتصاديات الأعمال',
                'مبادئ التسويق', 'سلوك المستهلك', 'التسويق الإلكتروني', 'بحوث التسويق'
            ],
            'آداب': [
                'النحو والصرف', 'الأدب العربي القديم', 'الأدب العربي الحديث', 'البلاغة',
                'اللغة الإنجليزية', 'الترجمة', 'الأدب الإنجليزي', 'اللسانيات',
                'التاريخ الإسلامي', 'تاريخ العراق', 'الحضارات القديمة', 'التاريخ المعاصر',
                'مدخل إلى الإعلام', 'الصحافة', 'الإذاعة والتلفزيون', 'الإعلام الرقمي'
            ],
            'طب': [
                'علم التشريح', 'علم وظائف الأعضاء', 'الكيمياء الحيوية', 'علم الأنسجة',
                'علم الأدوية', 'علم الأمراض', 'الطب الباطني', 'طب الأطفال',
                'الجراحة العامة', 'التخدير', 'طب الطوارئ', 'الطب النفسي'
            ]
        }
        
        stages = ['الأولى', 'الثانية', 'الثالثة', 'الرابعة']
        
        subjects = []
        subject_counter = 1
        
        for college_code, college_data in colleges.items():
            # تحديد المجال حسب الكلية
            if 'هندسة' in college_data['college'].name:
                field = 'هندسة'
            elif 'علوم' in college_data['college'].name:
                field = 'علوم'
            elif 'إدارة' in college_data['college'].name or 'اقتصاد' in college_data['college'].name:
                field = 'إدارة'
            elif 'آداب' in college_data['college'].name:
                field = 'آداب'
            elif 'طب' in college_data['college'].name:
                field = 'طب'
            else:
                field = 'علوم'
            
            for dept in college_data['departments']:
                # إنشاء 6-10 مواد لكل قسم
                num_subjects = random.randint(6, 10)
                available_subjects = subjects_by_field.get(field, subjects_by_field['علوم'])
                selected_subjects = random.sample(
                    available_subjects, 
                    min(num_subjects, len(available_subjects))
                )
                
                for subject_name in selected_subjects:
                    stage = random.choice(stages)
                    
                    subject, created = Subject.objects.get_or_create(
                        name=f'{subject_name} - {dept.code}',
                        defaults={
                            'code': f'{dept.code}{subject_counter:03d}',
                            'department': dept,
                            'stage': stage,
                            'hours_per_week': random.choice([2, 3, 4]),
                            'is_active': True,
                        }
                    )
                    subjects.append(subject)
                    subject_counter += 1
        
        self.stdout.write(f'   ✓ تم إنشاء {len(subjects)} مادة دراسية')
        return subjects

    def create_schedules(self, rooms, instructors, subjects):
        """إنشاء الحصص الدراسية"""
        from apps.schedules.models import Schedule
        from apps.schedules.validators import check_room_conflict, check_instructor_conflict
        
        self.stdout.write('📅 إنشاء الحصص الدراسية...')
        
        days = ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        schedule_types = ['محاضرة', 'مختبر', 'أخرى']
        
        # أوقات المحاضرات المتاحة
        time_slots = [
            (time(8, 0), time(9, 0)),
            (time(8, 0), time(9, 30)),
            (time(9, 0), time(10, 0)),
            (time(9, 0), time(10, 30)),
            (time(9, 30), time(11, 0)),
            (time(10, 0), time(11, 0)),
            (time(10, 0), time(11, 30)),
            (time(10, 30), time(12, 0)),
            (time(11, 0), time(12, 0)),
            (time(11, 0), time(12, 30)),
            (time(11, 30), time(13, 0)),
            (time(12, 0), time(13, 0)),
            (time(12, 0), time(13, 30)),
            (time(12, 30), time(14, 0)),
            (time(13, 0), time(14, 0)),
            (time(13, 0), time(14, 30)),
            (time(13, 30), time(15, 0)),
            (time(14, 0), time(15, 0)),
            (time(14, 0), time(15, 30)),
            (time(14, 30), time(16, 0)),
            (time(15, 0), time(16, 0)),
            (time(15, 0), time(16, 30)),
            (time(15, 30), time(17, 0)),
            (time(16, 0), time(17, 0)),
            (time(16, 0), time(17, 30)),
        ]
        
        schedules = []
        created_count = 0
        skipped_count = 0
        
        # لكل مادة، إنشاء 2-3 حصص في الأسبوع
        for subject in subjects:
            # اختيار أستاذ من نفس القسم إن أمكن
            dept_instructors = [i for i in instructors if i.department_id == subject.department_id]
            if not dept_instructors:
                dept_instructors = instructors
            
            instructor = random.choice(dept_instructors)
            
            # اختيار قاعة من نفس القسم إن أمكن
            dept_rooms = [r for r in rooms if r.department_id == subject.department_id]
            if not dept_rooms:
                dept_rooms = rooms
            
            # إنشاء 2-3 حصص
            num_sessions = random.randint(2, 3)
            selected_days = random.sample(days, min(num_sessions, len(days)))
            
            for day in selected_days:
                room = random.choice(dept_rooms)
                semester = random.choice(['1', '2']) # توزيع عشوائي بين الكورسات
                start_time, end_time = random.choice(time_slots)
                schedule_type = random.choices(schedule_types, weights=[70, 20, 10])[0]
                
                # التحقق من التعارضات (مع تمرير الكورس)
                room_conflict = check_room_conflict(room, day, start_time, end_time, semester=semester)
                instructor_conflict = check_instructor_conflict(instructor, day, start_time, end_time, semester=semester)
                
                if room_conflict or instructor_conflict:
                    skipped_count += 1
                    continue
                
                try:
                    schedule = Schedule.objects.create(
                        room=room,
                        instructor=instructor,
                        subject=subject,
                        day=day,
                        semester=semester,
                        start_time=start_time,
                        end_time=end_time,
                        schedule_type=schedule_type,
                        is_active=True
                    )
                    schedules.append(schedule)
                    created_count += 1
                except Exception as e:
                    skipped_count += 1
        
        self.stdout.write(f'   ✓ تم إنشاء {created_count} حصة (تم تخطي {skipped_count} بسبب التعارضات)')
        return schedules

    def print_summary(self):
        """طباعة ملخص البيانات"""
        from apps.core.models import College, Department
        from apps.rooms.models import Room
        from apps.instructors.models import Instructor
        from apps.subjects.models import Subject
        from apps.schedules.models import Schedule
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 ملخص البيانات التجريبية'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'   🏛️ الكليات: {College.objects.count()}')
        self.stdout.write(f'   📂 الأقسام: {Department.objects.count()}')
        self.stdout.write(f'   🚪 القاعات: {Room.objects.count()}')
        self.stdout.write(f'   👨‍🏫 الأساتذة: {Instructor.objects.count()}')
        self.stdout.write(f'   📚 المواد: {Subject.objects.count()}')
        self.stdout.write(f'   📅 الحصص: {Schedule.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 50))
