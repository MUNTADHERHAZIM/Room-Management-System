from django.utils import timezone
from .views import get_arabic_day

def server_time_context(request):
    """توفير وقت الخادم واليوم بشكل عالمي للقوالب"""
    now = timezone.localtime(timezone.now())
    return {
        'current_time': now,
        'current_day': get_arabic_day(now),
        'current_year': now.year,
    }
