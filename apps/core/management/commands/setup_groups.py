from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'إنشاء المجموعات اللازمة للنظام (مثل مجموعة مدخلي البيانات)'

    def handle(self, *args, **options):
        group_name = 'Data Entry'
        group, created = Group.objects.get_or_create(name=group_name)
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'تم إنشاء المجموعة: "{group_name}" بنجاح'))
        else:
            self.stdout.write(self.style.WARNING(f'المجموعة: "{group_name}" موجودة بالفعل'))

        self.stdout.write(self.style.SUCCESS('جاهز لإضافة المستخدمين لهذه المجموعة لإعطائهم صلاحية الإدخال.'))
