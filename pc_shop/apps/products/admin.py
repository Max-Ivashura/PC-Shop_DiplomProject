# admin.py
from django.contrib import admin
from django.contrib.admin import RelatedFieldListFilter
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import OuterRef, Subquery, Prefetch
from .models import Product, ProductImage, Review
from apps.catalog_config.models import ProductAttributeValue, Attribute


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ('preview',)
    fields = ('image', 'preview', 'is_main')
    ordering = ('-is_main', 'id')

    def preview(self, obj):
        return obj.preview_thumbnail()

    preview.short_description = _("Миниатюра")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'main_image_preview',
        'category_hierarchy',
        'price',
        'stock_status',
        'is_available',
        'created_at'
    )
    list_filter = (
        'is_available',
        ('category', admin.RelatedOnlyFieldListFilter),
        'created_at'
    )
    search_fields = (
        'name',
        'description',
        'category__name',
        'category__path'
    )
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    save_on_top = True
    list_select_related = ('category',)
    date_hierarchy = 'created_at'
    actions = ['update_attributes']

    fieldsets = (
        (_("Основное"), {
            'fields': (
                'name',
                'slug',
                'category',
                'price',
                'description',
                'main_image_preview'
            )
        }),
        (_("Инвентаризация"), {
            'fields': ('quantity', 'is_available'),
        }),
        (_("SEO"), {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('-is_main'))
        )

    def category_hierarchy(self, obj):
        return obj.category.path

    category_hierarchy.short_description = _("Путь категории")

    def stock_status(self, obj):
        if obj.quantity <= 0:
            return format_html('<span style="color: red;">Нет в наличии</span>')
        if obj.quantity < 10:
            return format_html(f'<span style="color: orange;">{obj.quantity} шт.</span>')
        return format_html(f'<span style="color: green;">{obj.quantity} шт.</span>')

    stock_status.short_description = _("Остаток")

    def main_image_preview(self, obj):
        return obj.main_image.preview_thumbnail() if obj.main_image else '-'

    main_image_preview.short_description = _("Главное изображение")

    def update_attributes(self, request, queryset):
        for product in queryset:
            attributes = product.category.get_all_attributes()
            for attr in attributes:
                ProductAttributeValue.objects.get_or_create(
                    product=product,
                    attribute=attr,
                    defaults={'value': attr.default_value()}
                )

    update_attributes.short_description = _("Обновить атрибуты для выбранных товаров")

    class Media:
        css = {'all': ('products/css/admin.css',)}
        js = ('products/js/admin.js',)


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0
    readonly_fields = ('attribute_type',)
    fields = ('attribute', 'value', 'attribute_type')
    autocomplete_fields = ('attribute',)
    show_change_link = True

    def attribute_type(self, obj):
        return obj.attribute.get_data_type_display()

    attribute_type.short_description = _("Тип атрибута")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('attribute')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating_stars', 'approved', 'created_at')
    list_filter = ('approved', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'text')
    list_editable = ('approved',)
    autocomplete_fields = ('product', 'user')
    date_hierarchy = 'created_at'

    def rating_stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)

    rating_stars.short_description = _("Рейтинг")


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'attribute', 'value_type', 'value_preview')
    list_filter = (
        'attribute__data_type',  # Фильтр по типу атрибута
        ('attribute__groups__category', RelatedFieldListFilter),  # Исправленный фильтр
    )
    search_fields = ('product__name', 'attribute__name')
    autocomplete_fields = ('product', 'attribute')

    def value_type(self, obj):
        return obj.attribute.get_data_type_display()

    value_type.short_description = _("Тип значения")

    def value_preview(self, obj):
        if obj.attribute.data_type == 'enum':
            return obj.value
        return str(obj.value)

    value_preview.short_description = _("Значение")