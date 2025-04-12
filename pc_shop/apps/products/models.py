from collections import defaultdict
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.template.defaultfilters import time
from django.utils.html import format_html
from django.utils.text import slugify
from django.urls import reverse
from django.utils.functional import cached_property
from apps.catalog_config.models import Attribute, Category as CatalogCategory
from mptt.utils import get_cached_trees
from sorl.thumbnail import get_thumbnail
from django.db.models import Avg, Q, Prefetch
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils.translation import gettext_lazy as _


class Product(models.Model):
    sku = models.CharField(
        _("Артикул"),
        max_length=32,
        unique=True,
        help_text=_("Уникальный идентификатор товара")
    )
    name = models.CharField(
        _("Название товара"),
        max_length=255,
        db_index=True
    )
    slug = models.SlugField(
        _("URL-адрес"),
        max_length=255,
        help_text=_("Автоматически генерируется из названия")
    )
    category = models.ForeignKey(
        CatalogCategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_("Категория")
    )
    price = models.DecimalField(
        _("Цена"),
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0.01, _("Цена не может быть меньше 0.01"))
        ]
    )
    description = models.TextField(_("Описание"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(
        _("Доступное количество"),
        default=0,
        validators=[MinValueValidator(0)]
    )
    is_available = models.BooleanField(
        _("Доступен для заказа"),
        default=True,
        help_text=_("Отображать ли товар в каталоге")
    )
    is_digital = models.BooleanField(
        _("Цифровой товар"),
        default=False,
        help_text=_("Не требует физической доставки")
    )

    class Meta:
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")
        unique_together = [['name', 'category']]
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['sku']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @cached_property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()

    @cached_property
    def attributes_by_group(self):
        attributes = self.attributes.select_related(
            'attribute__groups'
        ).prefetch_related(
            'attribute__groups__category'
        )

        groups = defaultdict(list)
        for attr_value in attributes:
            for group in attr_value.attribute.groups.all():
                groups[group].append(attr_value)
        return sorted(groups.items(), key=lambda x: x[0].name)

    @property
    def average_rating(self):
        return self.reviews.filter(approved=True).aggregate(
            avg=Avg('rating')
        )['avg'] or 0.00

    def clean(self):
        if not self.sku:
            raise ValidationError(_("Артикул обязателен для заполнения"))

        if self.price < 0:
            raise ValidationError(_("Цена не может быть отрицательной"))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        if not self.sku:
            self.sku = f"PRD-{self.category.id}-{int(time.time())}"

        self.is_available = self.quantity > 0
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='products/gallery/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png'],
                message=_("Допустимые форматы: JPG, JPEG, PNG")
            )
        ]
    )
    is_main = models.BooleanField(_("Главное изображение"), default=False)

    class Meta:
        verbose_name = _("Изображение товара")
        verbose_name_plural = _("Изображения товара")
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_main=True),
                name='unique_main_image_per_product'
            )
        ]

    def preview_thumbnail(self):
        if self.image:
            thumb = get_thumbnail(self.image, '100x100', crop='center', quality=99)
            return format_html(
                f'<img src="{thumb.url}" width="{thumb.width}" height="{thumb.height}"/>'
            )
        return "-"

    preview_thumbnail.short_description = _("Превью")

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(
                product=self.product
            ).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)


class Review(models.Model):
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    text = models.TextField(_("Отзыв"))
    rating = models.PositiveSmallIntegerField(
        _("Оценка"),
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(_("Одобрено"), default=False)
    moderator_comment = models.TextField(_("Комментарий модератора"), blank=True)

    class Meta:
        verbose_name = _("Отзыв")
        verbose_name_plural = _("Отзывы")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_review_per_user_product'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating})"

    def clean(self):
        if not 1 <= self.rating <= 5:
            raise ValidationError(_("Рейтинг должен быть от 1 до 5"))
