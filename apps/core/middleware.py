from django.shortcuts import render
from .models import SystemSettings

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow access to admin, static, and media files
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Check if maintenance mode is on
        try:
            settings = SystemSettings.load()
            if settings.is_maintenance_mode:
                # Allow staff members and editors to access the site
                if request.user.is_authenticated and (request.user.is_staff or request.user.groups.filter(name='Data Entry').exists()):
                    return self.get_response(request)
                
                # Render maintenance page for everyone else
                return render(request, 'maintenance.html', status=503)
        except Exception:
            # Fallback if DB is not ready or settings missing
            pass

        return self.get_response(request)
