from django.utils import timezone
from .views import get_arabic_day
from .models import SystemSettings

def is_editor(user):
    """التحقق مما إذا كان المستخدم يملك صلاحية الإدخال (أدمن أو ضمن مجموعة مدخلي البيانات)"""
    if not user.is_authenticated:
        return False
    return user.is_staff or user.groups.filter(name='Data Entry').exists()

def server_time_context(request):
    """توفير وقت الخادم واليوم بشكل عالمي للقوالب"""
    now = timezone.localtime(timezone.now())
    return {
        'current_time': now,
        'current_day': get_arabic_day(now),
        'current_year': now.year,
        'is_editor': is_editor(request.user),
        'system_settings': SystemSettings.load(),
    }
