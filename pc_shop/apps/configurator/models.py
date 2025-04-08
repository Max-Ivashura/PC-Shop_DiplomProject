from django.db import models
from django.contrib.auth import get_user_model
from apps.products.models import Product

User = get_user_model()


class CompatibilityRule(models.Model):
    COMPONENT_TYPES = [
        ('cpu', 'Процессор'),
        ('gpu', 'Видеокарта'),
        ('motherboard', 'Материнская плата'),
        ('ram', 'Оперативная память'),
        ('psu', 'Блок питания'),
        ('storage', 'Накопитель'),
        ('cooler', 'Система охлаждения'),
    ]

    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES)
    required_attribute = models.CharField(max_length=255, help_text="Например: 'Сокет', 'Тип памяти'")
    allowed_values = models.TextField(help_text="Разделенные запятой допустимые значения")

    def __str__(self):
        return f"{self.get_component_type_display()}: {self.required_attribute}"


class Build(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='builds')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cpu = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                            limit_choices_to={'category__name': 'Процессоры'})
    gpu = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                            limit_choices_to={'category__name': 'Видеокарты'}, null=True, blank=True)
    motherboard = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                                    limit_choices_to={'category__name': 'Материнские платы'})
    ram = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                            limit_choices_to={'category__name': 'Оперативная память'})
    psu = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                            limit_choices_to={'category__name': 'Блоки питания'})
    storage = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                                limit_choices_to={'category__name': 'Накопители'})
    cooler = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+',
                               limit_choices_to={'category__name': 'Системы охлаждения'}, null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_compatibility(self):
        errors = []

        # Проверка сокета CPU и материнской платы
        cpu_socket = self.cpu.attributes.filter(attribute__name='Сокет').first()
        motherboard_socket = self.motherboard.attributes.filter(attribute__name='Сокет').first()
        if cpu_socket and motherboard_socket and cpu_socket.value != motherboard_socket.value:
            errors.append("Несовместимость: Сокет процессора и материнской платы не совпадают")

        # Проверка совместимости RAM
        ram_type = self.ram.attributes.filter(attribute__name='Тип памяти').first()
        motherboard_ram_support = self.motherboard.attributes.filter(
            attribute__name='Поддерживаемые типы памяти').first()
        if ram_type and motherboard_ram_support and ram_type.value not in motherboard_ram_support.value.split(', '):
            errors.append("Несовместимость: Тип памяти не поддерживается материнской платой")

        # Проверка блока питания
        psu_power = self.psu.attributes.filter(attribute__name='Мощность').first()
        required_power = sum(
            component.attributes.filter(attribute__name='Тепловыделение (TDP)').first().value
            for component in [self.cpu, self.gpu, self.motherboard, self.ram, self.storage, self.cooler]
            if component and component.attributes.filter(attribute__name='Тепловыделение (TDP)').exists()
        )
        if psu_power and required_power > int(psu_power.value.replace(' Вт', '')):
            errors.append("Недостаточная мощность блока питания")

        return errors

    def __str__(self):
        return self.name