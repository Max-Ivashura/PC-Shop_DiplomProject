import django_filters
from apps.products.models import Product, ProductAttribute
from apps.catalog_config.models import AttributeGroup
import django.forms


class ProductFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['price_min', 'price_max']

    def __init__(self, *args, **kwargs):
        category = kwargs.pop('category', None)
        super().__init__(*args, **kwargs)

        if category:
            # Динамически добавляем фильтры по характеристикам
            attribute_groups = AttributeGroup.objects.filter(category=category)
            for group in attribute_groups:
                for attr in group.attributes.all():
                    # Используем ModelMultipleChoiceFilter для чекбоксов
                    self.filters[f'attr_{attr.id}'] = django_filters.ModelMultipleChoiceFilter(
                        field_name='attributes__value',
                        to_field_name='value',
                        queryset=ProductAttribute.objects.filter(
                            attribute=attr
                        ).values_list('value', flat=True).distinct(),
                        label=attr.name,
                        widget=forms.CheckboxSelectMultiple
                    )