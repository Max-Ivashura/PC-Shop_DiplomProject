from django import forms
from .models import ProductAttribute


class ProductAttributeForm(forms.ModelForm):
    class Meta:
        model = ProductAttribute
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Проверяем, что instance существует и имеет связанный attribute
        if self.instance and self.instance.pk and self.instance.attribute:
            self.set_widget_based_on_type()

    def set_widget_based_on_type(self):
        data_type = self.instance.attribute.data_type

        if data_type == 'bool':
            self.fields['value'].widget = forms.CheckboxInput()
            self.fields['value'].required = False
            # Устанавливаем начальное значение для чекбокса
            if self.instance.value.lower() in ['true', '1', 'yes']:
                self.fields['value'].initial = True
        elif data_type == 'int':
            self.fields['value'].widget = forms.NumberInput(attrs={'step': '1'})
        elif data_type == 'float':
            self.fields['value'].widget = forms.NumberInput(attrs={'step': '0.1'})
        else:
            self.fields['value'].widget = forms.TextInput()

    def clean_value(self):
        data_type = self.instance.attribute.data_type
        value = self.cleaned_data['value']

        if data_type == 'int':
            try:
                return int(value)
            except (ValueError, TypeError):
                raise forms.ValidationError("Введите целое число")
        elif data_type == 'float':
            try:
                return float(value)
            except (ValueError, TypeError):
                raise forms.ValidationError("Введите число")
        elif data_type == 'bool':
            return str(value).lower() in ['true', '1', 'yes']

        return value