from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """الحصول على قيمة من قاموس باستخدام مفتاح"""
    if dictionary is None:
        return []
    if isinstance(dictionary, dict):
        return dictionary.get(key, [])
    return []


@register.filter
def arabic_day(weekday):
    """تحويل رقم اليوم إلى اسم عربي"""
    days = {
        0: 'الإثنين',
        1: 'الثلاثاء',
        2: 'الأربعاء',
        3: 'الخميس',
        4: 'الجمعة',
        5: 'السبت',
        6: 'الأحد',
    }
    return days.get(weekday, '')


@register.simple_tag
def status_class(status):
    """إرجاع فئات CSS حسب الحالة"""
    classes = {
        'free': 'bg-green-100 text-green-800',
        'busy': 'bg-red-100 text-red-800',
        'soon': 'bg-yellow-100 text-yellow-800',
        'holiday': 'bg-gray-100 text-gray-800',
    }
    return classes.get(status, '')
@register.filter
def arabic_full_date(date_obj):
    """إرجاع التاريخ والوقت كاملاً باللغة العربية (اليوم، التاريخ، الوقت)"""
    if not date_obj:
        return ""
        
    days = {
        0: 'الإثنين', 1: 'الثلاثاء', 2: 'الأربعاء', 3: 'الخميس',
        4: 'الجمعة', 5: 'السبت', 6: 'الأحد'
    }
    
    months = {
        1: 'كانون الثاني', 2: 'شباط', 3: 'آذار', 4: 'نيسان',
        5: 'أيار', 6: 'حزيران', 7: 'تموز', 8: 'آب',
        9: 'أيلول', 10: 'تشرين الأول', 11: 'تشرين الثاني', 12: 'كانون الأول'
    }
    
    day_name = days.get(date_obj.weekday(), '')
    month_name = months.get(date_obj.month, '')
    
    # تنسيق: السبت، 10 تشرين الأول 2026 - 20:48
    return f"{day_name}، {date_obj.day} {month_name} {date_obj.year} - {date_obj.strftime('%H:%M')}"
