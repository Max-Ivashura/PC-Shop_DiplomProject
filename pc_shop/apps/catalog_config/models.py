from django.db import models
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
import re
from django.db.models import Q


class Category(MPTTModel):
    name = models.CharField(_("Название категории"), max_length=255)
    slug = models.SlugField(unique=True)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Родительская категория")
    )
    path = models.CharField(_("Путь категории"), max_length=255, editable=False, blank=True)

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Теперь можно вызывать MPTT-методы
        ancestors = self.get_ancestors(include_self=True)
        self.path = ' > '.join(ancestor.name for ancestor in ancestors)
        super().save(*args, **kwargs)

    def get_all_attributes(self):
        return Attribute.objects.filter(
            Q(groups__category=self) | Q(groups__category__in=self.get_descendants())
        ).select_related('parent').prefetch_related(
            'groups__category',
            'enum_options'
        ).distinct()


class AttributeGroup(MPTTModel):
    name = models.CharField(_("Название группы"), max_length=255)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Родительская группа")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='attribute_groups',
        verbose_name=_("Категория")
    )

    class Meta:
        verbose_name = _("Группа атрибутов")
        verbose_name_plural = _("Группы атрибутов")

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return f"{self.category.name} > {self.name}"


class Attribute(MPTTModel):
    DATA_TYPES = [
        ('string', _('Строка')),
        ('number', _('Число')),
        ('boolean', _('Да/Нет')),
        ('enum', _('Список')),
    ]

    name = models.CharField(_("Название атрибута"), max_length=255)
    data_type = models.CharField(_("Тип данных"), max_length=10, choices=DATA_TYPES)
    groups = models.ManyToManyField(
        AttributeGroup,
        related_name='attributes',
        verbose_name=_("Группы атрибутов")
    )
    unit = models.CharField(_("Единица измерения"), max_length=20, blank=True)
    is_required = models.BooleanField(_("Обязательный"), default=False)
    compatibility_critical = models.BooleanField(
        "Критично для совместимости",
        default=False,
        help_text="Атрибут влияет на совместимость компонентов"
    )
    validation_regex = models.CharField(
        _("Регулярное выражение"),
        max_length=255,
        blank=True,
        help_text=_("Пример: ^[A-Za-z0-9]+$ (только латиница и цифры)")
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Родительский атрибут")  # Исправлено
    )


    class Meta:
        verbose_name = _("Атрибут")
        verbose_name_plural = _("Атрибуты")
        indexes = [
            models.Index(fields=['data_type', 'is_required']),  # Составной индекс
            models.Index(fields=['name']),
        ]

    class MPTTMeta:
        order_insertion_by = ['name']

    def clean(self):
        if self.validation_regex:
            try:
                re.compile(self.validation_regex)
            except re.error:
                raise ValidationError(_("Невалидное регулярное выражение"))

    def __str__(self):
        return f"{self.name} ({self.get_data_type_display()})"


class EnumOption(models.Model):
    attribute = models.ForeignKey(
        Attribute,
        related_name='enum_options',
        on_delete=models.CASCADE,
        verbose_name=_("Атрибут")
    )
    value = models.CharField(_("Значение"), max_length=255)

    class Meta:
        ordering = ['value']
        unique_together = ('attribute', 'value')
        verbose_name = _("Вариант списка")
        verbose_name_plural = _("Варианты списка")

    def __str__(self):
        return self.value


class ProductAttributeValue(models.Model):
    product = models.ForeignKey(
        'products.Product',
        related_name='attributes',
        on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        verbose_name=_("Атрибут")
    )
    value = JSONField(_("Значение"))

    class Meta:
        unique_together = ('product', 'attribute')
        indexes = [
            models.Index(fields=['attribute']),
            models.Index(fields=['product']),
        ]

    def clean(self):
        attr = self.attribute
        val = self.value

        if attr.is_required and val in (None, ''):
            raise ValidationError(_("Значение обязательно для заполнения"))

        if attr.data_type == 'string':
            if not isinstance(val, str):
                raise ValidationError(_("Требуется строковое значение"))
            if attr.validation_regex and not re.match(attr.validation_regex, val):
                raise ValidationError(_("Неверный формат строки"))
        elif attr.data_type == 'number':
            if not isinstance(val, (int, float)):
                raise ValidationError(_("Требуется числовое значение"))
        elif attr.data_type == 'boolean':
            if not isinstance(val, bool):
                raise ValidationError(_("Требуется логическое значение"))
        elif attr.data_type == 'enum':
            valid_values = set(attr.enum_options.values_list('value', flat=True))
            if val not in valid_values:
                raise ValidationError(_("Недопустимое значение для списка"))

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"