# configurator/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from apps.products.models import Product

User = get_user_model()


class CompatibilityRule(models.Model):
    component_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='compatibility_rules',
        limit_choices_to={'app_label': 'products', 'model': 'product'}
    )
    attribute = models.ForeignKey(
        'catalog_config.Attribute',
        on_delete=models.CASCADE,
        related_name='compatibility_rules'
    )
    value = models.CharField(max_length=255)
    required_component_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='required_rules',
        limit_choices_to={'app_label': 'products', 'model': 'product'}
    )
    required_attribute = models.ForeignKey(
        'catalog_config.Attribute',
        on_delete=models.CASCADE,
        related_name='required_attributes'
    )
    required_value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.component_type} [{self.attribute}={self.value}] → {self.required_component_type} [{self.required_attribute}={self.required_value}]"


class BuildComponent(models.Model):
    build = models.ForeignKey('Build', on_delete=models.CASCADE, related_name='components')
    component_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'app_label': 'products', 'model': 'product'},
        verbose_name="Тип компонента"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('component_type', 'object_id')
    selected_options = models.JSONField(blank=True, null=True)

    class Meta:
        unique_together = ('build', 'component_type')

    def __str__(self):
        return f"{self.build.name} - {self.content_object}"


class Build(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='builds')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_compatibility(self):
        errors = []
        components = {c.component_type: c for c in self.components.all()}

        for component in components.values():
            rules = CompatibilityRule.objects.filter(
                component_type=component.component_type,
                value__in=component.content_object.attributes.values_list('value', flat=True)
            )

            for rule in rules:
                required_component = components.get(rule.required_component_type)
                if not required_component:
                    errors.append(f"Отсутствует обязательный компонент: {rule.required_component_type}")
                    continue

                required_attr = required_component.content_object.attributes.filter(
                    attribute=rule.required_attribute
                ).first()

                if not required_attr or required_attr.value != rule.required_value:
                    errors.append(
                        f"Несовместимость: {component} требует {rule.required_attribute} = {rule.required_value}"
                    )

        # Проверка мощности БП
        psu = components.get(ContentType.objects.get(model='psu'))
        if psu:
            total_power = sum(
                comp.content_object.get_tdp()
                for comp in components.values()
                if hasattr(comp.content_object, 'get_tdp')
            )
            if psu.content_object.get_power() < total_power:
                errors.append(f"Недостаточная мощность БП: {psu.content_object.get_power()} Вт / {total_power} Вт")

        return errors

    def get_total_price(self):
        return sum(
            component.content_object.price
            for component in self.components.all()
            if component.content_object
        )