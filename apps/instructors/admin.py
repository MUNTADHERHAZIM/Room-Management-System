from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Instructor
from .resources import InstructorResource


@admin.register(Instructor)
class InstructorAdmin(ImportExportModelAdmin):
    resource_class = InstructorResource
    list_display = ['name', 'academic_title', 'department', 'specialization', 'is_active']
    list_filter = ['academic_title', 'department__college', 'department', 'is_active']
    search_fields = ['name', 'email', 'specialization', 'department__name']
    ordering = ['department', 'name']
    list_editable = ['is_active']
    autocomplete_fields = ['department']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'academic_title', 'department', 'specialization')
        }),
        ('معلومات الاتصال', {
            'fields': ('email', 'phone')
        }),
        ('إضافي', {
            'fields': ('notes', 'is_active'),
            'classes': ('collapse',)
        }),
    )
