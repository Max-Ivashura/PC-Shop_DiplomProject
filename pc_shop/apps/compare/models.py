from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from apps.products.models import Product, Category


class Comparison(models.Model):
    MAX_PRODUCTS = 4
    MAX_COMPARISONS_PER_USER = 3

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='comparisons',
        verbose_name="Пользователь",
        null=True,
        blank=True
    )
    session_key = models.CharField(
        "Ключ сессии",
        max_length=40,
        null=True,
        blank=True,
        db_index=True
    )
    products = models.ManyToManyField(
        Product,
        through='ComparisonItem',
        related_name='comparisons'
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категория сравнения"
    )

    class Meta:
        verbose_name = "Сравнение"
        verbose_name_plural = "Сравнения"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'session_key']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name='user_or_session_required'
            )
        ]

    def __str__(self):
        identifier = self.user.username if self.user else f"Session {self.session_key}"
        return f"Сравнение {identifier} ({self.products.count()} товаров)"

    def clean(self):
        # Проверка лимита сравнений для авторизованных пользователей
        if self.user and self.user.comparisons.count() >= self.MAX_COMPARISONS_PER_USER:
            raise ValidationError(
                f"Максимум {self.MAX_COMPARISONS_PER_USER} сравнений для пользователя"
            )

        # Проверка категории при добавлении первого товара
        if self.products.exists() and self.category_id != self.products.first().category_id:
            raise ValidationError("Все товары должны быть из одной категории")

    def add_product(self, product):
        """Безопасное добавление товара с проверкой категории"""
        if self.products.count() >= self.MAX_PRODUCTS:
            raise ValidationError(f"Достигнут лимит в {self.MAX_PRODUCTS} товаров")

        # Установка категории при первом добавлении
        if not self.category:
            self.category = product.category
            self.save()

        # Проверка совпадения категории
        if product.category != self.category:
            raise ValidationError("Нельзя сравнивать товары из разных категорий")

        if product not in self.products.all():
            self.products.add(product)
            self.refresh_from_db()

    def remove_product(self, product):
        """Удаление товара с автоматическим обновлением категории"""
        if product in self.products.all():
            self.products.remove(product)

            # Обновление категории если список пуст
            if self.products.count() == 0:
                self.category = None
                self.save()

            # Удаление пустого сравнения через 1 минуту
            if self.products.count() == 0:
                from django.utils import timezone
                from datetime import timedelta
                if self.created_at < timezone.now() - timedelta(minutes=1):
                    self.delete()

    @property
    def attributes_matrix(self):
        """Оптимизированная матрица атрибутов с группировкой"""
        attributes = {}
        products = self.products.prefetch_related(
            'attributes__attribute__groups__group__category',
            'attributes__attribute__enum_options'
        )

        # Собираем все атрибуты категории
        category_attrs = self.category.get_all_attributes() if self.category else []

        for attr in category_attrs:
            for group in attr.groups.all():
                group_key = (group.group.category.path, group.group.name)
                attr_key = f"{attr.name} ({attr.unit})" if attr.unit else attr.name

                attributes.setdefault(group_key, {})[attr] = {
                    product.id: self._get_attribute_value(product, attr)
                    for product in products
                }

        return attributes

    def _get_attribute_value(self, product, attribute):
        """Получение значения атрибута для продукта"""
        try:
            value = product.attributes.get(attribute=attribute).value
            if attribute.data_type == 'boolean':
                return "Да" if value else "Нет"
            return value
        except ProductAttributeValue.DoesNotExist:
            return "-"

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
        indexes = [
            models.Index(fields=['comparison', 'product']),
            models.Index(fields=['added_at']),
        ]

    def __str__(self):
        return f"{self.comparison} - {self.product.name}"