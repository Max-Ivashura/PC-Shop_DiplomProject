from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from .models import Product, Category

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 9  # Постраничный вывод (9 товаров на страницу)

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            # Фильтрация по категории (пока базовая, позже добавим сложные фильтры)
            return Product.objects.filter(category__slug=category_slug)
        return Product.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = Category.objects.filter(slug=self.kwargs.get('category_slug')).first()
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'product_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Группировка характеристик по группам
        attributes = self.object.attributes.all()
        grouped_attributes = {}
        for attr in attributes:
            group_name = attr.attribute.group.name
            if group_name not in grouped_attributes:
                grouped_attributes[group_name] = []
            grouped_attributes[group_name].append(attr)
        context['grouped_attributes'] = grouped_attributes.items()
        return context