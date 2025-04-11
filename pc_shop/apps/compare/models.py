from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.products.models import Product


class Comparison(models.Model):
    MAX_PRODUCTS = 4  # Максимальное количество товаров для сравнения

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='comparisons',
        verbose_name="Пользователь"
    )
    products = models.ManyToManyField(
        Product,
        through='ComparisonItem',
        related_name='comparisons'
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Сравнение"
        verbose_name_plural = "Сравнения"
        ordering = ['-created_at']

    def __str__(self):
        return f"Сравнение {self.user.username} ({self.products.count()} товаров)"

    def clean(self):
        if self.products.count() > self.MAX_PRODUCTS:
            raise ValidationError(f"Можно сравнивать не более {self.MAX_PRODUCTS} товаров")

    def add_product(self, product):
        """Безопасное добавление товара с проверкой лимита"""
        if self.products.count() >= self.MAX_PRODUCTS:
            raise ValidationError(f"Достигнут лимит в {self.MAX_PRODUCTS} товаров")
        if product not in self.products.all():
            self.products.add(product)
            self.save()

    def remove_product(self, product):
        """Удаление товара из сравнения"""
        if product in self.products.all():
            self.products.remove(product)
            if self.products.count() == 0:
                self.delete()  # Автоудаление пустого сравнения

    @property
    def attributes_matrix(self):
        """Генерация матрицы атрибутов для сравнения"""
        attributes = {}
        for product in self.products.all():
            for group, attrs in product.attributes_by_group:
                for attr_value in attrs:
                    key = (group.name, attr_value.attribute.name)
                    attributes.setdefault(key, {})[product.id] = attr_value.value
        return attributes

    def get_absolute_url(self):
        return reverse('compare:detail', kwargs={'pk': self.pk})


class ComparisonItem(models.Model):
    comparison = models.ForeignKey(
        Comparison,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='comparison_items'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at']
        unique_together = ('comparison', 'product')

    def __str__(self):
        return f"{self.comparison} - {self.product.name}"
