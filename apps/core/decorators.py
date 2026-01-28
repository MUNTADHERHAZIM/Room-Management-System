from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def is_editor_check(user):
    """التحقق مما إذا كان المستخدم يملك صلاحية الإدخال (أدمن أو ضمن مجموعة مدخلي البيانات)"""
    if not user.is_authenticated:
        return False
    return user.is_staff or user.groups.filter(name='Data Entry').exists()

def editor_required(view_func):
    """ديكوريتور لتقييد الوصول لمدخلي البيانات فقط"""
    actual_decorator = user_passes_test(
        is_editor_check,
        login_url='admin:login',
        redirect_field_name=None
    )
    return actual_decorator(view_func)
