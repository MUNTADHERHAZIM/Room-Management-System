from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction

class Command(BaseCommand):
    help = 'إنشاء حسابات تجريبية للعمداء ورؤساء الأقسام والمسؤولين'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🚀 بدء إنشاء الحسابات التجريبية...'))

        with transaction.atomic():
            # 1. إنشاء المجموعات
            data_entry_group, _ = Group.objects.get_or_create(name='Data Entry')
            deans_group, _ = Group.objects.get_or_create(name='Deans')
            heads_group, _ = Group.objects.get_or_create(name='Department Heads')

            # بيانات الحسابات
            users_data = [
                {
                    'username': 'admin',
                    'email': 'admin@university.edu.iq',
                    'password': 'admin123',
                    'first_name': 'المدير',
                    'last_name': 'العام',
                    'is_staff': True,
                    'is_superuser': True,
                    'groups': [data_entry_group]
                },
                {
                    'username': 'dean',
                    'email': 'dean@university.edu.iq',
                    'password': 'dean123',
                    'first_name': 'العميد',
                    'last_name': 'المحترم',
                    'is_staff': True,
                    'is_superuser': False,
                    'groups': [deans_group, data_entry_group]
                },
                {
                    'username': 'head',
                    'email': 'head@university.edu.iq',
                    'password': 'head123',
                    'first_name': 'رئيس',
                    'last_name': 'القسم',
                    'is_staff': True,
                    'is_superuser': False,
                    'groups': [heads_group, data_entry_group]
                },
            ]

            for user_info in users_data:
                user, created = User.objects.get_or_create(
                    username=user_info['username'],
                    defaults={
                        'email': user_info['email'],
                        'first_name': user_info['first_name'],
                        'last_name': user_info['last_name'],
                        'is_staff': user_info['is_staff'],
                        'is_superuser': user_info['is_superuser'],
                    }
                )
                
                # تعيين كلمة المرور
                user.set_password(user_info['password'])
                user.save()
                
                # إضافة للمجموعات
                user.groups.set(user_info['groups'])
                
                status = "تم إنشاء" if created else "تم تحديث"
                self.stdout.write(self.style.SUCCESS(f'   ✓ {status} الحساب: {user.username}'))

        self.stdout.write(self.style.SUCCESS('✅ تم إنشاء الحسابات التجريبية بنجاح!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🔑 بيانات الدخول:'))
        self.stdout.write('   - المدير العام: admin / admin123')
        self.stdout.write('   - العميد: dean / dean123')
        self.stdout.write('   - رئيس القسم: head / head123')
