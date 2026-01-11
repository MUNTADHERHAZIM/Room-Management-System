from django.urls import path
from . import views

app_name = 'calendar_app'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('holidays/', views.holiday_list, name='holidays'),
    path('holidays/create/', views.holiday_create, name='holiday_create'),
    path('holidays/<int:pk>/delete/', views.holiday_delete, name='holiday_delete'),
    path('off-days/', views.off_day_list, name='off_days'),
    path('off-days/create/', views.off_day_create, name='off_day_create'),
    path('off-days/<int:pk>/delete/', views.off_day_delete, name='off_day_delete'),
]
