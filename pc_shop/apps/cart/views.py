from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
import json

from apps.products.models import Product
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.cart.utils import CartHandler


@require_POST
def cart_add(request, product_id):
    """Добавление товара с резервированием и конкурентным контролем"""
    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product_id)
            cart = CartHandler(request).cart

            if not cart.is_active:
                return JsonResponse({
                    'error': 'Корзина завершена. Создайте новую корзину'
                }, status=400)

            quantity = int(request.POST.get('quantity', 1))

            try:
                cart.add_product(product, quantity)
            except ValidationError as e:
                return JsonResponse({'error': str(e)}, status=400)

            return JsonResponse({
                'success': True,
                'total_items': cart.total_items,
                'reserved': product.quantity,
                'cart_total': cart.get_total_price()
            })

    except (Product.DoesNotExist, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
def cart_update(request, product_id):
    """Атомарное обновление количества с проверкой резерва"""
    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product_id)
            cart = CartHandler(request).cart
            data = json.loads(request.body)
            new_quantity = int(data['quantity'])

            if not cart.is_active:
                raise PermissionDenied("Корзина завершена")

            item = cart.items.get(product=product)
            delta = new_quantity - item.quantity

            if product.quantity < delta:
                return JsonResponse({
                    'error': f'Доступно только {product.quantity} шт.'
                }, status=400)

            item.quantity = new_quantity
            item.save()
            product.quantity -= delta
            product.save()

            return JsonResponse({
                'success': True,
                'new_quantity': item.quantity,
                'item_total': item.get_cost(),
                'cart_total': cart.get_total_price(),
                'product_reserved': product.quantity
            })

    except (CartItem.DoesNotExist, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=404)


@require_POST
def cart_remove(request, product_id):
    """Удаление с возвратом резерва"""
    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product_id)
            cart = CartHandler(request).cart

            if not cart.is_active:
                raise PermissionDenied("Корзина завершена")

            item = cart.items.get(product=product)
            product.quantity += item.quantity
            product.save()
            item.delete()

            return JsonResponse({
                'success': True,
                'cart_total': cart.get_total_price(),
                'total_items': cart.total_items,
                'product_restored': product.quantity
            })

    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Товар не найден'}, status=404)


@login_required
def checkout(request):
    """Оформление заказа с блокировкой корзины"""
    cart = CartHandler(request).cart

    if not cart.is_active or cart.total_items == 0:
        return redirect('cart_detail')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Создание заказа
                order = Order.objects.create(
                    user=request.user,
                    first_name=request.POST['first_name'],
                    last_name=request.POST['last_name'],
                    email=request.POST['email'],
                    address=request.POST['address'],
                    total=cart.get_total_price()
                )

                # Перенос товаров
                items = cart.items.select_related('product')
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity,
                        name_snapshot=item.product.name
                    ) for item in items
                ])

                # Блокировка корзины
                cart.converted_order = order
                cart.save()

                # Отправка уведомлений и очистка
                # ... (ваш код отправки email/SMS)

                return redirect('order_success', order_id=order.id)

        except KeyError as e:
            return HttpResponseBadRequest(f"Не заполнено поле: {str(e)}")

    return render(request, 'cart/checkout.html', {
        'cart': cart,
        'active_cart': cart.is_active
    })


def cart_detail(request):
    """Детализация корзины с блокировкой"""
    cart = CartHandler(request).cart
    return render(request, 'cart/detail.html', {
        'cart': cart,
        'readonly': not cart.is_active
    })


def order_success(request, order_id):
    """Страница успешного заказа с защитой доступа"""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'cart/success.html', {
        'order': order,
        'cart': order.source_cart
    })


@login_required
def cart_validate(request):
    """Проверка доступности всех товаров"""
    cart = CartHandler(request).cart
    problems = []

    for item in cart.items.select_related('product'):
        if item.quantity > item.product.quantity:
            problems.append({
                'product': item.product.name,
                'available': item.product.quantity,
                'requested': item.quantity
            })

    return JsonResponse({
        'valid': len(problems) == 0,
        'problems': problems,
        'cart_id': cart.id
    })
