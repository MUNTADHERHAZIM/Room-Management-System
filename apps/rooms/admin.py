from django.contrib import admin
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'department', 'capacity', 'floor', 'is_active']
    list_filter = ['room_type', 'department__college', 'department', 'is_active', 'has_projector', 'has_computers']
    search_fields = ['name', 'department__name', 'department__college__name']
    ordering = ['department', 'name']
    list_editable = ['is_active']
    autocomplete_fields = ['department']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'room_type', 'department', 'capacity', 'floor')
        }),
        ('التجهيزات', {
            'fields': ('has_projector', 'has_computers', 'has_whiteboard', 'has_air_conditioning')
        }),
        ('إضافي', {
            'fields': ('notes', 'is_active'),
            'classes': ('collapse',)
        }),
    )
