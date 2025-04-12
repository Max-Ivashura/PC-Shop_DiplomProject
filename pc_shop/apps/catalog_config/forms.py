from django import forms
from django.core.exceptions import ValidationError
from mptt.forms import TreeNodeChoiceField
from apps.catalog_config.models import Category, AttributeGroup, Attribute, AttributeGroupLink
from django.utils.translation import gettext_lazy as _


class AttributeGroupForm(forms.ModelForm):
    category = TreeNodeChoiceField(
        queryset=Category.objects.all(),
        label=_("Категория"),
        help_text=_("Выберите родительскую категорию для группы атрибутов")
    )

    class Meta:
        model = AttributeGroup
        fields = '__all__'
        widgets = {
            'parent': forms.Select(attrs={'class': 'mptt-select'})
        }

    def clean_parent(self):
        parent = self.cleaned_data.get('parent')
        category = self.cleaned_data.get('category')

        if parent and parent.category != category:
            raise ValidationError(
                _("Родительская группа должна принадлежать той же категории")
            )
        return parent


class AttributeForm(forms.ModelForm):
    data_type = forms.ChoiceField(
        choices=Attribute.DATA_TYPES,
        label=_("Тип данных"),
        widget=forms.Select(attrs={
            'class': 'data-type-selector',
            'onchange': "toggleFields(this)"
        })
    )

    class Meta:
        model = Attribute
        fields = '__all__'
        widgets = {
            'validation_regex': forms.TextInput(attrs={
                'placeholder': '^[A-Za-z0-9]+$'
            }),
            'parent': forms.Select(attrs={'class': 'mptt-select'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._toggle_fields_based_on_type()

    def _toggle_fields_based_on_type(self):
        """Скрываем/показываем поля в зависимости от типа данных"""
        data_type = self.instance.data_type if self.instance.pk else None
        if 'data_type' in self.data:  # При отправке формы
            data_type = self.data.get('data_type')

        # Скрываем ненужные поля
        if data_type != 'string':
            self.fields['validation_regex'].widget = forms.HiddenInput()
        if data_type != 'enum':
            self.fields['unit'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        data_type = cleaned_data.get('data_type')
        is_new = not self.instance.pk

        # Для новых и существующих объектов
        if data_type == 'enum':
            if is_new and not self.data.get('enum_options'):
                raise ValidationError({
                    'data_type': _("Для типа 'Список' необходимо добавить варианты значений")
                })
            elif not is_new and not self.instance.enum_options.exists():
                raise ValidationError({
                    'data_type': _("Добавьте варианты значений для типа 'Список'")
                })

        # Валидация уникальности через промежуточную модель
        name = cleaned_data.get('name')
        groups = cleaned_data.get('groups')
        if name and groups:
            conflicting = AttributeGroupLink.objects.filter(
                attribute__name=name,
                group__in=groups
            ).exclude(attribute=self.instance).exists()

            if conflicting:
                raise ValidationError(
                    _("Атрибут с именем '%(name)s' уже существует в выбранных группах") % {
                        'name': name
                    }
                )

        return cleaned_data
