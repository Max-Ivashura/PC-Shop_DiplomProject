from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from apps.products.models import Product
from django.http import JsonResponse
from apps.compare.models import Comparison


@login_required
def add_to_compare(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    comparison, created = Comparison.objects.get_or_create(user=request.user)

    # Проверка категории
    if comparison.products.exists():
        existing_product = comparison.products.first()
        if existing_product.category != product.category:
            return JsonResponse({
                'success': False,
                'message': 'Можно сравнивать только товары одной категории'
            })

    comparison.products.add(product)
    return JsonResponse({
        'success': True,
        'message': 'Товар добавлен в сравнение',
        'compare_count': comparison.products.count()
    })

def remove_from_comparison(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    comparison = request.user.comparisons.first()
    if comparison:
        comparison.products.remove(product)
    return redirect('compare_view')


# compare/views.py
@login_required
def compare_view(request):
    # Проверяем, есть ли сравнения у пользователя
    comparison = request.user.comparisons.first()
    products = comparison.products.all() if comparison else []

    # Если товаров нет — перенаправляем
    if not products:
        return redirect('product_list')  # Или другая страница

    # Группируем характеристики
    grouped_attributes = {}
    for product in products:
        for pa in product.attributes.select_related('attribute__group').all():
            group_name = pa.attribute.group.name
            attr_name = pa.attribute.name
            grouped_attributes.setdefault(group_name, {}).setdefault(attr_name, {})[product.id] = pa.value

    return render(request, 'compare/compare.html', {
        'products': products,
        'grouped_attributes': grouped_attributes
    })