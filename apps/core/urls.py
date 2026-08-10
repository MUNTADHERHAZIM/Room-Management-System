from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/departments/<int:college_id>/', views.get_departments, name='get_departments'),
    path('api/server-time/', views.server_time, name='server_time'),
    
    # 🔑 Portal for Accounts and Permissions Management
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.create_user_view, name='user_create'),
    path('users/<int:user_id>/permissions/', views.update_user_permissions_view, name='user_update_permissions'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status_view, name='user_toggle_status'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password_view, name='user_reset_password'),
    path('users/<int:user_id>/delete/', views.delete_user_view, name='user_delete'),
]
