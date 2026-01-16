# نظام إدارة القاعات والمختبرات
# Room Management System

نظام ويب احترافي لإدارة القاعات والمختبرات مبني على Django.

## المتطلبات

- Python 3.10+
- pip

## التثبيت المحلي

```bash
# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة (Windows)
venv\Scripts\activate

# تفعيل البيئة (Linux/Mac)
source venv/bin/activate

# تثبيت المتطلبات
pip install -r requirements.txt

# إنشاء قاعدة البيانات
python manage.py migrate

# إنشاء مستخدم مدير
python manage.py createsuperuser

# تحميل البيانات الأولية
python manage.py loaddata initial_data

# تشغيل الخادم
python manage.py runserver
```

## نشر على PythonAnywhere

1. إنشاء حساب على PythonAnywhere
2. رفع الملفات (Git أو ZIP)
3. إنشاء Web App جديد → Manual Configuration → Python 3.10
4. إعداد Virtual Environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 roomenv
   pip install -r requirements.txt
   ```
5. إعداد WSGI في `/var/www/username_pythonanywhere_com_wsgi.py`
6. إضافة Static files في Web tab:
   - URL: `/static/`
   - Directory: `/home/username/room_management/staticfiles/`
7. تشغيل:
   ```bash
   python manage.py collectstatic
   python manage.py migrate
   ```

## الميزات

- ✅ إدارة القاعات والمختبرات
- ✅ إدارة الأساتذة والمواد
- ✅ جدولة الحصص مع منع التعارضات
- ✅ لوحة تحكم لحظية
- ✅ البحث عن قاعات متاحة
- ✅ عرض الجدول الزمني
- ✅ عرض شبكي أسبوعي
- ✅ تقويم شهري
- ✅ خريطة القاعات
- ✅ إدارة العطل الرسمية
- ✅ أيام الراحة للأقسام
- ✅ تصدير PDF
- ✅ واجهة عربية RTL

## الهيكل

```
room_management/
├── config/          # إعدادات Django
├── apps/
│   ├── core/        # الكليات والأقسام
│   ├── rooms/       # القاعات
│   ├── instructors/ # الأساتذة
│   ├── subjects/    # المواد
│   ├── schedules/   # الجداول
│   └── calendar_app/ # التقويم والعطل
├── templates/       # القوالب
└── static/          # الملفات الثابتة
```

## المطور

**MUNTADHER HAZIM**

📞 للتواصل: `07724978301`

📧 البريد الإلكتروني: [muntadherhazim95@gmail.com](mailto:muntadherhazim95@gmail.com)
