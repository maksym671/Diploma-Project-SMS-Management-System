from django import template
from django.utils.translation import gettext as _gettext

register = template.Library()


@register.filter
def initials(name):
    """Two-letter initials from a display name, e.g. 'Anna Kowalska' → 'AK'."""
    parts = [part for part in (name or '').split() if part]
    if not parts:
        return '?'
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f'{parts[0][0]}{parts[-1][0]}'.upper()


@register.filter
def trans_db(value):
    """Translate a stored English catalog label; unknown values pass through."""
    if value in (None, ''):
        return value
    return _gettext(str(value))


@register.filter
def avatar_tone(name):
    """Stable 0–5 tone index so the same person keeps the same colour."""
    return sum(ord(char) for char in (name or '')) % 6
