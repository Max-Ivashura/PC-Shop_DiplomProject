from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from apps.products.models import Product

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f"Корзина {self.user or self.session_key}"

    def get_total_price(self):
        # Используем аннотации для оптимизации запроса
        total = self.items.aggregate(total=Sum(F('quantity') * F('product__price')))['total']
        return total or 0

    def add_product(self, product, quantity=1):
        """Добавление товара в корзину."""
        cart_item, created = self.items.get_or_create(product=product, defaults={'quantity': quantity})
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

    def remove_product(self, product):
        """Удаление товара из корзины."""
        self.items.filter(product=product).delete()

    def update_quantity(self, product, quantity):
        """Обновление количества товара."""
        cart_item = self.items.filter(product=product).first()
        if cart_item:
            cart_item.quantity = quantity
            cart_item.save()

    def clear(self):
        """Очистка корзины."""
        self.items.all().delete()

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_cost(self):
        return self.product.price * self.quantity