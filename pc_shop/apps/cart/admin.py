from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.http import HttpResponse
import csv
from .models import Cart, CartItem

# Inline для элементов корзины
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0  # Убираем дополнительные пустые строки
    readonly_fields = ('get_product_price', 'get_total_cost')
    fields = ('product', 'quantity', 'get_product_price', 'get_total_cost')

    def get_product_price(self, obj):
        """Отображает цену товара."""
        return f"{obj.product.price} руб."
    get_product_price.short_description = "Цена товара"

    def get_total_cost(self, obj):
        """Отображает общую стоимость позиции."""
        return f"{obj.get_cost()} руб."
    get_total_cost.short_description = "Общая стоимость"

# Админка для корзины
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_or_session', 'created_at', 'total_items', 'total_price')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'session_key')
    inlines = [CartItemInline]
    readonly_fields = ('created_at',)
    actions = ['export_cart_data']

    def user_or_session(self, obj):
        """Отображает пользователя или ключ сессии."""
        return obj.user.username if obj.user else obj.session_key
    user_or_session.short_description = "Пользователь/Сессия"

    def total_items(self, obj):
        """Отображает общее количество товаров в корзине."""
        return obj.items.aggregate(total=Sum('quantity'))['total'] or 0
    total_items.short_description = "Товаров"

    def total_price(self, obj):
        """Отображает общую стоимость корзины."""
        return f"{obj.get_total_price()} руб."
    total_price.short_description = "Общая стоимость"

    def export_cart_data(self, request, queryset):
        """Экспорт данных корзины в CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cart_data.csv"'
        writer = csv.writer(response)
        writer.writerow(['Корзина ID', 'Пользователь/Сессия', 'Товар', 'Количество', 'Цена за единицу', 'Общая стоимость'])

        for cart in queryset:
            for item in cart.items.all():
                writer.writerow([
                    cart.id,
                    self.user_or_session(cart),
                    item.product.name,
                    item.quantity,
                    item.product.price,
                    item.get_cost()
                ])
        return response
    export_cart_data.short_description = "Экспортировать данные корзины"

# Админка для элементов корзины
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'get_product_price', 'get_total_cost')
    list_filter = ('cart__created_at', 'product__category')
    search_fields = ('product__name', 'cart__user__username', 'cart__session_key')
    readonly_fields = ('get_product_price', 'get_total_cost')

    def get_product_price(self, obj):
        """Отображает цену товара."""
        return f"{obj.product.price} руб."
    get_product_price.short_description = "Цена товара"

    def get_total_cost(self, obj):
        """Отображает общую стоимость позиции."""
        return f"{obj.get_cost()} руб."
    get_total_cost.short_description = "Общая стоимость"