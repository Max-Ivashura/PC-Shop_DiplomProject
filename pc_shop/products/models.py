from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.text import slugify
from catalog_config.models import Attribute, Category, Attribute


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
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Категория"
    )
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    description = models.TextField("Описание", blank=True)
    images = models.ManyToManyField('ProductImage', blank=True, related_name='products')
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
        return self.gallery.filter(is_main=True).first() or self.gallery.first()

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def save(self, *args, **kwargs):
        if not self.slug:  # Генерируем только при создании
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='products/gallery/')
    is_main = models.BooleanField(default=False, verbose_name="Главное изображение")

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товара"

    def __str__(self):
        return f"Изображение для {self.product.name}"

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
            # Снимаем статус главного с других изображений
            ProductImage.objects.filter(product=self.product).update(is_main=False)
        super().save(*args, **kwargs)


class ProductAttribute(models.Model):
    DATA_TYPE_CHOICES = [
        ('str', 'Строка'),
        ('int', 'Целое число'),
        ('float', 'Десятичное число'),
        ('bool', 'Да/Нет'),
    ]
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='attributes',
        verbose_name="Товар"
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        verbose_name="Характеристика"
    )
    value = models.CharField("Значение", max_length=255)

    @property
    def typed_value(self):
        try:
            if self.attribute.data_type == 'int':
                return int(self.value)
            elif self.attribute.data_type == 'float':
                return float(self.value)
            elif self.attribute.data_type == 'bool':
                return self.value.lower() in ['true', '1', 'yes']
            return self.value
        except (ValueError, TypeError):
            return self.value

    class Meta:
        verbose_name = "Значение характеристики"
        verbose_name_plural = "Значения характеристик"

    def clean(self):
        if self.attribute.data_type == 'int' and not self.value.isdigit():
            raise ValidationError("Введите целое число")

    def get_data_type_display(self):
        return dict(self.DATA_TYPE_CHOICES).get(self.data_type, '')

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"


User = get_user_model()


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    text = models.TextField("Отзыв")
    rating = models.PositiveSmallIntegerField("Оценка", choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
