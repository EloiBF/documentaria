# file_processor/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 'No disponible')  # Valor por defecto si la clave no existe
