from django import template
from decimal import Decimal, ROUND_HALF_UP

register = template.Library()


@register.filter
def br_money(value):
    """Formata número no padrão BR: 1.234.567,89"""
    try:
        val = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        formatted = f"{val:,.2f}"          # '1,234,567.89'
        integer_str, decimal_str = formatted.split('.')
        integer_str = integer_str.replace(',', '.')   # '1.234.567'
        return f"{integer_str},{decimal_str}"          # '1.234.567,89'
    except Exception:
        return value or '—'


@register.filter
def br_number(value):
    """Formata inteiro com ponto como milhar: 29.760"""
    try:
        return f"{int(value):,}".replace(',', '.')
    except Exception:
        return value or '—'
