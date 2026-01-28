from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Subject
from .resources import SubjectResource


@admin.register(Subject)
class SubjectAdmin(ImportExportModelAdmin):
    resource_class = SubjectResource
    list_display = ['name', 'code', 'department', 'stage', 'hours_per_week', 'is_active']
    list_filter = ['stage', 'department__college', 'department', 'is_active']
    search_fields = ['name', 'code', 'department__name']
    ordering = ['department', 'stage', 'name']
    list_editable = ['is_active']
    autocomplete_fields = ['department']
