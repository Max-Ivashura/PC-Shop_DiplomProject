from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel


class Category(MPTTModel):
    name = models.CharField("Название категории", max_length=255)
    slug = models.SlugField(unique=True)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )

    class MPTTMeta:
        order_insertion_by = ['name']  # Ключевой параметр для сортировки
        level_attr = 'mptt_level'  # Добавляем для кастомизации

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

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

    def get_attributes(self):
        return self.attributes.all()

    def get_admin_url(self):
        from django.urls import reverse
        return reverse('admin:catalog_config_attributegroup_change', args=[self.id])

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Attribute(models.Model):
    DATA_TYPE_CHOICES = [
        ('str', 'Строка'),
        ('int', 'Целое число'),
        ('float', 'Десятичное число'),
        ('bool', 'Да/Нет'),
    ]

    group = models.ForeignKey(
        AttributeGroup,
        on_delete=models.CASCADE,
        related_name='attributes',
        verbose_name="Группа"
    )
    name = models.CharField("Название характеристики", max_length=255)
    data_type = models.CharField(
        "Тип данных",
        max_length=10,
        choices=DATA_TYPE_CHOICES,
        default='str'
    )
    unit = models.CharField(
        "Единица измерения",
        max_length=20,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики"

    def get_data_type_display(self):
        return dict(self.DATA_TYPE_CHOICES).get(self.data_type, '')

    def __str__(self):
        return f"{self.group.name} - {self.name}"
