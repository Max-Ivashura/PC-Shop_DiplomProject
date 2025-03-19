from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from products.models import Product
from django.http import JsonResponse

@login_required
def add_to_comparison(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    comparison, created = request.user.comparisons.get_or_create()
    comparison.products.add(product)
    return redirect('product_detail', product_slug=product.slug)

def remove_from_comparison(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    comparison = request.user.comparisons.first()
    if comparison:
        comparison.products.remove(product)
    return redirect('compare_view')


@login_required
def compare_view(request):
    comparison = request.user.comparisons.first()
    products = comparison.products.all() if comparison else []

    # Группировка характеристик
    grouped_attributes = {}
    for product in products:
        for pa in product.attributes.select_related('attribute__group').all():
            group_name = pa.attribute.group.name
            attr_name = pa.attribute.name
            if group_name not in grouped_attributes:
                grouped_attributes[group_name] = {}
            if attr_name not in grouped_attributes[group_name]:
                grouped_attributes[group_name][attr_name] = {}
            grouped_attributes[group_name][attr_name][product.id] = pa.value

    return render(request, 'compare/compare.html', {
        'products': products,
        'grouped_attributes': grouped_attributes
    })