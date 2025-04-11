from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from apps.products.models import Product

class Order(models.Model):
    STATUS_CHOICES = [
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('canceled', 'Отменен'),
    ]

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
    email = models.EmailField("Email")
    address = models.CharField("Адрес", max_length=250)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        db_index=True  # Для ускорения фильтрации по статусу
    )
    paid = models.BooleanField("Оплачен", default=False, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'paid']),
        ]

    def __str__(self):
        return f"Заказ {self.id} ({self.get_status_display()})"

    def get_total_cost(self):
        # Оптимизация через агрегацию
        return self.items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0

    def update_status(self, new_status):
        # Безопасное изменение статуса с проверкой
        allowed_transitions = {
            'processing': ['shipped', 'canceled'],
            'shipped': ['delivered', 'canceled'],
            'delivered': [],
            'canceled': [],
        }
        if new_status in allowed_transitions.get(self.status, []):
            self.status = new_status
            self.save()
            return True
        return False

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Заказ"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,  # Сохраняем товар даже если он удален
        null=True,
        verbose_name="Товар"
    )
    name_snapshot = models.CharField("Название товара", max_length=255, blank=True)  # Снапшот названия
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
        # Сохраняем снапшот названия при создании
        if not self.pk and self.product:
            self.name_snapshot = self.product.name
        super().save(*args, **kwargs)