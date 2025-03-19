from django.urls import path
from . import views

urlpatterns = [
    path('configurator/', views.configurator, name='configurator'),
    path('build/save/', views.save_build, name='save_build'),
    path('community-builds/', views.community_builds, name='community_builds'),
    path('build/<int:build_id>/', views.build_detail, name='build_detail'),
    path('api/components/<slug:category_slug>/', views.get_components, name='api_components'),
    path('api/check-compatibility/', views.check_compatibility, name='api_check_compatibility'),
    path('api/save-build/', views.save_build, name='api_save_build'),
]