from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('edit/', views.edit_profile, name='edit_profile'),
    path('password/', views.change_password, name='change_password'),
    path('my-builds/', views.user_builds, name='user_builds'),
]