from django.contrib import admin
from .models import Category, Product, AttributeGroup, Attribute, ProductAttribute, ProductImage
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from django.utils.html import format_html
from mptt.forms import TreeNodeChoiceField
from django import forms
from django.db import models


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = (
        'tree_actions',
        'indented_title_modified',
        'slug',
        'parent'
    )
    list_display_links = ('indented_title_modified',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def indented_title_modified(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance.mptt_level * 30,  # Увеличиваем отступ для наглядности
            instance.name
        )

    indented_title_modified.short_description = 'Категория'

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('tree_id', 'lft')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('name', 'category', 'price')
    prepopulated_fields = {'slug': ('name',)}


class AttributeGroupForm(forms.ModelForm):
    category = TreeNodeChoiceField(
        queryset=Category.objects.all(),
        level_indicator="---",
        label="Категория"
    )


@admin.register(AttributeGroup)
class AttributeGroupAdmin(admin.ModelAdmin):
    change_list_template = 'admin/products/attributegroup/change_list.html'
    form = AttributeGroupForm
    list_display = ('name', 'indented_category', 'category')
    list_filter = ('category',)
    search_fields = ('category__name', 'name')

    def changelist_view(self, request, extra_context=None):
        # Используем annotate для подсчета групп
        categories = Category.objects.annotate(
            num_groups=models.Count('attribute_groups')
        ).prefetch_related('attribute_groups').order_by('tree_id', 'lft')

        grouped_data = []
        for category in categories:
            # Проверяем, есть ли группы через аннотацию
            if category.num_groups > 0:
                grouped_data.append({
                    'id': category.id,
                    'name': category.name,
                    'attribute_groups': category.attribute_groups.all()
                })

        extra_context = extra_context or {}
        extra_context['categories'] = grouped_data

        return super().changelist_view(request, extra_context=extra_context)

    def indented_category(self, obj):
        return self.format_hierarchy(obj.category)

    indented_category.short_description = 'Иерархия категории'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Для поля category используем кастомный виджет с иерархией
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.all().order_by('tree_id', 'lft')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @staticmethod
    def format_hierarchy(category):
        if not category:
            return ""
        ancestors = category.get_ancestors(include_self=True)
        return " → ".join([c.name for c in ancestors])


from django.contrib import admin
from .models import Attribute


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'category', 'data_type', 'unit_display')
    list_filter = ('group__category', 'data_type')
    change_list_template = 'admin/products/attribute/change_list.html'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group__category')

    def category(self, obj):
        return obj.group.category.name

    category.short_description = "Категория"

    def unit_display(self, obj):
        return obj.unit if obj.unit else '—'

    unit_display.short_description = 'Единица измерения'

    def changelist_view(self, request, extra_context=None):
        from .models import Category
        categories = Category.objects.prefetch_related(
            'attribute_groups__attributes'
        ).order_by('tree_id', 'lft')

        grouped_data = []
        for category in categories:
            groups = []
            for group in category.attribute_groups.all():
                attributes = group.attributes.all()
                if attributes:
                    groups.append({
                        'id': group.id,
                        'name': group.name,
                        'attributes': attributes
                    })
            if groups:
                grouped_data.append({
                    'id': category.id,
                    'name': category.name,
                    'groups': groups
                })

        extra_context = extra_context or {}
        extra_context['categories'] = grouped_data

        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(ProductAttribute)
