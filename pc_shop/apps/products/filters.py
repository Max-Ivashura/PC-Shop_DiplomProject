import django_filters
from apps.products.models import Product
from apps.catalog_config.models import Attribute

class ProductFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    attributes = django_filters.ModelMultipleChoiceFilter(
        field_name='attributes__attribute',
        queryset=Attribute.objects.all(),
        label='Характеристики'
    )

    class Meta:
        model = Product
        fields = ['price_min', 'price_max', 'attributes']