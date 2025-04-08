from .forms import ProductAttributeForm
from .models import Product, ProductAttribute, ProductImage
from django.contrib import admin
from django.utils.html import format_html
from apps.catalog_config.models import Attribute


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('preview_thumbnail',)
    fields = ('image', 'preview_thumbnail', 'is_main')

    def preview_thumbnail(self, obj):
        return obj.preview_thumbnail()

    preview_thumbnail.short_description = "Превью"


class ProductAttributeInline(admin.TabularInline):
    form = ProductAttributeForm
    model = ProductAttribute
    extra = 0
    fields = ('attribute', 'data_type_display', 'value', 'unit_display',)
    readonly_fields = ('attribute', 'data_type_display', 'unit_display')

    class Media:
        css = {
            'all': ('admin/custom.css',)
        }
        js = ('admin/product_attributes.js',)

    def data_type_display(self, obj):
        return obj.attribute.get_data_type_display()

    data_type_display.short_description = 'Тип данных'

    def unit_display(self, obj):
        return obj.attribute.unit or '—'

    unit_display.short_description = 'Ед. измерения'

    def get_queryset(self, request):
        # Оптимизируем запросы
        return super().get_queryset(request).select_related('attribute__group')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Фильтруем характеристики по категории товара
        if db_field.name == "attribute" and hasattr(request, '_obj_'):
            kwargs["queryset"] = Attribute.objects.filter(
                group__category=request._obj_.category
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inline_instances(self, request, obj=None):
        # Группировка характеристик
        instances = super().get_inline_instances(request, obj)
        if obj and obj.category:
            setattr(self, 'grouped_attributes', self.get_grouped_attributes(obj))
        return instances


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
    fieldsets = (
        ('Основная информация', {
            'fields': ('main_image_preview', 'category', 'name', 'price',)
        }),
        ('Инвентаризация', {
            'fields': ('quantity', 'is_available')
        }),
        ('Контент', {
            'fields': ('description',)
        }),
        ('Метаданные', {
            'fields': ('slug', 'created_at', 'updated_at')
        }),
    )
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductAttributeInline]

    def main_image_preview(self, obj):
        main_image = obj.main_image
        if main_image:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px;" />',
                main_image.image.url
            )
        return "-"

    main_image_preview.short_description = "Главное изображение"

    def quantity_status(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color: red;">Нет в наличии</span>')
        elif obj.quantity < 10:
            return format_html(f'<span style="color: orange;">{obj.quantity} шт.</span>')
        return format_html(f'<span style="color: green;">{obj.quantity} шт.</span>')

    quantity_status.short_description = "Остаток"

    def get_form(self, request, obj=None, **kwargs):
        # Передаем объект товара в inline-формы
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product = form.instance
        # Создаем атрибуты только после сохранения продукта и выбора категории
        if product.category:
            attributes = Attribute.objects.filter(group__category=product.category)
            for attr in attributes:
                ProductAttribute.objects.get_or_create(
                    product=product,
                    attribute=attr,
                    defaults={'value': ''}
                )
