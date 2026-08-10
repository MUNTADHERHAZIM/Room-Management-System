from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Student, ExamSession, ExamSessionSubject, HallSetup, SeatingAssignment
from .resources import StudentResource


@admin.register(Student)
class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource
    list_display = ['name', 'university_id', 'department', 'stage', 'family_name', 'is_active']
    list_filter = ['department__college', 'department', 'stage', 'is_active']
    search_fields = ['name', 'university_id', 'family_name']
    ordering = ['department', 'stage', 'name']
    list_editable = ['is_active']


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'start_time', 'end_time', 'semester', 'is_distributed']
    list_filter = ['semester', 'is_distributed', 'date']
    search_fields = ['name']
    ordering = ['-date']


@admin.register(ExamSessionSubject)
class ExamSessionSubjectAdmin(admin.ModelAdmin):
    list_display = ['session', 'subject', 'color_code']
    list_filter = ['session']
    filter_horizontal = ['students']


@admin.register(HallSetup)
class HallSetupAdmin(admin.ModelAdmin):
    list_display = ['session', 'room', 'rows', 'columns', 'seat_type', 'spacing_mode', 'effective_capacity']
    list_filter = ['session', 'seat_type', 'spacing_mode']


@admin.register(SeatingAssignment)
class SeatingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['session', 'student', 'hall_setup', 'seat_label', 'row', 'column']
    list_filter = ['session', 'hall_setup__room']
    search_fields = ['student__name', 'student__university_id', 'seat_label']
    ordering = ['session', 'hall_setup', 'row', 'column']
