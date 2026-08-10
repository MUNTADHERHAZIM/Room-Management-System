# 🏛️ نظام إدارة القاعات والمختبرات الذكي
### Smart Room & Lab Management System

[![Django](https://img.shields.io/badge/Framework-Django%205.1-092e20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![TailwindCSS](https://img.shields.io/badge/UI-Tailwind%20CSS-38bdf8?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python)](https://www.python.org/)

نظام ويب متطور واحترافي مصمم خصيصاً للمؤسسات الأكاديمية لإدارة القاعات الدراسية، المختبرات، وجداول الحصص بكفاءة عالية ومنع تعارض المواعيد. يتميز النظام بواجهة عصرية (Glassmorphism) وتجربة مستخدم سلسة تدعم اللغة العربية بالكامل.

---

## 🚀 المميزات الرئيسية (Features)

### 📊 لوحة التحكم والإحصائيات
*   **داشبورد تفاعلي:** يعرض نظرة شاملة على إشغال القاعات في الوقت الفعلي.
*   **إحصائيات تحليلية:** رسوم بيانية وتوزيعات للأنشطة الأكاديمية حسب الكليات والأقسام.
*   **حالة القاعات:** مراقبة لحظية للقاعات (مشغولة/متاحة) مع تفاصيل الحصة الحالية.

### 📅 الجدولة والذكاء الاصطناعي البرمجي
*   **منع التعارض:** خوارزميات ذكية تمنع حجز قاعة لمرتين في نفس الوقت أو تكليف أستاذ بحصتين متزامنتين.
*   **البحث الذكي:** محرك بحث متقدم للعثور على أقرب قاعة متاحة بناءً على السعة، التوقيت، والتجهيزات.
*   **عروض متعددة:** عرض الجدول الزمني (Timeline)، العرض الشبكي (Grid)، والتقويم الشهري.

### 🔒 الأمن والإدارة
*   **نظام دخول آمن:** واجهة دخول احترافية خاصة بالعمداء ورؤساء الأقسام.
*   **صلاحيات مرنة:** تقسيم المستخدمين إلى أدوار (مدراء، مدخلي بيانات، مشاهدين).
*   **إدارة متكاملة:** لوحة تحكم لإدارة الكليات، الأقسام، الأساتذة، المواد الدراسية، والعطل الرسمية.

### 🖨️ التقارير والطباعة
*   **الجدول اليومي الشامل:** تقرير يومي لكافة القاعات جاهز للطباعة الفورية.
*   **جداول الأساتذة والقاعات:** تصدير جداول فردية منسقة بلمسة واحدة.
*   **دعم الطباعة:** تصميم مخصص للطباعة (Print-friendly) يخفي العناصر غير الضرورية ويحافظ على الهوية الرسمية.

---

## 🛠️ التقنيات المستخدمة (Tech Stack)

| المجال | التقنية |
| :--- | :--- |
| **Backend** | Django 5.1 (Python) |
| **Frontend** | Tailwind CSS, Alpine.js, HTMX |
| **Database** | SQLite (Default) / PostgreSQL (Optional) |
| **Aesthetics** | CSS Glassmorphism, Google Fonts (Outfit, Cairo) |

---

## 💻 التثبيت والتشغيل (Setup)

### 1. إعداد البيئة
```bash
# استنساخ المستودع
git clone https://github.com/your-repo/room-management.git
cd room-management

# إنشاء وتفعيل البيئة الافتراضية
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 2. تثبيت المكتبات وتجهيز قاعدة البيانات
```bash
pip install -r requirements.txt
python manage.py migrate
```

### 3. إنشاء البيانات التجريبية (Demo)
لقد قمنا بتوفير أوامر خاصة لتجهيز النظام بالبيانات والحسابات فوراً:
```bash
# إنشاء حسابات تجريبية (المدير، العميد، رئيس القسم)
python manage.py create_demo_users

# تحميل بيانات الكليات والقاعات والجداول الوهمية
python manage.py load_demo_data
```

---

## 📂 هيكلية المشروع (Project Structure)

*   `apps/core/`: النواة، الكليات، الأقسام، والإحصائيات.
*   `apps/rooms/`: إدارة وتتبع حالات القاعات والمختبرات.
*   `apps/instructors/`: سجلات الأساتذة وجداولهم الخاصة.
*   `apps/subjects/`: إدارة المواد الدراسية والمناهج.
*   `apps/schedules/`: محرك الجدولة والتحقق من التعارضات.
*   `apps/calendar_app/`: العطل الرسمية وأيام الراحة والتقويم.

---

## 👨‍💻 المطور (Developer)

<div align="center">
  <h3>MUNTADHER HAZIM</h3>
  <p>Software Developer & UI/UX Design Enthusiast</p>

  <p>
    <a href="tel:07724978301">📞 07724978301</a> | 
    <a href="mailto:muntadherhazim95@gmail.com">📧 muntadherhazim95@gmail.com</a>
  </p>
  
  <p>حقوق النشر © 2026 - كافة الحقوق محفوظة</p>
</div>
