from django.shortcuts import redirect, get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from apps.products.models import Product
from apps.cart.utils import CartHandler
from apps.orders.models import Order, OrderItem
from django.http import JsonResponse
import json


@require_POST
def cart_add(request, product_id):
    cart = CartHandler(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product=product, quantity=quantity)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'total_items': cart.get_cart_items().count()})
    return redirect('cart_detail')


@require_POST
def cart_update(request, product_id):
    cart = CartHandler(request)
    product = get_object_or_404(Product, id=product_id)

    try:
        data = json.loads(request.body)
        new_quantity = int(data.get('quantity', 1))
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Неверный формат данных',
            'old_quantity': 1
        }, status=400)
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Некорректное количество',
            'old_quantity': 1
        }, status=400)

    if new_quantity < 1:
        return JsonResponse({
            'success': False,
            'message': 'Количество не может быть меньше 1',
            'old_quantity': 1
        }, status=400)

    # Проверяем наличие товара в корзине
    cart_item = cart.cart.items.filter(product=product).first()
    if not cart_item:
        return JsonResponse({
            'success': False,
            'message': 'Товар не найден в корзине',
            'old_quantity': 0
        }, status=404)

    # Сохраняем старое количество
    old_quantity = cart_item.quantity

    # Обновляем количество
    try:
        cart_item.quantity = new_quantity
        cart_item.save()
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка обновления: {str(e)}',
            'old_quantity': old_quantity
        }, status=500)

    # Подготовка ответа
    try:
        cart_items_html = render_to_string(
            'includes/cart_items.html',
            {'cart': cart},
            request=request
        )
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка рендеринга: {str(e)}',
            'old_quantity': old_quantity
        }, status=500)

    return JsonResponse({
        'success': True,
        'cart_count': cart.cart.items.count(),
        'cart_html': cart_items_html,
        'total_price': cart.get_total_price(),
        'old_quantity': old_quantity
    })


@require_POST
def cart_remove(request, product_id):
    cart = CartHandler(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart_detail')


def cart_detail(request):
    cart = CartHandler(request)
    return render(request, 'cart/detail.html', {'cart': cart})


def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'cart/success.html', {'order': order})


@login_required
def checkout(request):
    cart = CartHandler(request)
    if request.method == 'POST':
        # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            email=request.POST['email'],
            address=request.POST['address']
        )
        # Переносим товары из корзины в заказ
        for item in cart.get_cart_items():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price,
                quantity=item.quantity
            )
        cart.clear()
        return redirect('order_success', order_id=order.id)
    return render(request, 'cart/checkout.html', {'cart': cart})
