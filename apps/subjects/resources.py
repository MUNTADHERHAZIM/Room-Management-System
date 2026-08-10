from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Subject
from apps.core.models import Department


def normalize_arabic(text):
    """توحيد الأحرف العربية للمقارنة (أ/إ/آ → ا، ة → ه، ى → ي)"""
    text = text.strip()
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = text.replace('ة', 'ه').replace('ى', 'ي')
    # حذف الحركات
    for ch in 'ًٌٍَُِّْ':
        text = text.replace(ch, '')
    return text


def word_overlap_score(query, candidate):
    """نسبة الكلمات المشتركة بين النصين (0.0 — 1.0)"""
    q_words = set(normalize_arabic(query).split())
    c_words = set(normalize_arabic(candidate).split())
    if not q_words:
        return 0.0
    overlap = len(q_words & c_words)
    return overlap / len(q_words)


class FlexibleDepartmentWidget(ForeignKeyWidget):
    """بحث مرن عن القسم بخوارزمية تشابه الكلمات"""

    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        val = str(value).strip()

        # 1) تطابق دقيق
        try:
            return self.model.objects.get(name=val)
        except self.model.DoesNotExist:
            pass

        # 2) يحتوي على النص (بعد التطبيع)
        norm_val = normalize_arabic(val)
        for dept in self.model.objects.all():
            if normalize_arabic(dept.name) == norm_val:
                return dept

        # 3) أفضل تطابق بخوارزمية الكلمات المشتركة
        all_depts = list(self.model.objects.all())
        best_dept = None
        best_score = 0.0
        for dept in all_depts:
            score = word_overlap_score(val, dept.name)
            if score > best_score:
                best_score = score
                best_dept = dept

        # نقبل أي تطابق بنسبة 40% أو أكثر
        if best_dept and best_score >= 0.4:
            return best_dept

        # 4) بحث بالرمز
        match = self.model.objects.filter(code__iexact=val).first()
        if match:
            return match

        # 5) بحث بالـ ID
        try:
            return self.model.objects.get(pk=int(val))
        except (ValueError, self.model.DoesNotExist):
            pass

        available = ", ".join(self.model.objects.values_list("name", flat=True)[:10])
        raise ValueError(f'لم يتم العثور على قسم باسم "{val}". بعض الأقسام: {available}')




def normalize_stage(value):
    """توحيد مسميات المراحل"""
    val = str(value).strip()
    if 'اولى' in val or 'الأولى' in val: return 'الأولى'
    if 'ثانيه' in val or 'الثانية' in val: return 'الثانية'
    if 'ثالثه' in val or 'الثالثة' in val: return 'الثالثة'
    if 'رابعه' in val or 'الرابعة' in val: return 'الرابعة'
    if 'خامسه' in val or 'الخامسة' in val: return 'الخامسة'
    if 'سادسه' in val or 'السادسة' in val: return 'السادسة'
    return 'الأولى'

class SubjectResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=FlexibleDepartmentWidget(Department, 'name')
    )

    class Meta:
        model = Subject
        fields = ('id', 'name', 'code', 'department', 'stage', 'hours_per_week', 'is_active')
        export_order = ('id', 'name', 'code', 'department', 'stage', 'hours_per_week', 'is_active')
        # جعل النظام يميز المادة بناءً على الاسم والقسم والمرحلة معاً
        import_id_fields = ('code',)
        skip_unchanged = True
        report_skipped = True

    def get_instance(self, instance_loader, row):
        """البحث عن مادة موجودة مسبقاً بناءً على الكود فقط"""
        code = row.get('code')
        if code:
            return Subject.objects.filter(code=code).first()
        return None

    def before_import_row(self, row, row_number=None, **kwargs):
        """تحويل المسميات العربية إلى مسميات النظام البرمجية"""
        mapping = {
            'اسم المادة': 'name',
            'الاسم': 'name',
            'كود المادة': 'code',
            'الكود': 'code',
            'الرمز': 'code',
            'القسم': 'department',
            'القسم (اختياري)': 'department',
            'المرحلة': 'stage',
            'المرحلة (اختياري)': 'stage',
            'عدد الساعات': 'hours_per_week',
            'الساعات': 'hours_per_week',
        }
        for ar_name, en_name in mapping.items():
            if ar_name in row and row[ar_name] and not row.get(en_name):
                row[en_name] = row[ar_name]
        
        # تطبيع المرحلة لضمان التطابق
        if 'stage' in row and row['stage']:
            row['stage'] = normalize_stage(row['stage'])
