from django.views.generic import ListView, DetailView
from django.db.models import Prefetch, Q, F, Count
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.utils.translation import gettext_lazy as _
from django_filters.views import FilterView
from apps.products.models import Product, ProductImage, Review
from apps.products.filters import ProductFilter
from apps.catalog_config.models import Category, Attribute
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Review


class ProductListView(FilterView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 24
    filterset_class = ProductFilter
    strict = False

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.get_current_category()

        if category:
            queryset = queryset.filter(
                category__in=category.get_descendants(include_self=True)
            )

        return queryset

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        # Удаляем передачу категории в фильтр
        return kwargs

    def get_current_category(self):
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            return get_object_or_404(Category, slug=category_slug)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'category': self.get_current_category(),
            'sort_options': self.get_sort_options(),
            'result_count': self.get_queryset().count(),
            'category_tree': self.get_cached_category_tree()
        })
        return context

    def get_sort_options(self):
        return [
            {'key': 'default', 'label': _('По умолчанию')},
            {'key': 'price_asc', 'label': _('Цена ↑')},
            {'key': 'price_desc', 'label': _('Цена ↓')},
            {'key': 'newest', 'label': _('Новинки')},
            {'key': 'top_rated', 'label': _('Рейтинг')}
        ]

    def get_cached_category_tree(self):
        cache_key = 'category_tree'
        category_tree = cache.get(cache_key)
        if not category_tree:
            category_tree = Category.objects.filter(level=0).get_descendants(
                include_self=True).annotate(product_count=Count('products'))
            cache.set(cache_key, category_tree, 3600)
        return category_tree

    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'product_slug'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'category'
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('-is_main')),
            Prefetch('attributes__attribute__groups'),  # Используйте Prefetch для groups
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Загружаем отзывы после получения продукта
        reviews = Review.objects.filter(
            approved=True,
            product=product
        ).select_related('user')

        context.update({
            'grouped_attributes': self.get_grouped_attributes(product),
            'related_products': self.get_related_products(product),
            'sku': product.sku,
            'is_digital': product.is_digital,
            'reviews': reviews,  # Передаем отзывы в контекст
        })
        return context

    def get_grouped_attributes(self, product):
        # Замените select_related на prefetch_related для ManyToMany-связи
        attributes = product.attributes.select_related('attribute').prefetch_related(
            'attribute__groups',  # Если groups — ManyToManyField
            'attribute__enum_options'
        )

        grouped = {}
        for attr in attributes:
            # Используйте attribute.groups.all() для доступа к группам
            for group in attr.attribute.groups.all():
                grouped.setdefault(group, []).append(attr)
        return sorted(grouped.items(), key=lambda x: x[0].name)

    def get_related_products(self, product):
        return Product.objects.filter(
            category=product.category
        ).exclude(id=product.id).order_by('?')[:4]


class SearchView(ListView):
    model = Product
    template_name = 'products/search_results.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            return Product.objects.filter(
                Q(name__icontains=query) |
                Q(sku__iexact=query) |
                Q(description__icontains=query)
            ).distinct().select_related('category').prefetch_related('images')
        return Product.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['result_count'] = self.get_queryset().count()
        return context


class AddReviewView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = Product.objects.get(id=product_id)
        text = request.POST.get('text')
        rating = request.POST.get('rating')

        # Создаем отзыв
        review = Review.objects.create(
            user=request.user,
            product=product,
            text=text,
            rating=rating,
            approved=False  # Модерация включена
        )

        return JsonResponse({
            'success': True,
            'message': 'Отзыв отправлен на модерацию.'
        })
