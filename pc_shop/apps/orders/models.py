from django.db import models
from django.conf import settings
from django.db.models import Sum, F, Q
from django.core.exceptions import ValidationError
from django.urls import reverse
from apps.products.models import Product

STATUS_CHOICES = [
    ('processing', 'В обработке'),
    ('shipped', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
]


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Пользователь",
        related_name='orders'
    )
    first_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    email = models.EmailField("Email", db_index=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)  # Добавлено
    address = models.CharField("Адрес", max_length=250, db_index=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        db_index=True
    )
    paid = models.BooleanField("Оплачен", default=False, db_index=True)
    total_price = models.DecimalField(  # Добавлено
        "Итоговая сумма",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'paid']),
        ]
        constraints = [  # Добавлено
            models.CheckConstraint(
                check=Q(status__in=dict(STATUS_CHOICES).keys()),
                name='valid_order_status'
            )
        ]

    def __str__(self):
        return f"Заказ {self.id} ({self.get_status_display()})"

    def clean(self):  # Добавлено
        super().clean()
        allowed_transitions = {
            'processing': ['shipped', 'canceled'],
            'shipped': ['delivered', 'canceled'],
            'delivered': [],
            'canceled': [],
        }

        if self.pk:
            old_status = Order.objects.get(pk=self.pk).status
            if self.status not in allowed_transitions[old_status]:
                raise ValidationError(
                    f"Недопустимый переход статуса из {old_status} в {self.status}"
                )

    def save(self, *args, **kwargs):  # Обновлено
        if not self.pk:
            self.total_price = self.calculate_total_cost()
        super().save(*args, **kwargs)

    def calculate_total_cost(self):
        return self.items.aggregate(
            total=Sum(F('price') * F('quantity'))
        )['total'] or 0

    def get_absolute_url(self):  # Добавлено
        return reverse('orders:order_detail', kwargs={'pk': self.pk})

    def update_status(self, new_status):
        self.status = new_status
        self.save(update_fields=['status'])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Заказ"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Товар"
    )
    name_snapshot = models.CharField("Название товара", max_length=255, blank=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("Количество", default=1)

    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'
        indexes = [
            models.Index(fields=['order', 'product']),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_name()}"

    def product_name(self):
        return self.product.name if self.product else self.name_snapshot

    def get_cost(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        if not self.pk and self.product:
            self.name_snapshot = self.product.name
            self.price = self.product.price  # Актуальная цена на момент заказа

        super().save(*args, **kwargs)
        if self.order_id:  # Обновление итоговой суммы заказа
            self.order.total_price = self.order.calculate_total_cost()
            self.order.save(update_fields=['total_price'])
