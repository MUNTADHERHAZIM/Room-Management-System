from django.utils import timezone
from django.core.cache import cache
from .views import get_arabic_day
from .decorators import has_user_perm


def get_user_permissions(user):
    """جلب قائمة بكل صلاحيات المستخدم الحالية بصورة قاموس"""
    if not user.is_authenticated:
        return {}
    
    if hasattr(user, '_cached_user_perms'):
        return user._cached_user_perms

    if user.is_superuser or user.is_staff:
        perms = {
            'can_view_schedules': True,
            'can_manage_schedules': True,
            'can_access_attendance': True,
            'can_manage_attendance': True,
            'can_access_exams': True,
            'can_manage_rooms': True,
            'can_manage_instructors': True,
            'can_manage_subjects': True,
            'can_manage_users': True,
            'is_admin': True,
        }
        user._cached_user_perms = perms
        return perms

    from .models import UserProfile
    try:
        profile = getattr(user, 'profile', None)
        if not profile:
            profile, _ = UserProfile.objects.get_or_create(user=user)
    except Exception:
        profile, _ = UserProfile.objects.get_or_create(user=user)

    perms = {
        'can_view_schedules': profile.has_perm('can_view_schedules'),
        'can_manage_schedules': profile.has_perm('can_manage_schedules'),
        'can_access_attendance': profile.has_perm('can_access_attendance'),
        'can_manage_attendance': profile.has_perm('can_manage_attendance'),
        'can_access_exams': profile.has_perm('can_access_exams'),
        'can_manage_rooms': profile.has_perm('can_manage_rooms'),
        'can_manage_instructors': profile.has_perm('can_manage_instructors'),
        'can_manage_subjects': profile.has_perm('can_manage_subjects'),
        'can_manage_users': profile.has_perm('can_manage_users'),
        'is_admin': profile.role == 'admin',
    }
    user._cached_user_perms = perms
    return perms


def is_editor(user):
    """التحقق مما إذا كان المستخدم يملك صلاحية الإدخال"""
    if not user.is_authenticated:
        return False
    if hasattr(user, '_cached_is_editor'):
        return user._cached_is_editor

    val = user.is_superuser or user.is_staff or has_user_perm(user, 'can_manage_schedules') or user.groups.filter(name='Data Entry').exists()
    user._cached_is_editor = val
    return val


def _get_cached_settings():
    """جلب إعدادات النظام مع تخزين مؤقت (30 ثانية) لتقليل استعلامات قاعدة البيانات"""
    from .models import SystemSettings
    settings = cache.get('system_settings')
    if settings is None:
        settings = SystemSettings.load()
        cache.set('system_settings', settings, 30)  # cache 30 seconds
    return settings


def server_time_context(request):
    """توفير وقت الخادم والصلاحيات بشكل عالمي للقوالب"""
    now = timezone.localtime(timezone.now())
    return {
        'current_time': now,
        'current_day': get_arabic_day(now),
        'current_year': now.year,
        'is_editor': is_editor(request.user),
        'system_settings': _get_cached_settings(),
        'user_perms': get_user_permissions(request.user),
    }
