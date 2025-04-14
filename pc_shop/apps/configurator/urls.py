from django.urls import path
from . import views

app_name = 'configurator'

urlpatterns = [
    # Основной интерфейс конфигуратора
    path('', views.configurator, name='main'),

    # Управление сборками
    path('build/<int:build_id>/', views.build_detail, name='build_detail'),
    path('build/delete/<int:build_id>/', views.delete_build, name='delete_build'),
    path('toggle-visibility/<int:build_id>/',
         views.toggle_build_visibility,
         name='toggle_visibility'),

    # Публичные сборки
    path('community/', views.community_builds, name='community'),

    # API Endpoints
    path('api/save/', views.save_build_api, name='api_save'),
    path('api/check/', views.check_compatibility_api, name='api_check'),
    path('api/components/<int:type_id>/',
         views.get_components_api,
         name='api_components'),
]
