from django.contrib import admin
from .models import Category, Product, AttributeGroup, Attribute, ProductAttribute, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('name', 'category', 'price')
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(AttributeGroup)
admin.site.register(Attribute)
admin.site.register(ProductAttribute)
