from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """الحصول على قيمة من قاموس باستخدام مفتاح"""
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def time_format(value, format_str="H:i"):
    """تنسيق الوقت"""
    if value:
        return value.strftime(format_str.replace('H', '%H').replace('i', '%M'))
    return ""
