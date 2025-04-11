from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Список заказов
    path('', views.OrderListView.as_view(), name='order_list'),

    # Детальная страница заказа
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),

    # Создание заказа из корзины
    path('create/', views.OrderCreateView.as_view(), name='order_create'),

    # Отмена заказа
    path('<int:pk>/cancel/', views.OrderCancelView.as_view(), name='order_cancel'),

    # Для AJAX-запросов (если понадобится)
    # path('api/update-status/', views.OrderStatusUpdateView.as_view(), name='api_order_status'),
]