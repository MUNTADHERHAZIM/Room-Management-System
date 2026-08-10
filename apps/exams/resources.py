from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Student
from apps.core.models import Department
from apps.subjects.models import Subject


# ───────────────────────────────────────────────────────────
# دوال مساعدة لتطبيع النصوص العربية
# ───────────────────────────────────────────────────────────

def normalize_arabic(text):
    """توحيد الأحرف العربية للمقارنة"""
    text = str(text).strip()
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = text.replace('ة', 'ه').replace('ى', 'ي')
    for ch in 'ًٌٍَُِّْ':
        text = text.replace(ch, '')
    return text


def word_overlap_score(query, candidate):
    """نسبة الكلمات المشتركة بين النصين"""
    q_words = set(normalize_arabic(query).split())
    c_words = set(normalize_arabic(candidate).split())
    if not q_words:
        return 0.0
    return len(q_words & c_words) / len(q_words)


def normalize_stage(value):
    """
    تحويل قيمة المرحلة من أي صيغة إلى القيمة المخزونة:
    'المرحلة الثانية' → 'الثانية'
    'الثانية'         → 'الثانية'
    """
    STAGES = Subject.STAGES  # [('الأولى', 'المرحلة الأولى'), ...]
    val = str(value).strip()

    # 1) مطابقة مباشرة بالقيمة المخزونة
    stored_vals = [s[0] for s in STAGES]
    if val in stored_vals:
        return val

    # 2) حذف "المرحلة " من البداية ثم مطابقة
    stripped = val.replace('المرحلة ', '').replace('مرحلة ', '').strip()
    if stripped in stored_vals:
        return stripped

    # 3) مطابقة بقيم العرض الكاملة
    for stored, display in STAGES:
        if normalize_arabic(val) == normalize_arabic(display):
            return stored
        if normalize_arabic(stripped) == normalize_arabic(stored):
            return stored

    # 4) الافتراضي
    return 'الأولى'


# ───────────────────────────────────────────────────────────
# Widget مرن للقسم
# ───────────────────────────────────────────────────────────

class FlexibleDepartmentWidget(ForeignKeyWidget):

    def clean(self, value, row=None, **kwargs):
        if not value or str(value).strip() in ('', 'None'):
            return None
        val = str(value).strip()

        # 1) تطابق دقيق
        try:
            return self.model.objects.get(name=val)
        except self.model.DoesNotExist:
            pass

        # 2) تطابق بعد تطبيع الأحرف
        norm_val = normalize_arabic(val)
        for dept in self.model.objects.all():
            if normalize_arabic(dept.name) == norm_val:
                return dept

        # 3) أفضل تطابق بخوارزمية الكلمات المشتركة
        best_dept, best_score = None, 0.0
        for dept in self.model.objects.all():
            score = word_overlap_score(val, dept.name)
            if score > best_score:
                best_score = score
                best_dept = dept

        if best_dept and best_score >= 0.4:
            return best_dept

        # 4) بحث بالرمز
        match = self.model.objects.filter(code__iexact=val).first()
        if match:
            return match

        available = ", ".join(self.model.objects.values_list("name", flat=True)[:8])
        raise ValueError(f'لم يتم العثور على قسم باسم "{val}". بعض الأقسام: {available}')


# ───────────────────────────────────────────────────────────
# Student Resource
# ───────────────────────────────────────────────────────────

class StudentResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=FlexibleDepartmentWidget(Department, 'name')
    )

    class Meta:
        model = Student
        fields = ('id', 'name', 'university_id', 'department', 'stage',
                  'family_name', 'phone', 'notes', 'is_active')
        export_order = ('id', 'name', 'university_id', 'department', 'stage',
                        'family_name', 'phone', 'notes', 'is_active')
        import_id_fields = ('university_id',)
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, row_number=None, **kwargs):
        """تحويل المسميات العربية إلى مسميات النظام البرمجية وتطبيع المرحلة"""
        
        # خريطة الربط بين العربي والإنجليزي
        mapping = {
            'الاسم الكامل': 'name',
            'الرقم الجامعي': 'university_id',
            'القسم (اختياري)': 'department',
            'القسم': 'department',
            'المرحلة (اختياري)': 'stage',
            'المرحلة': 'stage',
            'اللقب العائلي (اختياري)': 'family_name',
            'اللقب العائلي': 'family_name',
            'اللقب': 'family_name',
            'رقم الهاتف': 'phone',
            'الهاتف': 'phone',
            'ملاحظات': 'notes',
        }

        # نقل البيانات من العمود العربي للعمود الإنجليزي
        for ar_name, en_name in mapping.items():
            if ar_name in row and row[ar_name] and not row.get(en_name):
                row[en_name] = row[ar_name]

        # تطبيع قيمة المرحلة
        if 'stage' in row and row['stage']:
            row['stage'] = normalize_stage(row['stage'])

    def save_instance(self, instance, is_new, using_transactions=True, dry_run=False):
        """
        استخدام update_or_create مباشرة لضمان التحديث وليس التكرار.
        """
        if dry_run:
            return

        uid = instance.university_id
        dept = getattr(instance, 'department', None)

        if not dept:
            raise ValueError(f'لم يتم تحديد القسم للطالب {instance.name}')

        Student.objects.update_or_create(
            university_id=uid,
            defaults={
                'name': instance.name,
                'department': dept,
                'stage': instance.stage or 'الأولى',
                'family_name': instance.family_name or '',
                'phone': instance.phone or '',
                'notes': instance.notes or '',
                'is_active': instance.is_active if instance.is_active is not None else True,
            }
        )
