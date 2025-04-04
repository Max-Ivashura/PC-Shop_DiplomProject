from .filters import ProductFilter
from .models import Product
from django.db.models import Q
from django_filters.views import FilterView
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from catalog_config.models import Category


def product_search(request):
    query = request.GET.get('q')
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ) if query else Product.objects.none()
    return render(request, 'products/search_results.html', {'products': products, 'query': query})


class ProductListView(FilterView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 9
    filterset_class = ProductFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.kwargs.get('category_slug')
        sort = self.request.GET.get('sort', '').strip()

        queryset = queryset.prefetch_related('gallery')

        # Применяем сортировку
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')

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

        return queryset.distinct()  # Избегаем дубликатов

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['active_sort'] = self.request.GET.get('sort', 'default')  # Для визуального подтверждения
        return context

    # В представлении для нормализации параметров
    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)

        # Проверяем, есть ли данные в GET-запросе
        if 'data' in kwargs and kwargs['data'] is not None:
            data = kwargs['data'].copy()

            # Удаляем пустые параметры
            for key in list(data.keys()):
                if not data[key].strip():
                    del data[key]

            kwargs['data'] = data

        # Передаем категорию в фильтр
        kwargs['category'] = self.category
        return kwargs

    def get(self, request, *args, **kwargs):
        # Удаляем лишние пробелы из параметров
        if 'sort' in request.GET:
            request.GET = request.GET.copy()
            request.GET['sort'] = request.GET['sort'].strip()
        return super().get(request, *args, **kwargs)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'product_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем все изображения товара
        context['images'] = self.object.gallery.all()
        context['main_image'] = self.object.gallery.filter(is_main=True).first()

        # Если нет главного изображения - берем первое
        if not context['main_image'] and context['images']:
            context['main_image'] = context['images'].first()

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
