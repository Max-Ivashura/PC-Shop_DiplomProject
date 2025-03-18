from django.urls import path
from . import views

urlpatterns = [
    path('configurator/', views.configurator, name='configurator'),
    path('build/save/', views.save_build, name='save_build'),
    path('community-builds/', views.community_builds, name='community_builds'),
    path('build/<int:build_id>/', views.build_detail, name='build_detail'),
]