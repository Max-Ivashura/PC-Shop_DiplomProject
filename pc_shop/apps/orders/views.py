from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from apps.cart.utils import CartHandler
from .models import Order, OrderItem
from .forms import OrderCreateForm, OrderStatusUpdateForm  # Предполагается, что форма создана
from apps.products.models import Product
from apps.cart.models import Cart


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(user=self.request.user)
            .select_related('user')
            .prefetch_related('items__product')
            .only(
                'id', 'status', 'created_at',
                'total_price', 'paid', 'user__email'
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = dict(Order.STATUS_CHOICES)
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(user=self.request.user)
            .prefetch_related(
                Prefetch('items', queryset=OrderItem.objects.select_related('product'))
            )
        )

    def dispatch(self, request, *args, **kwargs):
        order = self.get_object()
        if order.user != request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_protect, name='dispatch')
class OrderCreateView(FormView):
    template_name = 'orders/order_create.html'
    form_class = OrderCreateForm
    success_url = reverse_lazy('order_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user if self.request.user.is_authenticated else None
        kwargs['user'] = user
        return kwargs

    def form_valid(self, form):
        cart_handler = CartHandler(self.request)
        cart = cart_handler.cart

        if not cart or not cart.items.exists():
            messages.error(self.request, 'Ваша корзина пуста')
            return redirect('cart_detail')

        try:
            with transaction.atomic():
                order = self.create_order_from_form(form, cart)
                self.create_order_items(order, cart)
                self.clear_cart_and_associate(cart_handler, cart, order)

                messages.success(self.request, 'Заказ успешно оформлен!')
                return redirect(order.get_absolute_url())

        except Product.DoesNotExist:
            messages.error(self.request, 'Один из товаров больше недоступен')
        except ValidationError as e:
            messages.error(self.request, f'Ошибка: {e}')
        except Exception as e:
            messages.error(self.request, f'Системная ошибка: {str(e)}')

        return redirect('cart_detail')

    def create_order_from_form(self, form, cart):
        return Order.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            email=form.cleaned_data['email'],
            phone=form.cleaned_data['phone'],
            address=form.cleaned_data['address'],
            total_price=cart.get_total_price()
        )

    def create_order_items(self, order, cart):
        items_to_create = []
        for item in cart.items.select_related('product'):
            if item.product.quantity < item.quantity:
                raise ValidationError(f'Недостаточно товара: {item.product.name}')

            items_to_create.append(OrderItem(
                order=order,
                product=item.product,
                price=item.product.price,
                quantity=item.quantity,
                name_snapshot=item.product.name
            ))

            item.product.quantity -= item.quantity
            item.product.save(update_fields=['quantity'])

        OrderItem.objects.bulk_create(items_to_create)

    def clear_cart_and_associate(self, cart_handler, cart, order):
        cart.converted_order = order
        cart.save(update_fields=['converted_order'])
        cart_handler.clear()


class OrderCancelView(LoginRequiredMixin, UpdateView):
    model = Order
    form_class = OrderStatusUpdateForm  # Новая форма для статусов
    template_name = 'orders/order_cancel.html'
    success_url = reverse_lazy('order_list')

    def get_queryset(self):
        return super().get_queryset().filter(
            user=self.request.user,
            status__in=['processing', 'shipped']
        )

    def form_valid(self, form):
        if form.cleaned_data['status'] != 'canceled':
            form.add_error(None, 'Недопустимый статус для отмены')
            return self.form_invalid(form)

        return super().form_valid(form)
