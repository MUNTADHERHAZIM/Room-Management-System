from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    # الطلاب
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/import/', views.student_import, name='student_import'),

    # الجلسات الامتحانية
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),

    # إدارة المواد في الجلسة
    path('sessions/<int:session_pk>/add-subject/', views.add_subject_to_session, name='add_subject'),
    path('sessions/<int:session_pk>/remove-subject/<int:es_pk>/', views.remove_subject_from_session, name='remove_subject'),

    # إدارة القاعات في الجلسة
    path('sessions/<int:session_pk>/add-hall/', views.add_hall_to_session, name='add_hall'),
    path('sessions/<int:session_pk>/hall/<int:hall_pk>/edit/', views.edit_hall, name='edit_hall'),
    path('sessions/<int:session_pk>/remove-hall/<int:hall_pk>/', views.remove_hall_from_session, name='remove_hall'),
    path('sessions/<int:session_pk>/swap-seats/', views.swap_seats, name='swap_seats'),

    # إدارة طلاب المادة
    path('sessions/<int:session_pk>/subject/<int:es_pk>/students/', views.manage_subject_students, name='manage_subject_students'),

    # التوزيع الذكي
    path('sessions/<int:pk>/generate/', views.generate_seating, name='generate_seating'),
    path('sessions/<int:pk>/map/', views.seating_map, name='seating_map'),
    path('sessions/<int:pk>/lists/', views.hall_student_lists, name='hall_student_lists'),
    path('sessions/<int:pk>/cards/', views.seat_cards, name='seat_cards'),
    path('sessions/<int:pk>/attendance/', views.department_attendance_lists, name='department_attendance_lists'),
    path('sessions/<int:pk>/excel/', views.session_excel_export, name='session_excel_export'),
    path('sessions/<int:pk>/pdf/', views.seating_pdf, name='seating_pdf'),
    path('sessions/<int:pk>/lookup/', views.student_lookup, name='student_lookup'),
]
