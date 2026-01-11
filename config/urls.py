"""
URL configuration for Room Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('rooms/', include('apps.rooms.urls')),
    path('instructors/', include('apps.instructors.urls')),
    path('subjects/', include('apps.subjects.urls')),
    path('schedules/', include('apps.schedules.urls')),
    path('calendar/', include('apps.calendar_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = 'نظام إدارة القاعات'
admin.site.site_title = 'إدارة القاعات'
admin.site.index_title = 'لوحة التحكم'
