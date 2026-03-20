# presenze/urls_profile.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]
