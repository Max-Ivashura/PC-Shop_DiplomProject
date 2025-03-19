from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from products.models import Product
from .utils import CartHandler
from orders.models import Order, OrderItem
from django.http import JsonResponse

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