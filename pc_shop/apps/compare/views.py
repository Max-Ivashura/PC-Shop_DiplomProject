from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.products.models import Product
from apps.compare.models import Comparison


@login_required
def add_to_compare(request, product_id):
    """AJAX-представление для добавления товара в сравнение"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        raise Http404

    product = get_object_or_404(Product, id=product_id)
    comparison = request.user.comparisons.first() or Comparison.objects.create(user=request.user)

    try:
        # Проверяем категорию перед добавлением
        if comparison.products.exists():
            existing_product = comparison.products.first()
            if existing_product.category != product.category:
                raise ValidationError("Можно сравнивать только товары одной категории")

        comparison.add_product(product)

        return JsonResponse({
            'success': True,
            'message': 'Товар добавлен в сравнение',
            'compare_count': comparison.products.count(),
            'max_reached': comparison.products.count() >= Comparison.MAX_PRODUCTS
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
def remove_from_compare(request, product_id):
    """AJAX-представление для удаления товара из сравнения"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        raise Http404

    product = get_object_or_404(Product, id=product_id)
    comparison = request.user.comparisons.first()

    if comparison:
        comparison.remove_product(product)
        remaining = comparison.products.count()

        return JsonResponse({
            'success': True,
            'compare_count': remaining,
            'redirect': reverse('compare:detail') if remaining > 0 else reverse('product_list')
        })

    return JsonResponse({'success': False, 'message': 'Сравнение не найдено'}, status=404)


@login_required
def compare_detail(request):
    """Основная страница сравнения"""
    comparison = request.user.comparisons.prefetch_related(
        'products__images',
        'products__attributes__attribute__group'
    ).first()

    if not comparison or comparison.products.count() == 0:
        return redirect('product_list')

    # Генерация матрицы атрибутов
    attributes_matrix = comparison.attributes_matrix

    return render(request, 'compare/compare_detail.html', {
        'comparison': comparison,
        'attributes_matrix': attributes_matrix,
        'MAX_PRODUCTS': Comparison.MAX_PRODUCTS
    })