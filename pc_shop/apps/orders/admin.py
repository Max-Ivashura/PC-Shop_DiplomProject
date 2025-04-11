from django.contrib import admin
from django.utils.html import format_html
from apps.orders.models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product_name', 'price', 'quantity', 'get_cost')
    can_delete = False
    extra = 0

    def product_name(self, obj):
        return obj.product.name if obj.product else obj.name_snapshot
    product_name.short_description = 'Товар'

    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = 'Стоимость'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_info',
        'status_colored',
        'created_at',
        'total_cost',
        'paid',
        'payment_actions'
    )
    list_filter = (
        'status',
        'paid',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'id',
        'user__email',
        'email',
        'first_name',
        'last_name',
    )
    inlines = [OrderItemInline]
    readonly_fields = ('created_at', 'updated_at', 'get_total_cost')
    list_editable = ('status',)
    actions = ['mark_as_shipped', 'mark_as_canceled']
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'paid', 'created_at', 'updated_at')
        }),
        ('Данные покупателя', {
            'fields': ('first_name', 'last_name', 'email', 'address')
        }),
        ('Финансы', {
            'fields': ('get_total_cost',)
        })
    )

    def user_info(self, obj):
        if obj.user:
            return format_html(
                '<a href="?user__id__exact={}">{}</a>',
                obj.user.id,
                obj.user.email
            )
        return 'Гость'
    user_info.short_description = 'Пользователь'

    def status_colored(self, obj):
        color = {
            'processing': 'orange',
            'shipped': 'blue',
            'delivered': 'green',
            'canceled': 'red'
        }.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Статус'

    def total_cost(self, obj):
        return obj.get_total_cost()
    total_cost.short_description = 'Итого'

    def mark_as_shipped(self, request, queryset):
        updated = queryset.filter(status='processing').update(status='shipped')
        self.message_user(request, f'Заказов обновлено: {updated}')
    mark_as_shipped.short_description = 'Пометить как отправленные'

    def mark_as_canceled(self, request, queryset):
        updated = queryset.exclude(status='canceled').update(status='canceled')
        self.message_user(request, f'Заказов отменено: {updated}')
    mark_as_canceled.short_description = 'Отменить заказы'

    def payment_actions(self, obj):
        if obj.paid:
            return format_html('<span style="color:green;">Оплачен</span>')
        return format_html(
            '<a href="#" class="button">Оплатить</a>',
            obj.id
        )
    payment_actions.short_description = 'Оплата'