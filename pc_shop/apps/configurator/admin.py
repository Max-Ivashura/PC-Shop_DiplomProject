from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Build, BuildComponent, CompatibilityRule

class BuildComponentInline(admin.TabularInline):
    model = BuildComponent
    extra = 0
    readonly_fields = ('component_type', 'component_preview')
    fields = ('component_type', 'component_preview', 'selected_options')
    template = 'admin/configurator/build/stacked.html'

    def component_preview(self, obj):
        if obj.content_object:
            url = reverse(f'admin:products_product_change', args=[obj.object_id])
            return format_html(
                '<a href="{}" target="_blank">{} → {}</a>',
                url,
                obj.component_type,
                obj.content_object.name
            )
        return "-"
    component_preview.short_description = "Компонент"

@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'component_count', 'compatibility_status', 'is_public', 'created_at')
    list_filter = ('is_public', 'user')
    search_fields = ('name', 'user__username')
    inlines = [BuildComponentInline]
    readonly_fields = ('compatibility_errors',)
    save_on_top = True

    def component_count(self, obj):
        return obj.components.count()
    component_count.short_description = "Компонентов"

    def compatibility_status(self, obj):
        errors = obj.check_compatibility()
        color = 'green' if not errors else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            'OK' if not errors else f'{len(errors)} ошибок'
        )
    compatibility_status.short_description = "Совместимость"

    def compatibility_errors(self, obj):
        errors = obj.check_compatibility()
        if not errors:
            return "Нет ошибок"
        return mark_safe("<br>".join(errors))
    compatibility_errors.short_description = "Ошибки совместимости"

@admin.register(CompatibilityRule)
class CompatibilityRuleAdmin(admin.ModelAdmin):
    list_display = ('component_type', 'attribute', 'value', 'required_component_type', 'required_value')
    list_filter = ('component_type', 'required_component_type')
    search_fields = ('attribute__name', 'value', 'required_value')
    save_as = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "component_type":
            kwargs["queryset"] = ContentType.objects.filter(app_label='products', model='product')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)