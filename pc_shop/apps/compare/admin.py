from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from apps.compare.models import Comparison, ComparisonItem
from apps.catalog_config.models import Category


class CategoryFilter(admin.SimpleListFilter):
    title = 'Категория'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return Category.objects.all().values_list('id', 'name')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category__id=self.value())
        return queryset


class ComparisonItemInline(admin.TabularInline):
    model = ComparisonItem
    extra = 0
    readonly_fields = ('added_at', 'product_category')
    raw_id_fields = ('product',)

    def product_category(self, obj):
        return obj.product.category.name if obj.product.category else '-'

    product_category.short_description = 'Категория товара'


@admin.register(Comparison)
class ComparisonAdmin(admin.ModelAdmin):
    list_display = ('user_or_session', 'category', 'product_count', 'created_at_formatted', 'is_active')
    list_filter = (CategoryFilter, 'created_at', 'category')
    search_fields = (
        'user__username',
        'session_key',
        'products__name',
        'category__name'
    )
    date_hierarchy = 'created_at'
    inlines = [ComparisonItemInline]
    readonly_fields = ('created_at', 'session_key', 'attributes_preview')
    raw_id_fields = ('user', 'category')
    actions = ['delete_old_comparisons', 'export_as_csv']

    fieldsets = (
        (None, {
            'fields': ('user', 'session_key', 'category')
        }),
        ('Дополнительно', {
            'fields': ('created_at', 'attributes_preview'),
            'classes': ('collapse',)
        }),
    )

    def user_or_session(self, obj):
        return obj.user.username if obj.user else f"Session: {obj.session_key}"

    user_or_session.short_description = "Идентификатор"

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Товары"

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    created_at_formatted.short_description = "Дата создания"

    def is_active(self, obj):
        return obj.products.exists()

    is_active.boolean = True
    is_active.short_description = "Активно"

    def attributes_preview(self, obj):
        return format_html("<br>".join(
            f"{group}: {attrs}"
            for group, attrs in obj.attributes_matrix.items()
        ))

    attributes_preview.short_description = "Превью атрибутов"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'products',
            'category'
        ).select_related('user')

    @admin.action(description="Удалить сравнения старше 7 дней")
    def delete_old_comparisons(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta

        old_comparisons = queryset.filter(
            created_at__lt=timezone.now() - timedelta(days=7)
        )
        count = old_comparisons.count()
        old_comparisons.delete()
        self.message_user(request, f"Удалено {count} старых сравнений")

    @admin.action(description="Экспорт в CSV")
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="comparisons.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'User/Session',
            'Category',
            'Products Count',
            'Created At',
            'Attributes'
        ])

        for obj in queryset:
            writer.writerow([
                obj.user.username if obj.user else obj.session_key,
                obj.category.name if obj.category else '-',
                obj.products.count(),
                obj.created_at.strftime("%Y-%m-%d %H:%M"),
                "\n".join(f"{k}: {v}" for k, v in obj.attributes_matrix.items())
            ])

        return response


@admin.register(ComparisonItem)
class ComparisonItemAdmin(admin.ModelAdmin):
    list_display = ('comparison_info', 'product_link', 'category', 'added_at')
    list_filter = ('product__category',)
    raw_id_fields = ('comparison', 'product')
    search_fields = (
        'comparison__user__username',
        'comparison__session_key',
        'product__name'
    )

    def comparison_info(self, obj):
        return f"Сравнение #{obj.comparison.id}"

    comparison_info.short_description = "Сравнение"

    def product_link(self, obj):
        return format_html('<a href="{}">{}</a>',
                           reverse('admin:products_product_change', args=[obj.product.id]),
                           obj.product.name
                           )

    product_link.short_description = "Товар"

    def category(self, obj):
        return obj.product.category.name if obj.product.category else '-'

    category.short_description = "Категория"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'comparison__user',
            'product__category'
        )
