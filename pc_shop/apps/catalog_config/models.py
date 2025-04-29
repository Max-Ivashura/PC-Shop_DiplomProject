from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.translation import gettext_lazy as _
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
    path = models.CharField(_("Путь категории"), max_length=255, editable=False, blank=True, db_index=True)

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)

        ancestors = self.get_ancestors(include_self=True)
        self.path = ' > '.join(ancestor.name for ancestor in ancestors)
        super().save(*args, **kwargs)

    def get_all_attributes(self):
        return Attribute.objects.filter(
            Q(groups__group__category=self) | Q(groups__group__category__in=self.get_descendants())
        ).prefetch_related(
            'groups__group__category',
            'enum_options'
        ).distinct()


@receiver([post_save, post_delete], sender=Category)
def update_descendants_path(sender, instance, **kwargs):
    if kwargs.get('update_fields') and 'path' in kwargs['update_fields']:
        return
    for descendant in instance.get_descendants():
        descendant.save(update_fields=['path'])


class AttributeGroupLink(models.Model):
    attribute = models.ForeignKey('Attribute', on_delete=models.CASCADE)
    group = models.ForeignKey('AttributeGroup', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('attribute', 'group')
        verbose_name = _("Связь атрибута с группой")
        verbose_name_plural = _("Связи атрибутов с группами")


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


class AttributeManager(models.Manager):
    def required_attributes(self):
        return self.filter(is_required=True)

    def compatibility_critical(self):
        return self.filter(compatibility_critical=True)


class Attribute(MPTTModel):
    DATA_TYPES = [
        ('string', _('Строка')),
        ('number', _('Число')),
        ('boolean', _('Да/Нет')),
        ('enum', _('Список')),
    ]

    objects = AttributeManager()

    name = models.CharField(_("Название атрибута"), max_length=255)
    data_type = models.CharField(_("Тип данных"), max_length=10, choices=DATA_TYPES)
    groups = models.ManyToManyField(
        AttributeGroup,
        through='AttributeGroupLink',
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
        verbose_name=_("Родительский атрибут")
    )

    class Meta:
        verbose_name = _("Атрибут")
        verbose_name_plural = _("Атрибуты")
        indexes = [
            models.Index(fields=['data_type', 'is_required']),
            models.Index(fields=['name']),
        ]

    class MPTTMeta:
        order_insertion_by = ['name']

    def clean(self):
        super().clean()
        if self.pk:
            for group in self.groups.all():
                if Attribute.objects.filter(
                        name=self.name,
                        groups=group
                ).exclude(pk=self.pk).exists():
                    raise ValidationError(
                        _("Атрибут с именем '%(name)s' уже существует в группе '%(group)s'") % {
                            'name': self.name,
                            'group': group
                        }
                    )

    def __str__(self):
        return f"{self.name} ({self.get_data_type_display()})"


class EnumOption(models.Model):
    attribute = models.ForeignKey(
        Attribute,
        related_name='enum_options',
        on_delete=models.CASCADE,
        verbose_name=_("Атрибут")
    )
    value = models.CharField(_("Значение"), max_length=255, blank=True)

    class Meta:
        ordering = ['value']
        unique_together = ('attribute', 'value')
        verbose_name = _("Вариант списка")
        verbose_name_plural = _("Варианты списка")

    def __str__(self):
        return self.value


