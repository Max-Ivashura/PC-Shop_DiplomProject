from django.contrib import admin
from django.contrib.admin import RelatedFieldListFilter
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Prefetch
from apps.products.models import Product, ProductImage, Review, ProductAttributeValue
import time


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
        'sku',
        'name',
        'category_hierarchy',
        'price',
        'stock_status',
        'is_available',
        'is_digital',
        'created_at'
    )
    list_filter = (
        'is_available',
        'is_digital',
        ('category', admin.RelatedOnlyFieldListFilter),
        'created_at'
    )
    search_fields = (
        'sku',
        'name',
        'description',
        'category__name'
    )
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    save_on_top = True
    list_select_related = ('category',)
    date_hierarchy = 'created_at'
    actions = ['update_attributes']
    autocomplete_fields = ['category']

    fieldsets = (
        (_("Основное"), {
            'fields': (
                'sku',
                'name',
                'slug',
                'category',
                'price',
                'description',
                'is_digital',
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
            Prefetch('images', queryset=ProductImage.objects.order_by('-is_main')),
            Prefetch('attributes', queryset=ProductAttributeValue.objects.select_related('attribute'))
        )

    def category_hierarchy(self, obj):
        return obj.category.path

    category_hierarchy.short_description = _("Путь категории")

    def stock_status(self, obj):
        if obj.quantity <= 0:
            return format_html('<span style="color: red;">{}</span>', _("Нет в наличии"))
        if obj.quantity < 10:
            return format_html(f'<span style="color: orange;">{obj.quantity} {_("шт.")}</span>')
        return format_html(f'<span style="color: green;">{obj.quantity} {_("шт.")}</span>')

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
        self.message_user(request, _("Атрибуты успешно обновлены"))

    update_attributes.short_description = _("Обновить атрибуты для выбранных товаров")

    def save_model(self, request, obj, form, change):
        if not obj.sku:
            obj.sku = f"PRD-{obj.category.id}-{int(time.time())}"
        super().save_model(request, obj, form, change)

    class Media:
        css = {'all': ('products/css/admin.css',)}
        js = ('products/js/admin.js',)


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0
    readonly_fields = ('attribute_type', 'validation_rules')
    fields = ('attribute', 'value', 'attribute_type', 'validation_rules')
    autocomplete_fields = ('attribute',)

    def attribute_type(self, obj):
        return obj.attribute.get_data_type_display()

    attribute_type.short_description = _("Тип атрибута")

    def validation_rules(self, obj):
        rules = []
        if obj.attribute.is_required:
            rules.append(_("Обязательный"))
        if obj.attribute.validation_regex:
            rules.append(_("Регулярка: ") + obj.attribute.validation_regex)
        return ", ".join(rules)

    validation_rules.short_description = _("Правила валидации")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating_stars', 'approved', 'created_at')
    list_filter = ('approved', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'text')
    list_editable = ('approved',)
    autocomplete_fields = ('product', 'user')
    date_hierarchy = 'created_at'
    list_select_related = ('product', 'user')

    def rating_stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)

    rating_stars.short_description = _("Рейтинг")


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'attribute', 'value_type', 'value_preview')
    list_filter = (
        'attribute__data_type',
        ('attribute__groups__category', RelatedFieldListFilter),
    )
    search_fields = ('product__name', 'attribute__name')
    autocomplete_fields = ('product', 'attribute')
    raw_id_fields = ('product',)

    def value_type(self, obj):
        return obj.attribute.get_data_type_display()

    value_type.short_description = _("Тип значения")

    def value_preview(self, obj):
        return str(obj.value)[:100]

    value_preview.short_description = _("Значение")
