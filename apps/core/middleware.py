from django.shortcuts import render
from django.core.cache import cache


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow access to admin, static, and media files
        if request.path.startswith(('/admin/', '/static/', '/media/')):
            return self.get_response(request)

        # ✅ Check if maintenance mode is on (with cache to avoid DB hit on every request)
        try:
            settings = cache.get('system_settings')
            if settings is None:
                from .models import SystemSettings
                settings = SystemSettings.load()
                cache.set('system_settings', settings, 5)

            if settings.is_maintenance_mode:
                # Allow staff members and editors to access the site
                if request.user.is_authenticated and (
                    request.user.is_staff or
                    request.user.groups.filter(name='Data Entry').exists()
                ):
                    return self.get_response(request)

                # Render maintenance page for everyone else
                return render(request, 'maintenance.html', status=503)
        except Exception:
            pass

        return self.get_response(request)
