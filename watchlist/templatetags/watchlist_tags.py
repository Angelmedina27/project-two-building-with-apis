import re

from django import template

register = template.Library()


@register.filter
def initials(title):
    """Up to two uppercase initials for a poster placeholder: "Dune: Part Two" -> "DP"."""
    words = re.findall(r"\w+", title or "")
    return "".join(word[0] for word in words[:2]).upper() or "?"
