from django import template
from products.models import ProductImage

register = template.Library()

@register.filter
def get_main_image(gallery):
    return gallery.filter(is_main=True).first()