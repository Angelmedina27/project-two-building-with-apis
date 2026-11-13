"""Watchlist search, filter, and sort shared by the web list and the API list."""

from django.db.models import F

from .models import WatchlistItem

DEFAULT_SORT = "recent"

# Whitelisted sort orders: URL value -> (label, ordering). Ties fall back to newest first.
SORTS = {
    "recent": ("Recently added", ["-created_at", "-pk"]),
    "title": ("Title A–Z", ["title", "-created_at"]),
    "rating": ("My rating", [F("rating").desc(nulls_last=True), "-created_at"]),
    "year": ("Year (newest)", [F("year").desc(nulls_last=True), "-created_at"]),
    "score": ("TMDB score", [F("vote_average").desc(nulls_last=True), "-created_at"]),
}


def clean_filters(params):
    """The recognized filter values from ``params``; anything unknown falls back to the default."""
    status = params.get("status", "")
    media_type = params.get("media_type", "")
    sort = params.get("sort", "")
    return {
        "q": params.get("q", "").strip(),
        "status": status if status in WatchlistItem.Status.values else "",
        "media_type": media_type if media_type in WatchlistItem.MediaType.values else "",
        "sort": sort if sort in SORTS else DEFAULT_SORT,
    }


def filter_watchlist(queryset, params):
    """Apply ``q``, ``status``, ``media_type``, and ``sort`` from ``params`` to ``queryset``.

    ``queryset`` must already be limited to the requesting user.
    """
    filters = clean_filters(params)
    if filters["q"]:
        queryset = queryset.filter(title__icontains=filters["q"])
    if filters["status"]:
        queryset = queryset.filter(status=filters["status"])
    if filters["media_type"]:
        queryset = queryset.filter(media_type=filters["media_type"])
    _, ordering = SORTS[filters["sort"]]
    return queryset.order_by(*ordering)
