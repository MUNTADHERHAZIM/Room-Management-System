from django.contrib import admin
from .models import Holiday, DepartmentOffDay


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'recurring', 'created_at']
    list_filter = ['recurring', 'date']
    search_fields = ['name', 'description']
    ordering = ['-date']
    date_hierarchy = 'date'


@admin.register(DepartmentOffDay)
class DepartmentOffDayAdmin(admin.ModelAdmin):
    list_display = ['department', 'day', 'created_at']
    list_filter = ['day', 'department__college', 'department']
    search_fields = ['department__name', 'notes']
    ordering = ['department', 'day']
    autocomplete_fields = ['department']
