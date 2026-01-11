from django.contrib import admin
from .models import College, Department


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department_count', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']
    ordering = ['name']

    def department_count(self, obj):
        return obj.departments.count()
    department_count.short_description = 'عدد الأقسام'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'college', 'created_at']
    search_fields = ['name', 'code', 'college__name']
    list_filter = ['college', 'created_at']
    ordering = ['college', 'name']
    autocomplete_fields = ['college']
