from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.session_list, name="session_list"),
    path("guide/", views.offline_setup_guide, name="offline_setup_guide"),
    path("digital-id/", views.digital_id, name="digital_id"),
    path("session/<int:pk>/", views.session_detail, name="session_detail"),
    path("session/<int:pk>/scanner/", views.scanner_view, name="scanner_view"),
    path("session/<int:pk>/rotate-qr/", views.rotate_qr, name="rotate_qr"),
    path("session/create/<int:schedule_pk>/", views.create_session, name="create_session"),
    path("session/create-adhoc/", views.create_adhoc_session, name="create_adhoc_session"),
    path("scan/<str:otp_token>/", views.student_scan, name="student_scan"),
    path("session/<int:pk>/submit-attendance/", views.submit_attendance, name="submit_attendance"),
    path('join/', views.student_join_by_pin, name='join_by_pin'),
    
    # تصدير الجلسات المحددة
    path('export/excel/<int:pk>/', views.export_excel, name='export_excel'),
    path("session/<int:pk>/export/pdf/", views.export_pdf, name="export_pdf"),

    # المرونة والسجل العام الشامل
    path("history/", views.attendance_history, name="attendance_history"),
    path("session/<int:pk>/toggle-status/", views.toggle_record_status, name="toggle_record_status"),
    path("session/<int:pk>/mark-remaining-absent/", views.mark_remaining_absent, name="mark_remaining_absent"),
    path("session/<int:pk>/add-manual-record/", views.add_manual_record, name="add_manual_record"),
    path("student/<int:student_pk>/history/", views.student_attendance_detail, name="student_attendance_detail"),
    path("history/export/excel/", views.export_history_excel, name="export_history_excel"),
    path("history/export/pdf/", views.export_history_pdf, name="export_history_pdf"),
]

