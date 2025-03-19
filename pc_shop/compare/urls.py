from django.urls import path
from . import views

urlpatterns = [
    path('', views.compare_view, name='compare'),
    path('add/<int:product_id>/', views.add_to_comparison, name='add_to_compare'),
    path('remove/<int:product_id>/', views.remove_from_comparison, name='remove_from_compare'),
]