from django.db import models
from django.conf import settings
from django.db.models import Sum, F, Q
from django.core.exceptions import ValidationError
from apps.products.models import Product
from apps.orders.models import Order


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Добавлено поле
    converted_order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_cart'
    )

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
            models.Index(fields=['created_at', 'updated_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name='user_or_session_required'
            )
        ]

    def __str__(self):
        return f"Cart #{self.id} ({self.user or 'Anonymous'})"

    def clean(self):
        if not self.user and not self.session_key:
            raise ValidationError("Cart must have either user or session key")

    def get_total_price(self):
        return self.items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or 0

    def add_product(self, product, quantity=1):
        """Добавление с проверкой доступности и резервированием"""
        if not product.is_available or product.quantity < quantity:
            raise ValidationError("Product not available in required quantity")

        item, created = self.items.get_or_create(
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            new_quantity = item.quantity + quantity
            if new_quantity > product.quantity:
                raise ValidationError("Exceeds available stock")
            item.quantity = new_quantity
            item.save()

        product.quantity -= quantity
        product.save(update_fields=['quantity'])

    def release_stock(self):
        """Освобождение резерва при отмене корзины"""
        for item in self.items.select_related('product'):
            item.product.quantity += item.quantity
            item.product.save(update_fields=['quantity'])
        self.items.all().delete()

    @property
    def is_active(self):
        """Не преобразована ли корзина в заказ"""
        return self.converted_order is None


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_product_in_cart'
            )
        ]
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_cost(self):
        return self.product.price * self.quantity

    def clean(self):
        if self.quantity > self.product.quantity:
            raise ValidationError("Quantity exceeds available stock")
