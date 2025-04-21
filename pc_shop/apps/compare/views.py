from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.sessions.models import Session
from django.conf import settings
from django.db.models import Q
from apps.products.models import Product
from apps.compare.models import Comparison, ComparisonItem


def _get_current_comparison(request):
    """Получение или создание текущего сравнения"""
    if request.user.is_authenticated:
        comparison, created = Comparison.objects.get_or_create(user=request.user)
        return comparison

    # Для анонимных пользователей используем сессию
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    comparison, created = Comparison.objects.get_or_create(
        session_key=session_key,
        defaults={'user': None}
    )
    return comparison


def _get_comparison_for_view(request):
    """Получение сравнения с оптимизированными запросами"""
    q_filter = Q(user=request.user) if request.user.is_authenticated else Q(session_key=request.session.session_key)

    return Comparison.objects.filter(q_filter).prefetch_related(
        'products__images',
        'products__attributes__attribute__groups__group__category',
        'products__category'
    ).first()


@login_required
def add_to_compare(request, product_id):
    """AJAX-добавление товара в сравнение"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        raise Http404

    product = get_object_or_404(Product, id=product_id)
    comparison = _get_current_comparison(request)

    try:
        comparison.add_product(product)
        return JsonResponse({
            'success': True,
            'message': 'Товар добавлен в сравнение',
            'compare_count': comparison.products.count(),
            'max_reached': comparison.products.count() >= Comparison.MAX_PRODUCTS,
            'category': comparison.category.name if comparison.category else ''
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'error_code': 'category_mismatch' if 'категории' in str(e) else 'limit_reached'
        }, status=400)


def remove_from_compare(request, product_id):
    """AJAX-удаление товара из сравнения"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        raise Http404

    product = get_object_or_404(Product, id=product_id)
    comparison = _get_current_comparison(request)

    if not comparison:
        return JsonResponse({'success': False, 'message': 'Сравнение не найдено'}, status=404)

    try:
        comparison.remove_product(product)
        remaining = comparison.products.count()

        response_data = {
            'success': True,
            'compare_count': remaining,
            'is_empty': remaining == 0
        }

        if remaining == 0:
            response_data['redirect'] = reverse('product_list')

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def compare_detail(request):
    """Детальная страница сравнения"""
    comparison = _get_comparison_for_view(request)

    if not comparison or comparison.products.count() == 0:
        return redirect('product_list')

    # Оптимизированное получение матрицы атрибутов
    attributes_matrix = comparison.attributes_matrix

    return render(request, 'compare/compare_detail.html', {
        'comparison': comparison,
        'attributes_matrix': attributes_matrix,
        'MAX_PRODUCTS': Comparison.MAX_PRODUCTS,
        'is_anonymous': not request.user.is_authenticated
    })


def clear_comparison(request):
    """Полная очистка сравнения"""
    comparison = _get_current_comparison(request)
    comparison.products.clear()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'redirect': reverse('product_list')})
    return redirect('compare:detail')
