from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Список заказов пользователя
    path(
        'history/',
        views.OrderListView.as_view(),
        name='order_list'
    ),

    # Детальная информация о заказе
    path(
        '<int:pk>/',
        views.OrderDetailView.as_view(),
        name='order_detail'
    ),

    # Создание нового заказа
    path(
        'create/',
        views.OrderCreateView.as_view(),
        name='order_create'
    ),

    # Отмена незавершенного заказа
    path(
        '<int:pk>/cancel/',
        views.OrderCancelView.as_view(),
        name='order_cancel'
    ),
]