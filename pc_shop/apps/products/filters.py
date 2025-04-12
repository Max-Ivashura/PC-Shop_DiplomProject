import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from apps.products.models import Product
from apps.catalog_config.models import Attribute, Category


class ProductFilter(django_filters.FilterSet):
    sku = django_filters.CharFilter(
        field_name='sku',
        lookup_expr='iexact',
        label=_('Артикул (точное совпадение)')
    )

    price = django_filters.RangeFilter(
        field_name='price',
        label=_('Диапазон цен'),
        help_text=_('Мин. - Макс. значение')
    )

    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        method='filter_by_category_tree',
        label=_('Категория (с подкатегориями)')
    )

    is_digital = django_filters.BooleanFilter(
        field_name='is_digital',
        label=_('Только цифровые товары')
    )

    search = django_filters.CharFilter(
        method='custom_search',
        label=_('Поиск по названию/SKU/описанию')
    )

    class Meta:
        model = Product
        fields = ['sku', 'price', 'category', 'is_digital']

    def __init__(self, *args, **kwargs):
        # Удаляем получение категории из kwargs
        super().__init__(*args, **kwargs)
        self.add_dynamic_attribute_filters()

    def add_dynamic_attribute_filters(self):
        category_slug = self.data.get('category_slug')  # Получаем из GET-параметров
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
                attributes = category.get_all_attributes()

                for attr in attributes:
                    self.filters[f'attr_{attr.id}'] = self.create_attribute_filter(attr)

            except Category.DoesNotExist:
                pass

    def create_attribute_filter(self, attribute):
        """Создает фильтр для конкретного атрибута"""
        if attribute.data_type == 'enum':
            return django_filters.ModelMultipleChoiceFilter(
                field_name=f'attributes__attribute__id',
                queryset=attribute.enum_options.all(),
                label=attribute.name,
                method=f'filter_by_enum_attribute'
            )

        elif attribute.data_type == 'number':
            return django_filters.NumericRangeFilter(
                field_name=f'attributes__value',
                label=attribute.name,
                method=f'filter_by_numeric_attribute'
            )

        else:  # string/boolean
            return django_filters.CharFilter(
                field_name=f'attributes__value',
                lookup_expr='icontains',
                label=attribute.name,
                method=f'filter_by_generic_attribute'
            )

    def filter_by_category_tree(self, queryset, name, value):
        """Фильтрация по категории и ее подкатегориям"""
        return queryset.filter(
            category__in=value.get_descendants(include_self=True)
        )

    def custom_search(self, queryset, name, value):
        """Расширенный поиск с учетом SKU"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(sku__iexact=value) |
            Q(description__icontains=value)
        ).distinct()

    # Методы фильтрации атрибутов
    def filter_by_enum_attribute(self, queryset, name, value):
        attr_id = name.split('__')[0].replace('attr_', '')
        return queryset.filter(
            attributes__attribute__id=attr_id,
            attributes__value__in=value.values_list('value', flat=True)
        )

    def filter_by_numeric_attribute(self, queryset, name, value):
        attr_id = name.split('__')[0].replace('attr_', '')
        qs = queryset.filter(attributes__attribute__id=attr_id)

        if value.start and value.stop:
            return qs.filter(
                attributes__value__gte=value.start,
                attributes__value__lte=value.stop
            )
        return qs

    def filter_by_generic_attribute(self, queryset, name, value):
        attr_id = name.split('__')[0].replace('attr_', '')
        return queryset.filter(
            attributes__attribute__id=attr_id,
            attributes__value__icontains=value
        )
