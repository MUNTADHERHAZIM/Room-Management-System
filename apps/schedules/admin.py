from django.contrib import admin
from .models import Schedule


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['subject', 'room', 'instructor', 'day', 'start_time', 'end_time', 'schedule_type', 'is_active']
    list_filter = ['day', 'schedule_type', 'room__department__college', 'room__department', 'is_active']
    search_fields = ['subject__name', 'instructor__name', 'room__name']
    ordering = ['day', 'start_time']
    list_editable = ['is_active']
    autocomplete_fields = ['room', 'instructor', 'subject']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('معلومات الحصة', {
            'fields': ('subject', 'instructor', 'room', 'schedule_type')
        }),
        ('الوقت', {
            'fields': ('day', 'start_time', 'end_time')
        }),
        ('إضافي', {
            'fields': ('notes', 'is_active'),
            'classes': ('collapse',)
        }),
    )
