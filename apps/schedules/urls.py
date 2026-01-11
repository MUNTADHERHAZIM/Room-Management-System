from django.urls import path
from . import views

app_name = 'schedules'

urlpatterns = [
    path('', views.schedule_list, name='list'),
    path('create/', views.schedule_create, name='create'),
    path('<int:pk>/edit/', views.schedule_edit, name='edit'),
    path('<int:pk>/delete/', views.schedule_delete, name='delete'),
    path('find-room/', views.find_available_room, name='find_room'),
    path('timeline/', views.timeline_view, name='timeline'),
    path('grid/', views.grid_view, name='grid'),
    path('day-schedule/', views.day_schedule, name='day_schedule'),
]
