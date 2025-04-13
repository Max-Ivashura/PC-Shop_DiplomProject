from django.contrib import admin
from django.db.models import Sum, F
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
import csv
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'added_at', 'get_cost')
    fields = ('product', 'quantity', 'added_at', 'get_cost')
    show_change_link = True

    def get_cost(self, obj):
        return f"{obj.get_cost()} ₽"

    get_cost.short_description = "Стоимость"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_or_session',
        'status_badge',
        'created_at',
        'updated_at',
        'total_items',
        'total_price',
        'converted_order_link'
    )
    list_filter = (
        'created_at',
        'updated_at',
        'converted_order__status',
    )
    search_fields = (
        'user__email',
        'user__phone',
        'session_key',
        'converted_order__id'
    )
    inlines = [CartItemInline]
    readonly_fields = (
        'created_at',
        'updated_at',
        'converted_order',
        'status_badge'
    )
    actions = [
        'export_carts_csv',
        'release_stock_action',
    ]
    autocomplete_fields = ['user']

    def user_or_session(self, obj):
        if obj.user:
            return f"👤 {obj.user.email}"
        return f"🔑 {obj.session_key}"

    user_or_session.short_description = "Владелец"

    def status_badge(self, obj):
        if obj.converted_order:
            color = 'green' if obj.converted_order.status == 'delivered' else 'grey'
            return format_html(
                '<span style="color: white; background: {}; padding: 3px 8px; border-radius: 5px">{}</span>',
                color,
                obj.converted_order.get_status_display()
            )
        return format_html('<span style="color: green">🛒 Активна</span>')

    status_badge.short_description = "Статус"

    def converted_order_link(self, obj):
        if obj.converted_order:
            url = reverse('admin:orders_order_change', args=[obj.converted_order.id])
            return format_html('<a href="{}">Заказ #{}</a>', url, obj.converted_order.id)
        return "-"

    converted_order_link.short_description = "Связанный заказ"

    def total_items(self, obj):
        return obj.items.aggregate(total=Sum('quantity'))['total'] or 0

    total_items.short_description = "Товаров"

    def total_price(self, obj):
        return f"{obj.get_total_price()} ₽"

    total_price.short_description = "Общая сумма"

    def release_stock_action(self, request, queryset):
        for cart in queryset:
            cart.release_stock()
        self.message_user(request, f"Освобождено резервов: {queryset.count()}")

    release_stock_action.short_description = "❗ Освободить резерв товаров"

    def export_carts_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="carts_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID корзины',
            'Владелец',
            'Статус',
            'Товаров',
            'Сумма',
            'Дата создания',
            'Последнее обновление',
            'Связанный заказ'
        ])

        for cart in queryset.prefetch_related('items', 'converted_order'):
            writer.writerow([
                cart.id,
                cart.user.email if cart.user else cart.session_key,
                'Завершена' if cart.converted_order else 'Активна',
                cart.total_items,
                cart.get_total_price(),
                cart.created_at.strftime("%d.%m.%Y %H:%M"),
                cart.updated_at.strftime("%d.%m.%Y %H:%M") if cart.updated_at else '-',
                cart.converted_order.id if cart.converted_order else '-'
            ])

        return response

    export_carts_csv.short_description = "📤 Экспорт в CSV"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        'product_link',
        'cart_link',
        'quantity',
        'added_at',
        'get_cost'
    )
    list_filter = ('added_at', 'product__category')
    search_fields = (
        'product__name',
        'cart__user__email',
        'cart__session_key'
    )
    readonly_fields = ('added_at',)
    autocomplete_fields = ['product', 'cart']

    def product_link(self, obj):
        url = reverse('admin:products_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)

    product_link.short_description = "Товар"

    def cart_link(self, obj):
        url = reverse('admin:cart_cart_change', args=[obj.cart.id])
        return format_html('<a href="{}">Корзина #{}</a>', url, obj.cart.id)

    cart_link.short_description = "Корзина"

    def get_cost(self, obj):
        return f"{obj.get_cost()} ₽"

    get_cost.short_description = "Стоимость"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product',
            'cart',
            'cart__user'
        )
