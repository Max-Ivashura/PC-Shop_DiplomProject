from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Product, ProductImage, Review
from apps.catalog_config.models import ProductAttributeValue


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('preview_thumbnail',)
    fields = ('image', 'preview_thumbnail', 'is_main')

    def preview_thumbnail(self, obj):
        return obj.preview_thumbnail()

    preview_thumbnail.short_description = "Превью"


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0
    fields = ('attribute', 'value_display', 'value_input')
    readonly_fields = ('attribute', 'value_display')
    can_delete = False

    class Media:
        css = {'all': ('products/css/admin.css',)}
        js = ('products/js/admin.js',)

    def value_display(self, obj):
        return obj.get_value()

    value_display.short_description = _('Текущее значение')

    def value_input(self, obj):
        attr = obj.attribute
        value = obj.get_value()

        if attr.data_type == 'string':
            return f'<input type="text" name="value_{obj.id}" value="{value}" />'
        elif attr.data_type == 'number':
            return f'<input type="number" name="value_{obj.id}" value="{value}" />'
        elif attr.data_type == 'boolean':
            checked = 'checked' if value else ''
            return f'<input type="checkbox" name="value_{obj.id}" {checked} />'
        elif attr.data_type == 'enum':
            options = ''.join(
                f'<option value="{opt}" {"selected" if opt == value else ""}>{opt}</option>'
                for opt in attr.enum_options
            )
            return f'<select name="value_{obj.id}">{options}</select>'
        return '-'

    value_input.short_description = _('Изменить значение')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('attribute')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'main_image_preview',
        'name',
        'category',
        'price',
        'quantity_status',
        'is_available',
        'created_at'
    )
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    readonly_fields = ('main_image_preview', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductAttributeValueInline]
    save_on_top = True

    fieldsets = (
        (_('Основная информация'), {
            'fields': ('main_image_preview', 'category', 'name', 'slug', 'price')
        }),
        (_('Инвентаризация'), {
            'fields': ('quantity', 'is_available')
        }),
        (_('Контент'), {
            'fields': ('description',)
        }),
        (_('Метаданные'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def main_image_preview(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px;" />',
                obj.main_image.image.url
            )
        return "-"

    main_image_preview.short_description = _("Главное изображение")

    def quantity_status(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color: red;">Нет в наличии</span>')
        elif obj.quantity < 10:
            return format_html(f'<span style="color: orange;">{obj.quantity} шт.</span>')
        return format_html(f'<span style="color: green;">{obj.quantity} шт.</span>')

    quantity_status.short_description = _("Остаток")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product = form.instance
        if product.category:
            attributes = product.category.get_all_attributes()
            for attr in attributes:
                ProductAttributeValue.objects.get_or_create(
                    product=product,
                    attribute=attr,
                    defaults={
                        'value_string': '' if attr.data_type == 'string' else None,
                        'value_number': None,
                        'value_boolean': None,
                        'value_enum': attr.enum_options[0] if attr.enum_options else None
                    }
                )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if '_continue' in request.POST:
            self._update_attribute_values(request, obj)

    def _update_attribute_values(self, request, product):
        pattern = re.compile(r'value_(\d+)')
        for key, value in request.POST.items():
            match = pattern.match(key)
            if match:
                attr_value_id = match.group(1)
                try:
                    attr_value = ProductAttributeValue.objects.get(
                        id=attr_value_id,
                        product=product
                    )
                    attr = attr_value.attribute
                    if attr.data_type == 'string':
                        attr_value.value_string = value
                    elif attr.data_type == 'number':
                        attr_value.value_number = value
                    elif attr.data_type == 'boolean':
                        attr_value.value_boolean = value == 'on'
                    elif attr.data_type == 'enum':
                        attr_value.value_enum = value
                    attr_value.save()
                except ProductAttributeValue.DoesNotExist:
                    pass


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'text')
    readonly_fields = ('user', 'product', 'created_at')

    def has_add_permission(self, request):
        return False