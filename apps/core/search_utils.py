import re
from django.db.models import Q


def make_arabic_regex(term):
    """
    تحويل نص البحث العربي إلى تعبير نمطي (Regex) مرن يتطابق مع كافة الحالات الشائعة:
    - الألف بأنواعها: (أ، إ، آ، ا، ٱ)
    - التاء المربوطة والهاء: (ة، ه)
    - الياء والألف المقصورة والهمزة على نبرة: (ي، ى، ئ)
    - الواو والهمزة على الواو: (و، ؤ)
    - إزالة التشكيل والتطويل تلقائياً
    """
    if not term:
        return ""
    # إزالة التشكيل والتطويل
    term = re.sub(r'[\u064B-\u065F\u0670ـ]', '', str(term).strip())
    res = []
    for ch in term:
        if ch in 'اأإآٱ':
            res.append('[اأإآٱ]')
        elif ch in 'هة':
            res.append('[هة]')
        elif ch in 'يىئ':
            res.append('[يىئ]')
        elif ch in 'وؤ':
            res.append('[وؤ]')
        elif ch in r'\.^$*+?{}[]|()':
            res.append('\\' + ch)
        else:
            res.append(ch)
    return ''.join(res)


def arabic_search_filter(field_name, search_term):
    """
    إنشاء تعبير Q للبحث المرن في قاعدة البيانات
    """
    if not search_term or not str(search_term).strip():
        return Q()
    regex_pattern = make_arabic_regex(search_term)
    return Q(**{f"{field_name}__iregex": regex_pattern}) | Q(**{f"{field_name}__icontains": search_term})
