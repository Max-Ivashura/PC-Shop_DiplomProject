# views.py
from collections import defaultdict

from django.views.generic import ListView, DetailView
from django.db.models import Prefetch, Q, F, Count
from django.shortcuts import get_object_or_404
from django.core.cache.utils import make_template_fragment_key
from django.core.cache import cache
from django_filters.views import FilterView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from apps.products.models import Product, ProductImage
from apps.catalog_config.models import Attribute, Category, ProductAttributeValue
from .filters import ProductFilter  # Создайте этот файл для фильтров
from django.db import models

class ProductListView(FilterView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 24
    filterset_class = ProductFilter
    strict = False

    def get_queryset(self):
        # Базовый queryset с оптимизациями
        queryset = super().get_queryset().select_related(
            'category'  # Для быстрого доступа к категории
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('-is_main')),
            'attributes__attribute__enum_options'  # Для характеристик
        )

        # Обработка фильтрации по категории
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            # Получаем категорию из БД
            self.category = get_object_or_404(Category, slug=category_slug)

            # Фильтруем товары по текущей категории и всем вложенным
            queryset = queryset.filter(
                category__in=self.category.get_descendants(include_self=True)
            )

        # Применение сортировки
        sort = self.request.GET.get('sort', '').strip()
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'top_rated':
            queryset = queryset.annotate(
                avg_rating=models.Avg('reviews__rating')
            ).order_by('-avg_rating')

        # Поиск по названию/описанию
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Категория и фильтры
        context['category'] = getattr(self, 'category', None)
        context['active_filters'] = self.request.GET.dict()

        # 2. Кэширование структуры категорий
        cache_key = make_template_fragment_key('category_tree')
        category_tree = cache.get(cache_key)
        if not category_tree:
            category_tree = Category.objects.filter(
                level=0
            ).get_descendants(include_self=True).annotate(
                product_count=Count('products')
            )
            cache.set(cache_key, category_tree, 3600)
        context['category_tree'] = category_tree

        # 3. Группировка атрибутов для фильтров
        if context['category']:
            attributes = Attribute.objects.filter(
                groups__category=context['category']
            ).prefetch_related('enum_options').distinct()

            grouped_attributes = defaultdict(list)
            for attr in attributes:
                grouped_attributes[attr.group].append(attr)
            context['grouped_attributes'] = dict(grouped_attributes)

        # 4. Параметры сортировки
        context['sort_options'] = [
            ('default', 'По умолчанию'),
            ('price_asc', 'Цена ↑'),
            ('price_desc', 'Цена ↓'),
            ('newest', 'Новинки'),
            ('top_rated', 'Рейтинг')
        ]

        # 5. Подсчет количества результатов
        context['result_count'] = self.get_queryset().count()

        return context

    @method_decorator(cache_page(60 * 15))  # Кэшируем на 15 минут
    @method_decorator(vary_on_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'product_slug'
    queryset = Product.objects.select_related(
        'category'
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('-is_main')),
        'attributes__attribute__groups',
        'reviews'
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Оптимизированная группировка атрибутов
        attributes = self.object.attributes.select_related(
            'attribute__groups'
        ).prefetch_related('attribute__enum_options')

        grouped_attributes = {}
        for attr in attributes:
            for group in attr.attribute.groups.all():
                grouped_attributes.setdefault(group, []).append(attr)

        context['grouped_attributes'] = sorted(
            grouped_attributes.items(),
            key=lambda x: x[0].name
        )

        # Рекомендации
        context['related_products'] = Product.objects.filter(
            category=self.object.category
        ).exclude(
            id=self.object.id
        ).order_by('?')[:4]

        return context


class SearchView(ListView):
    model = Product
    template_name = 'products/search_results.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Product.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(attributes__value__icontains=query)
            ).distinct().select_related('category').prefetch_related('images')
        return Product.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['result_count'] = self.get_queryset().count()
        return context