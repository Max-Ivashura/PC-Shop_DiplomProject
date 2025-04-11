from django.shortcuts import redirect, get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import F
from apps.products.models import Product
from apps.cart.utils import CartHandler
from apps.orders.models import Order, OrderItem
import json


@require_POST
def cart_add(request, product_id):
    """
    Добавление товара в корзину.
    """
    cart = CartHandler(request)
    product = get_object_or_404(Product, id=product_id)

    # Проверка доступности товара
    if not product.is_available or product.quantity <= 0:
        return JsonResponse({'success': False, 'message': 'Товар недоступен или закончился'}, status=400)

    # Получение количества из запроса
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            raise ValueError("Количество не может быть меньше 1")
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Некорректное количество'}, status=400)

    # Добавление товара в корзину
    cart.add(product=product, quantity=quantity)

    # Ответ для AJAX-запросов
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'total_items': cart.get_cart_items().count(),
            'message': f'{product.name} добавлен в корзину'
        })

    return redirect('cart_detail')


@require_POST
def cart_update(request, product_id):
    """
    Обновление количества товара в корзине.
    """
    cart = CartHandler(request)
    product = get_object_or_404(Product, id=product_id)

    # Парсинг данных из JSON
    try:
        data = json.loads(request.body)
        new_quantity = int(data.get('quantity', 1))
        if new_quantity < 1:
            raise ValueError("Количество не может быть меньше 1")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Некорректные данные'}, status=400)

    # Поиск товара в корзине
    cart_item = cart.cart.items.filter(product=product).first()
    if not cart_item:
        return JsonResponse({'success': False, 'message': 'Товар не найден в корзине'}, status=404)

    # Проверка доступного количества товара
    if new_quantity > product.quantity:
        return JsonResponse({'success': False, 'message': 'Недостаточно товара на складе'}, status=400)

    # Обновление количества
    old_quantity = cart_item.quantity
    cart_item.quantity = new_quantity
    cart_item.save()

    # Рендеринг HTML для корзины
    try:
        cart_items_html = render_to_string(
            'includes/cart_items.html',
            {'cart': cart},
            request=request
        )
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка рендеринга: {str(e)}'}, status=500)

    return JsonResponse({
        'success': True,
        'cart_count': cart.cart.items.count(),
        'cart_html': cart_items_html,
        'total_price': cart.get_total_price(),
        'old_quantity': old_quantity
    })


@require_POST
def cart_remove(request, product_id):
    """
    Удаление товара из корзины.
    """
    cart = CartHandler(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)

    # Ответ для AJAX-запросов
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'total_items': cart.get_cart_items().count(),
            'message': f'{product.name} удален из корзины'
        })

    return redirect('cart_detail')


def cart_detail(request):
    """
    Страница с деталями корзины.
    """
    cart = CartHandler(request)
    return render(request, 'cart/detail.html', {'cart': cart})


@login_required
def checkout(request):
    """
    Оформление заказа.
    """
    cart = CartHandler(request)
    if request.method == 'POST':
        # Создание заказа
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            email=request.POST['email'],
            address=request.POST['address']
        )

        # Перенос товаров из корзины в заказ
        for item in cart.get_cart_items():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price,
                quantity=item.quantity
            )

        # Очистка корзины
        cart.clear()

        return redirect('order_success', order_id=order.id)

    return render(request, 'cart/checkout.html', {'cart': cart})


def order_success(request, order_id):
    """
    Страница успешного оформления заказа.
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'cart/success.html', {'order': order})


@login_required
def cart_validate(request):
    cart = CartHandler(request)
    all_available = True
    for item in cart.get_cart_items():
        if not item.product.is_available or item.quantity > item.product.quantity:
            all_available = False
            break
    return JsonResponse({'all_available': all_available})