from django import forms

from .models import NOTES_MAX_LENGTH, WatchlistItem


class WatchlistItemForm(forms.ModelForm):
    """The user's own tracking fields; cached TMDB fields are never editable."""

    class Meta:
        model = WatchlistItem
        fields = ["status", "rating", "notes"]
        labels = {"rating": "My rating"}
        help_texts = {
            "rating": "A whole number from 1 to 10. Leave blank if you haven't rated it.",
            "notes": f"Up to {NOTES_MAX_LENGTH:,} characters.",
        }
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 10, "step": 1}),
            "notes": forms.Textarea(attrs={"rows": 5, "maxlength": NOTES_MAX_LENGTH}),
        }
