from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.text import slugify
from apps.catalog_config.models import Attribute, Category, ProductAttributeValue as CatalogProductAttributeValue


class Product(models.Model):
    name = models.CharField("Название товара", max_length=255)
    slug = models.SlugField(
        "URL-адрес",
        unique=True,
        max_length=255,
        help_text="Автоматически генерируется из названия"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Категория"
    )
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    description = models.TextField("Описание", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(
        "Доступное количество",
        default=0,
        help_text="Количество товара на складе"
    )
    is_available = models.BooleanField(
        "Доступен для заказа",
        default=True,
        help_text="Отображать ли товар в каталоге"
    )

    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()

    @property
    def attributes_by_group(self):
        """Группировка атрибутов по группам для шаблонов"""
        from collections import defaultdict
        groups = defaultdict(list)

        # Используем prefetch_related для оптимизации
        attribute_values = self.attributes.select_related(
            'attribute__groups'
        ).prefetch_related('attribute__groups__category')

        for attr_value in attribute_values:
            for group in attr_value.attribute.groups.all():
                groups[group].append(attr_value)

        return sorted(groups.items(), key=lambda x: x[0].name)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['slug']),
        ]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    is_main = models.BooleanField("Главное изображение", default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_main=True),
                name='unique_main_image_per_product'
            )
        ]
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товара"

    def preview_thumbnail(self):
        if self.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                self.image.url
            )
        return "-"

    preview_thumbnail.short_description = "Превью"

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Изображение для {self.product.name}"


class Review(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    text = models.TextField("Отзыв")
    rating = models.PositiveSmallIntegerField(
        "Оценка",
        choices=[(i, i) for i in range(1, 6)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_review'
            )
        ]
        indexes = [
            models.Index(fields=['product', 'user']),
        ]
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def clean(self):
        if not 1 <= self.rating <= 5:
            raise ValidationError(_("Рейтинг должен быть от 1 до 5"))

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"