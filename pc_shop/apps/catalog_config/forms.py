from django import forms
from mptt.forms import TreeNodeChoiceField
from .models import Category, AttributeGroup, Attribute


class AttributeGroupForm(forms.ModelForm):
    category = TreeNodeChoiceField(queryset=Category.objects.all())

    class Meta:
        model = AttributeGroup
        fields = '__all__'


class AttributeForm(forms.ModelForm):
    class Meta:
        model = Attribute
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        data_type = cleaned_data.get('data_type')

        # Проверяем только при сохранении существующего объекта
        if self.instance.pk and data_type == 'enum':
            if not self.instance.enum_options.exists():
                self.add_error('enum_options', ("Добавьте варианты для типа 'Список'"))
