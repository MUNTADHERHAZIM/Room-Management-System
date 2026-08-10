from functools import wraps
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test


def has_user_perm(user, perm_name):
    """التحقق التفاعلي من صلاحيات المستخدم"""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    from .models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.has_perm(perm_name)


def is_editor_check(user):
    """التحقق مما إذا كان المستخدم يملك صلاحية الإدخال (أدمن أو ضمن مجموعة مدخلي البيانات أو حسابه محدد كـ editor)"""
    if not user.is_authenticated:
        return False
    return has_user_perm(user, 'can_manage_schedules') or user.is_staff or user.groups.filter(name='Data Entry').exists()


def editor_required(view_func):
    """ديكوريتور لتقييد الوصول لمدخلي البيانات فقط"""
    actual_decorator = user_passes_test(
        is_editor_check,
        login_url='core:login',
        redirect_field_name=None
    )
    return actual_decorator(view_func)


def permission_required(perm_name):
    """ديكوريتور مخصص لتقييد الوصول حسب الصلاحيات الحبيبية (Granular RBAC)"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('core:login')
            if has_user_perm(request.user, perm_name):
                return view_func(request, *args, **kwargs)
            
            # ⛔ إظهار صفحة منع الوصول (403 Access Denied)
            context = {
                'perm_name': perm_name,
                'user': request.user
            }
            return render(request, 'core/403.html', context, status=403)
        return _wrapped_view
    return decorator

