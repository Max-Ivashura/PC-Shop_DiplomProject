from django.urls import path, include
from django.views.decorators.http import require_http_methods
from . import views

app_name = 'compare'

# Основные URL-паттерны
urlpatterns = [
    path('', views.compare_detail, name='detail'),

    # API Endpoints
    path('api/', include([
        path('add/<int:product_id>/',
             require_http_methods(["POST"])(views.add_to_compare),
             name='api-add'),

        path('remove/<int:product_id>/',
             require_http_methods(["DELETE"])(views.remove_from_compare),
             name='api-remove'),

        path('clear/',
             require_http_methods(["DELETE"])(views.clear_comparison),
             name='api-clear'),
    ])),

    # HTML Views
    path('actions/', include([
        path('add/<int:product_id>/',
             views.add_to_compare,
             name='add'),

        path('remove/<int:product_id>/',
             views.remove_from_compare,
             name='remove'),

        path('clear/',
             views.clear_comparison,
             name='clear'),
    ])),
]
