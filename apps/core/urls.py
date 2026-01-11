from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('api/departments/<int:college_id>/', views.get_departments, name='get_departments'),
    path('api/server-time/', views.server_time, name='server_time'),
]
