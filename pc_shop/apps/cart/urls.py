from django.urls import path
from . import views

urlpatterns = [
    # Страница корзины
    path('', views.cart_detail, name='cart_detail'),

    # Добавление товара в корзину
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),

    # Удаление товара из корзины
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),

    # Обновление количества товара в корзине
    path('update/<int:product_id>/', views.cart_update, name='cart_update'),

    # Оформление заказа
    path('checkout/', views.checkout, name='checkout'),

    # Страница успешного оформления заказа
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('validate/', views.cart_validate, name='cart_validate'),
]