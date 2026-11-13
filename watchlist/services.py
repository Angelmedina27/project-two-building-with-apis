"""Shared watchlist logic used by the web views, the API, and the refresh command."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import tmdb
from .models import WatchlistItem


class AlreadyOnWatchlist(Exception):
    """The user has already saved this title."""


def _cached_fields(media_type, details):
    """Map a TMDB details reply to WatchlistItem's cached fields."""
    vote = details.get("vote_average")
    return {
        "title": tmdb.title_of(details),
        "year": tmdb.year_of(details),
        "poster_path": details.get("poster_path") or "",
        "overview": details.get("overview") or "",
        # TMDB reports 0 for titles nobody has voted on yet; treat that as no score.
        "vote_average": Decimal(str(round(vote, 1))) if vote else None,
        "genres": ", ".join(g["name"] for g in details.get("genres") or [] if g.get("name")),
        "runtime": (details.get("runtime") or None) if media_type == "movie" else None,
        "number_of_seasons": details.get("number_of_seasons") if media_type == "tv" else None,
        "cached_at": timezone.now(),
    }


def add_to_watchlist(user, media_type, tmdb_id, **user_fields):
    """Fetch a title's TMDB details and save it to ``user``'s watchlist.

    Only ``media_type`` and ``tmdb_id`` identify the title; TMDB values always come from
    TMDB, never the client. ``user_fields`` may set status, rating, and notes.

    Raises ``AlreadyOnWatchlist`` for a duplicate and lets ``tmdb.TMDBError`` propagate;
    either way nothing is saved.
    """
    existing = WatchlistItem.objects.filter(user=user, tmdb_id=tmdb_id, media_type=media_type)
    if existing.exists():
        raise AlreadyOnWatchlist
    details = tmdb.get_details(media_type, tmdb_id)
    try:
        # A savepoint keeps a lost race from breaking any surrounding transaction.
        with transaction.atomic():
            return WatchlistItem.objects.create(
                user=user,
                tmdb_id=tmdb_id,
                media_type=media_type,
                **_cached_fields(media_type, details),
                **user_fields,
            )
    except IntegrityError:
        # Another request (double click, second tab) saved it after the check above.
        if existing.exists():
            raise AlreadyOnWatchlist from None
        raise


def refresh_item(item):
    """Re-fetch ``item``'s TMDB details and update its cached fields and ``cached_at``.

    The user's own fields are left alone. ``tmdb.TMDBError`` propagates and nothing changes.
    """
    fields = _cached_fields(item.media_type, tmdb.get_details(item.media_type, item.tmdb_id))
    for name, value in fields.items():
        setattr(item, name, value)
    item.save(update_fields=[*fields, "updated_at"])
    return item
