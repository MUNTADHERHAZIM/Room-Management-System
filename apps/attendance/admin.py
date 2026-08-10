from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    raw_id_fields = ["student"]


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ["schedule", "date", "is_active", "created_at"]
    list_filter = ["date", "is_active", "schedule__room", "schedule__instructor"]
    search_fields = ["schedule__subject__name", "session_token"]
    inlines = [AttendanceRecordInline]
    date_hierarchy = "date"


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ["student", "session", "status", "scanned_at", "device_fingerprint"]
    list_filter = ["status", "scanned_at", "session__date"]
    search_fields = ["student__name", "student__university_id", "session__schedule__subject__name"]
    raw_id_fields = ["student", "session"]
