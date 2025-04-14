from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from import_export.admin import ExportActionMixin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product_link', 'price', 'quantity', 'get_cost')
    readonly_fields = ('product_link', 'price', 'quantity', 'get_cost')
    extra = 0

    def product_link(self, obj):
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.id])
            return format_html('<a href="{}">{}</a>', url, obj.product_name())
        return obj.product_name()

    product_link.short_description = 'Товар'

    def get_cost(self, obj):
        return f"{obj.get_cost():.2f} ₽"

    get_cost.short_description = 'Стоимость'


@admin.register(Order)
class OrderAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'user_link',
        'status_badge',
        'created_at',
        'total_price',
        'payment_status',
        'actions'
    )
    list_filter = (
        'status',
        'paid',
        ('created_at', admin.DateFieldListFilter),
        ('total_price', admin.RangeFilter),
    )
    search_fields = (
        'id',
        'user__email',
        'email',
        'phone',
        'first_name',
        'last_name',
        'address'
    )
    inlines = [OrderItemInline]
    readonly_fields = ('created_at', 'updated_at', 'total_price')
    actions = ['mark_as_shipped', 'mark_as_canceled', 'mark_as_paid']
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'paid', 'created_at', 'updated_at')
        }),
        ('Контактные данные', {
            'fields': (
                ('first_name', 'last_name'),
                'email',
                'phone',
                'address'
            )
        }),
        ('Финансы', {
            'fields': ('total_price',),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:accounts_customuser_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return 'Гость'

    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__email'

    def status_badge(self, obj):
        colors = {
            'processing': 'orange',
            'shipped': 'blue',
            'delivered': 'green',
            'canceled': 'red'
        }
        return format_html(
            '<span style="background: {1}; color: white; padding: 3px 8px; border-radius: 4px">{0}</span>',
            obj.get_status_display(),
            colors.get(obj.status, '#999')
        )

    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'

    def payment_status(self, obj):
        if obj.paid:
            return format_html(
                '<span style="color: green;">✓ Оплачен</span>'
            )
        return format_html(
            '<span style="color: red;">× Не оплачен</span>'
        )

    payment_status.short_description = 'Оплата'

    def actions(self, obj):
        links = []
        if obj.status == 'processing':
            links.append(
                f'<a href="{obj.id}/cancel/">Отменить</a>'
            )
        if not obj.paid:
            links.append(
                f'<a href="{obj.id}/mark-paid/">Пометить оплаченным</a>'
            )
        return format_html(' | '.join(links))

    actions.short_description = 'Действия'

    # Custom Actions
    def mark_as_shipped(self, request, queryset):
        updated = queryset.filter(status='processing').update(status='shipped')
        self.message_user(request, f'{updated} заказов помечены как отправленные')

    mark_as_shipped.short_description = 'Пометить как отправленные'

    def mark_as_canceled(self, request, queryset):
        updated = queryset.exclude(status='canceled').update(status='canceled')
        self.message_user(request, f'{updated} заказов отменено')

    mark_as_canceled.short_description = 'Отменить выбранные заказы'

    def mark_as_paid(self, request, queryset):
        updated = queryset.update(paid=True)
        self.message_user(request, f'{updated} заказов помечены как оплаченные')

    mark_as_paid.short_description = 'Пометить как оплаченные'

    # Custom Views
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/cancel/', self.admin_site.admin_view(self.cancel_order)),
            path('<path:object_id>/mark-paid/', self.admin_site.admin_view(self.mark_order_paid))
        ]
        return custom_urls + urls

    def cancel_order(self, request, object_id):
        # Реализация отмены заказа
        pass

    def mark_order_paid(self, request, object_id):
        # Реализация отметки оплаты
        pass
