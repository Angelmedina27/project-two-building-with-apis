from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

NOTES_MAX_LENGTH = 2000


class WatchlistItem(models.Model):
    """A title a user is tracking, with TMDB details cached locally so the list works offline."""

    class MediaType(models.TextChoices):
        MOVIE = "movie", "Movie"
        TV = "tv", "TV"

    class Status(models.TextChoices):
        PLAN = "plan", "Plan to watch"
        WATCHING = "watching", "Watching"
        WATCHED = "watched", "Watched"
        ON_HOLD = "on_hold", "On hold"
        DROPPED = "dropped", "Dropped"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_items"
    )

    # TMDB identity: movie and TV IDs are separate namespaces, so both fields are needed.
    tmdb_id = models.PositiveIntegerField()
    media_type = models.CharField(max_length=5, choices=MediaType.choices)

    # Cached TMDB details (never supplied by clients).
    title = models.CharField(max_length=255)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    overview = models.TextField(blank=True)
    vote_average = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    genres = models.CharField(max_length=255, blank=True, help_text="Comma-separated names.")
    runtime = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Minutes (movies).")
    number_of_seasons = models.PositiveSmallIntegerField(null=True, blank=True)
    cached_at = models.DateTimeField(default=timezone.now)

    # The user's own tracking fields.
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLAN)
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    notes = models.TextField(blank=True, validators=[MaxLengthValidator(NOTES_MAX_LENGTH)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tmdb_id", "media_type"], name="unique_title_per_user"
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.get_media_type_display()})"
