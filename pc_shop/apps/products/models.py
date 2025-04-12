from collections import defaultdict

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.text import slugify
from django.urls import reverse
from django.utils.functional import cached_property
from apps.catalog_config.models import Attribute, Category as CatalogCategory
from mptt.utils import get_cached_trees
from sorl.thumbnail import get_thumbnail
from django.db.models import Avg, Q, Prefetch
from django.core.validators import MinValueValidator


class Product(models.Model):
    name = models.CharField("Название товара", max_length=255)
    slug = models.SlugField(
        "URL-адрес",
        unique=True,
        max_length=255,
        help_text="Автоматически генерируется из названия"
    )
    category = models.ForeignKey(
        CatalogCategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Категория"
    )
    price = models.DecimalField(
        "Цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    description = models.TextField("Описание", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(
        "Доступное количество",
        default=0,
        validators=[MinValueValidator(0)]
    )
    is_available = models.BooleanField(
        "Доступен для заказа",
        default=True,
        help_text="Отображать ли товар в каталоге"
    )
    average_rating = models.DecimalField(
        "Средний рейтинг",
        max_digits=3,
        decimal_places=2,
        default=0.00
    )

    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['slug']),
            models.Index(fields=['price']),
        ]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name

    @cached_property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()

    @cached_property
    def attributes_by_group(self):
        from apps.catalog_config.models import ProductAttributeValue
        attributes = ProductAttributeValue.objects.filter(product=self).select_related(
            'attribute__groups'
        ).prefetch_related('attribute__groups__category')

        groups = defaultdict(list)
        for attr_value in attributes:
            for group in attr_value.attribute.groups.all():
                groups[group].append(attr_value)
        return sorted(groups.items(), key=lambda x: x[0].name)

    def get_tdp(self):
        attr = self.attributes.filter(attribute__name='Тепловыделение (TDP)').first()
        return int(attr.value.replace(' Вт', '')) if attr else 0

    def get_power(self):
        attr = self.attributes.filter(attribute__name='Мощность').first()
        return int(attr.value.replace(' Вт', '')) if attr else 0

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    def update_rating(self):
        """Обновляет средний рейтинг"""
        self.average_rating = self.reviews.filter(approved=True).aggregate(avg=Avg('rating'))['avg'] or 0.00
        self.save(update_fields=['average_rating'])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.is_available = self.quantity > 0
        super().save(*args, **kwargs)


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
            thumb = get_thumbnail(self.image, '100x100', crop='center', quality=99)
            return format_html(f'<img src="{thumb.url}" width="{thumb.width}" height="{thumb.height}"/>')
        return "-"

    preview_thumbnail.short_description = "Превью"

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def get_thumbnail_url(self, size='100x100'):
        return get_thumbnail(self.image, size, crop='center').url


class Review(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    text = models.TextField("Отзыв")
    rating = models.PositiveSmallIntegerField(
        "Оценка",
        choices=[(i, i) for i in range(1, 6)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField("Одобрено", default=False)
    moderator_comment = models.TextField("Комментарий модератора", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_review'
            )
        ]
        indexes = [
            models.Index(fields=['product', 'approved']),
            models.Index(fields=['user']),
        ]
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating})"

    def clean(self):
        if not 1 <= self.rating <= 5:
            raise ValidationError("Рейтинг должен быть от 1 до 5")

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new or self.approved:
            self.product.update_rating()
