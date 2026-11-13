"""Keep cached TMDB details within TMDB's 6-month caching limit.

Run manually or from an OS scheduler: ``uv run python manage.py refresh_tmdb``.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from watchlist import services, tmdb
from watchlist.models import WatchlistItem

logger = logging.getLogger(__name__)

# TMDB allows caching for at most 6 months; 150 days leaves a safety margin.
MAX_CACHE_AGE = timedelta(days=150)


class Command(BaseCommand):
    help = "Refresh cached TMDB details older than 150 days."

    def handle(self, *args, **options):
        cutoff = timezone.now() - MAX_CACHE_AGE
        refreshed = failed = 0
        for item in WatchlistItem.objects.filter(cached_at__lt=cutoff).order_by("pk"):
            try:
                services.refresh_item(item)
            except tmdb.TMDBError as error:
                failed += 1
                logger.warning(
                    "Could not refresh %s %s (%r, item %s): %s",
                    item.media_type,
                    item.tmdb_id,
                    item.title,
                    item.pk,
                    error,
                )
            else:
                refreshed += 1
        self.stdout.write(f"Refreshed {refreshed} item(s); {failed} failed.")
