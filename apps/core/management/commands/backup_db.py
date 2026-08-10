import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from io import StringIO


class Command(BaseCommand):
    help = 'إنشاء نسخة احتياطية كاملة من قاعدة البيانات (SQLite + JSON)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-backups',
            type=int,
            default=10,
            help='الحد الأقصى لعدد النسخ الاحتياطية المحفوظة (الافتراضي: 10)',
        )
        parser.add_argument(
            '--format',
            type=str,
            default='both',
            choices=['sqlite', 'json', 'both'],
            help='صيغة النسخة الاحتياطية: sqlite, json, أو both (الافتراضي: both)',
        )

    def handle(self, *args, **options):
        max_backups = options['max_backups']
        backup_format = options['format']
        
        # إنشاء مجلد النسخ الاحتياطية
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        created_files = []

        # === 1. نسخة SQLite ===
        if backup_format in ('sqlite', 'both'):
            db_path = settings.BASE_DIR / 'db.sqlite3'
            if db_path.exists():
                backup_name = f'backup_{timestamp}.sqlite3'
                backup_path = backup_dir / backup_name
                shutil.copy2(str(db_path), str(backup_path))
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                created_files.append((backup_name, size_mb))
                self.stdout.write(f'  ✅ نسخة SQLite: {backup_name} ({size_mb:.2f} MB)')
            else:
                self.stdout.write(self.style.WARNING('  ⚠️ ملف قاعدة البيانات غير موجود!'))

        # === 2. نسخة JSON (محمولة) ===
        if backup_format in ('json', 'both'):
            json_name = f'backup_{timestamp}.json'
            json_path = backup_dir / json_name
            
            output = StringIO()
            try:
                call_command(
                    'dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    '--exclude=contenttypes',
                    '--exclude=auth.permission',
                    '--exclude=sessions',
                    '--indent=2',
                    stdout=output
                )
                with open(str(json_path), 'w', encoding='utf-8') as f:
                    f.write(output.getvalue())
                
                size_mb = json_path.stat().st_size / (1024 * 1024)
                created_files.append((json_name, size_mb))
                self.stdout.write(f'  ✅ نسخة JSON: {json_name} ({size_mb:.2f} MB)')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ خطأ في تصدير JSON: {str(e)}'))

        # === 3. حذف النسخ القديمة ===
        self._cleanup_old_backups(backup_dir, max_backups)

        # === ملخص ===
        if created_files:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'✨ تم إنشاء {len(created_files)} نسخة احتياطية بنجاح!'))
            self.stdout.write(f'📁 المسار: {backup_dir}')
        else:
            self.stdout.write(self.style.WARNING('لم يتم إنشاء أي نسخة احتياطية.'))

    def _cleanup_old_backups(self, backup_dir, max_backups):
        """حذف النسخ الأقدم إذا تجاوز العدد الحد الأقصى"""
        # SQLite backups
        sqlite_files = sorted(backup_dir.glob('backup_*.sqlite3'), key=os.path.getmtime)
        while len(sqlite_files) > max_backups:
            oldest = sqlite_files.pop(0)
            oldest.unlink()
            self.stdout.write(f'  🗑️ تم حذف نسخة قديمة: {oldest.name}')

        # JSON backups
        json_files = sorted(backup_dir.glob('backup_*.json'), key=os.path.getmtime)
        while len(json_files) > max_backups:
            oldest = json_files.pop(0)
            oldest.unlink()
            self.stdout.write(f'  🗑️ تم حذف نسخة قديمة: {oldest.name}')
