from django.urls import path
from . import views

app_name = 'subjects'

urlpatterns = [
    path('', views.subject_list, name='list'),
    path('create/', views.subject_create, name='create'),
    path('<int:pk>/edit/', views.subject_edit, name='edit'),
    path('<int:pk>/delete/', views.subject_delete, name='delete'),
]
