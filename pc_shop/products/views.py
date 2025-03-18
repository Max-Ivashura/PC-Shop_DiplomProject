from .filters import ProductFilter
from .models import Product, Category
from django.db.models import Q
from django_filters.views import FilterView
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView


class ProductListView(FilterView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 9
    filterset_class = ProductFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.kwargs.get('category_slug')

        # Фильтрация по категории
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
            self.category = get_object_or_404(Category, slug=category_slug)
        else:
            self.category = None

        # Поиск по названию и описанию
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs['category'] = self.category  # Передаем категорию в фильтр
        return kwargs

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