from django.db import models


class Category(models.Model):
    name = models.CharField("Название категории", max_length=255)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("Название товара", max_length=255)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Категория"
    )
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    description = models.TextField("Описание", blank=True)
    image = models.ImageField("Изображение", upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name


class AttributeGroup(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='attribute_groups',
        verbose_name="Категория"
    )
    name = models.CharField("Название группы", max_length=255)

    class Meta:
        verbose_name = "Группа характеристик"
        verbose_name_plural = "Группы характеристик"

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Attribute(models.Model):
    group = models.ForeignKey(
        AttributeGroup,
        on_delete=models.CASCADE,
        related_name='attributes',
        verbose_name="Группа"
    )
    name = models.CharField("Название характеристики", max_length=255)

    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики"

    def __str__(self):
        return f"{self.group.name} - {self.name}"


class ProductAttribute(models.Model):
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

    class Meta:
        verbose_name = "Значение характеристики"
        verbose_name_plural = "Значения характеристик"

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"
