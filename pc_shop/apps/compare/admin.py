from django.contrib import admin
from django.utils.html import format_html
from .models import Comparison, ComparisonItem


class ComparisonItemInline(admin.TabularInline):
    model = ComparisonItem
    extra = 0
    readonly_fields = ('added_at',)
    raw_id_fields = ('product',)  # Для удобства выбора товаров


@admin.register(Comparison)
class ComparisonAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_count', 'created_at_formatted')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'products__name')
    date_hierarchy = 'created_at'
    inlines = [ComparisonItemInline]
    readonly_fields = ('created_at',)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Количество товаров"

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    created_at_formatted.short_description = "Дата создания"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('products')


@admin.register(ComparisonItem)
class ComparisonItemAdmin(admin.ModelAdmin):
    list_display = ('comparison_user', 'product', 'added_at')
    list_filter = ('comparison__user',)
    raw_id_fields = ('comparison', 'product')

    def comparison_user(self, obj):
        return obj.comparison.user.username

    comparison_user.short_description = "Пользователь"