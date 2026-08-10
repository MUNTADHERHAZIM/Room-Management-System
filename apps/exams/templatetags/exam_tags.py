from django import template

register = template.Library()


@register.simple_tag
def row_letter(index):
    """تحويل رقم الصف إلى حرف: 0→A, 1→B, ..."""
    return chr(65 + int(index))
