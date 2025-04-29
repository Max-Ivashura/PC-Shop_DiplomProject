from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from apps.products.models import Product
from apps.catalog_config.models import Attribute

User = get_user_model()

class ComponentType(models.Model):
    """Тип компонента для конфигуратора (процессор, видеокарта и т.д.)"""
    name = models.CharField(_("Название"), max_length=100, unique=True)
    slug = models.SlugField(_("Slug"), unique=True)
    required = models.BooleanField(_("Обязательный"), default=False)
    order = models.PositiveIntegerField(_("Порядок"), default=0)
    compatibility_attributes = models.ManyToManyField(
        Attribute,
        verbose_name=_("Критические атрибуты"),
        related_name='component_types',
        limit_choices_to={'compatibility_critical': True}
    )

    class Meta:
        verbose_name = _("Тип компонента")
        verbose_name_plural = _("Типы компонентов")
        ordering = ['order']

    def __str__(self):
        return self.name

class CompatibilityRule(models.Model):
    """Правило совместимости между типами компонентов"""
    source_type = models.ForeignKey(
        ComponentType,
        on_delete=models.CASCADE,
        related_name='source_rules',
        verbose_name=_("Исходный тип")
    )
    source_attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='source_rules',
        verbose_name=_("Атрибут источника")
    )
    target_type = models.ForeignKey(
        ComponentType,
        on_delete=models.CASCADE,
        related_name='target_rules',
        verbose_name=_("Целевой тип")
    )
    target_attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='target_rules',
        verbose_name=_("Атрибут цели")
    )
    rule_type = models.CharField(
        _("Тип правила"),
        max_length=20,
        choices=[
            ('required', _("Обязательное")),
            ('incompatible', _("Несовместимое"))
        ],
        default='required'
    )

    class Meta:
        verbose_name = _("Правило совместимости")
        verbose_name_plural = _("Правила совместимости")
        unique_together = ('source_type', 'source_attribute', 'target_type', 'target_attribute')

    def __str__(self):
        return f"{self.source_type} → {self.target_type} ({self.rule_type})"

class BuildComponent(models.Model):
    """Компонент в сборке"""
    build = models.ForeignKey(
        'Build',
        on_delete=models.CASCADE,
        related_name='components',
        verbose_name=_("Сборка")
    )
    component_type = models.ForeignKey(
        ComponentType,
        on_delete=models.PROTECT,
        verbose_name=_("Тип компонента")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_("Продукт"),
        related_name='build_components'
    )

    class Meta:
        verbose_name = _("Компонент сборки")
        verbose_name_plural = _("Компоненты сборки")
        unique_together = ('build', 'component_type')

    def __str__(self):
        return f"{self.build.name} - {self.component_type}"

    def clean(self):
        """Проверка соответствия атрибутов продукта требованиям типа компонента"""
        required_attributes = self.component_type.compatibility_attributes.all()
        product_attributes = self.product.attributes.values_list('attribute', flat=True)

        missing = required_attributes.exclude(id__in=product_attributes)
        if missing.exists():
            raise ValidationError(
                _("Продукт не имеет требуемых атрибутов: %(attrs)s") % {
                    'attrs': ', '.join(missing.values_list('name', flat=True))
                }
            )

class Build(models.Model):
    """Пользовательская сборка компонентов"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='builds',
        verbose_name=_("Пользователь")
    )
    name = models.CharField(_("Название"), max_length=100)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)
    total_price = models.DecimalField(
        _("Общая стоимость"),
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        verbose_name = _("Сборка")
        verbose_name_plural = _("Сборки")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user})"

    def update_total_price(self):
        """Обновление общей стоимости на основе выбранных компонентов"""
        self.total_price = sum(
            component.product.price
            for component in self.components.all()
        )
        self.save(update_fields=['total_price', 'updated_at'])

    def check_compatibility(self):
        """Проверка совместимости компонентов через ProductAttributeValue"""
        errors = []
        components = {c.component_type: c for c in self.components.all()}

        # Проверка обязательных компонентов
        missing_required = ComponentType.objects.filter(
            required=True
        ).exclude(id__in=components.keys())
        if missing_required.exists():
            errors.append(
                _("Отсутствуют обязательные компоненты: %(types)s") % {
                    'types': ', '.join(missing_required.values_list('name', flat=True))
                }
            )

        # Проверка правил совместимости
        for rule in CompatibilityRule.objects.filter(source_type__in=components.keys()):
            source = components.get(rule.source_type)
            target = components.get(rule.target_type)

            if not (source and target):
                continue

            source_value = source.product.attributes.filter(
                attribute=rule.source_attribute
            ).first()
            target_value = target.product.attributes.filter(
                attribute=rule.target_attribute
            ).first()

            if not (source_value and target_value):
                continue

            if rule.rule_type == 'required' and not self._check_required_rule(source_value, target_value):
                errors.append(
                    _("%(source_type)s (%(source_attr)s=%(source_val)s) требует "
                      "%(target_attr)s=%(target_val)s для %(target_type)s") % {
                        'source_type': rule.source_type,
                        'source_attr': rule.source_attribute.name,
                        'source_val': source_value.value,
                        'target_attr': rule.target_attribute.name,
                        'target_val': rule.target_attribute.compatibility_value,
                        'target_type': rule.target_type
                    }
                )
            elif rule.rule_type == 'incompatible' and self._check_incompatible_rule(source_value, target_value):
                errors.append(
                    _("%(source_type)s несовместим с %(target_type)s") % {
                        'source_type': rule.source_type,
                        'target_type': rule.target_type
                    }
                )

        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }

    def _check_required_rule(self, source_value, target_value):
        return target_value.value == source_value.attribute.compatibility_value

    def _check_incompatible_rule(self, source_value, target_value):
        return target_value.value == source_value.attribute.incompatibility_value

    def save(self, *args, **kwargs):
        self.update_total_price()
        super().save(*args, **kwargs)