from django.urls import path
from . import views

urlpatterns = [
    # Основная страница сравнения
    path('', views.compare_detail, name='compare'),

    # AJAX-операции
    path('add/<int:product_id>/', views.add_to_compare, name='add'),
    path('remove/<int:product_id>/', views.remove_from_compare, name='remove'),
]