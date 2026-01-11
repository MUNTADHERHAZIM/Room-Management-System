from django.contrib import admin
from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'stage', 'hours_per_week', 'is_active']
    list_filter = ['stage', 'department__college', 'department', 'is_active']
    search_fields = ['name', 'code', 'department__name']
    ordering = ['department', 'stage', 'name']
    list_editable = ['is_active']
    autocomplete_fields = ['department']
