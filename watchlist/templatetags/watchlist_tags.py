import re
from pathlib import Path

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def versioned_static(path):
    """A static URL stamped with the file's modified time, so browsers fetch each rebuild."""
    found = finders.find(path)
    if not found:
        return static(path)
    return f"{static(path)}?v={int(Path(found).stat().st_mtime)}"


@register.filter
def initials(title):
    """Up to two uppercase initials for a poster placeholder: "Dune: Part Two" -> "DP"."""
    words = re.findall(r"\w+", title or "")
    return "".join(word[0] for word in words[:2]).upper() or "?"
