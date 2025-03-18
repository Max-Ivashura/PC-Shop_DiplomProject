import django_filters
from .models import Product, AttributeGroup, Attribute, ProductAttribute


class ProductFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['price_min', 'price_max']

    def __init__(self, *args, **kwargs):
        category = kwargs.pop('category', None)
        super().__init__(*args, **kwargs)

        # Динамически добавляем фильтры по характеристикам для текущей категории
        if category:
            # Получаем все группы характеристик для категории
            attribute_groups = AttributeGroup.objects.filter(category=category)
            for group in attribute_groups:
                # Для каждой группы добавляем фильтры по её характеристикам
                for attr in group.attributes.all():
                    # Используем MultipleChoiceFilter для чекбоксов
                    self.filters[f'attr_{attr.id}'] = django_filters.MultipleChoiceFilter(
                        field_name=f'attributes__value',
                        lookup_expr='icontains',
                        label=attr.name,
                        choices=ProductAttribute.objects.filter(attribute=attr).values_list('value', 'value').distinct()
                    )