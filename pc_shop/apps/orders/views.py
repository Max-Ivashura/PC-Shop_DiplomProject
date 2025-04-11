from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages

from apps.cart.utils import CartHandler
from .models import Order, OrderItem
from apps.products.models import Product
from apps.cart.models import Cart


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')


class OrderCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cart_handler = CartHandler(request)
        cart = cart_handler.cart

        # Проверка товаров в корзине
        if not cart.items.exists():
            messages.error(request, 'Корзина пуста')
            return redirect('cart_detail')

        # Проверка доступности товаров
        for item in cart.items.all():
            if item.quantity > item.product.quantity:
                messages.error(request, f'Товара "{item.product.name}" недостаточно на складе')
                return redirect('cart_detail')

        try:
            with transaction.atomic():
                # Создание заказа
                order = Order.objects.create(
                    user=request.user,
                    first_name=request.POST.get('first_name') or request.user.first_name,
                    last_name=request.POST.get('last_name') or request.user.last_name,
                    email=request.POST.get('email') or request.user.email,
                    address=request.POST.get('address') or getattr(request.user, 'profile', {}).get('address', '')
                )

                # Перенос товаров
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity,
                        name_snapshot=item.product.name  # Фиксируем название
                    )
                    # Уменьшаем остатки
                    item.product.quantity -= item.quantity
                    item.product.save()

                # Очистка корзины
                cart_handler.clear()

                messages.success(request, 'Заказ успешно оформлен')
                return redirect('order_detail', pk=order.pk)

        except Exception as e:
            messages.error(request, f'Ошибка оформления заказа: {str(e)}')
            return redirect('cart_detail')


class OrderCancelView(LoginRequiredMixin, UpdateView):
    model = Order
    fields = []
    template_name = 'orders/order_cancel.html'
    success_url = reverse_lazy('order_list')

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, status='processing')

    def form_valid(self, form):
        form.instance.status = 'canceled'
        messages.info(self.request, 'Заказ отменен')
        return super().form_valid(form)