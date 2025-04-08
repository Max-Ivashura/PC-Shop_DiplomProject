from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    # Удаляем пагинацию при изменении параметров
    if 'page' in query:
        del query['page']
    return query.urlencode()