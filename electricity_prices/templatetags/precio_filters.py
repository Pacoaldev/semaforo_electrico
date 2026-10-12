"""
Filtros de plantilla personalizados para mostrar precios en formato español.
"""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def precio_es(value, decimales=5):
    """
    Formatea un precio en formato español (coma decimal, sin separador de miles).

    Ejemplos:
        0.19908  -> "0,19908"
        0.05455  -> "0,05455"
        1.5      -> "1,50000" (con decimales=5)

    Se puede indicar el número de decimales: {{ precio|precio_es:2 }}
    """
    if value is None or value == "":
        return ""

    try:
        numero = Decimal(str(value))
        decimales = int(decimales)
    except (InvalidOperation, ValueError, TypeError):
        return value

    return f"{numero:.{decimales}f}".replace(".", ",")
