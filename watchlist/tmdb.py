"""The only module that talks to TMDB over HTTP.

Every failure leaves this module as a ``TMDBError`` subclass, so views and the API never
see raw ``requests`` exceptions.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.themoviedb.org/3"
TIMEOUT_SECONDS = 10


class TMDBError(Exception):
    """Base class for every TMDB failure views and the API are allowed to catch."""


class TMDBNotFound(TMDBError):
    """TMDB has no title with that ID (404)."""


class TMDBUnavailable(TMDBError):
    """TMDB can't be reached or answered badly; trying again later may work."""


class TMDBConfigError(TMDBUnavailable):
    """The API key is missing or rejected; logged at error level."""


def _get(path, params=None):
    """GET a TMDB endpoint and return its JSON, mapping every failure to a TMDBError."""
    api_key = (settings.TMDB_API_KEY or "").strip()
    if not api_key:
        logger.error("TMDB_API_KEY is not set; TMDB features are disabled.")
        raise TMDBConfigError("TMDB API key is missing.")

    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            params={"api_key": api_key, **(params or {})},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as error:
        raise TMDBUnavailable("TMDB did not respond in time.") from error
    except requests.RequestException as error:
        raise TMDBUnavailable("Could not connect to TMDB.") from error

    status = response.status_code
    if status == 401:
        logger.error("TMDB rejected the API key (401). Check TMDB_API_KEY.")
        raise TMDBConfigError("TMDB rejected the API key.")
    if status == 404:
        raise TMDBNotFound("TMDB has no such title.")
    if status != 200:
        # 429 rate limits, 5xx server trouble, and anything unexpected.
        raise TMDBUnavailable(f"TMDB returned HTTP {status}.")

    try:
        return response.json()
    except ValueError as error:
        raise TMDBUnavailable("TMDB sent a response that was not valid JSON.") from error


MEDIA_TYPES = ("movie", "tv")
# TMDB never serves more than 500 pages of search results.
MAX_SEARCH_PAGES = 500


def title_of(data):
    # Movies use "title"; TV shows use "name".
    return data.get("title") or data.get("name") or "(untitled)"


def year_of(data):
    """The release (movie) or first-air (TV) year as an int, or None."""
    date = data.get("release_date") or data.get("first_air_date") or ""
    return int(date[:4]) if date[:4].isdigit() else None


def search(query, media_filter="all", page=1):
    """Search TMDB for movies and/or TV shows.

    ``media_filter`` is "all", "movie", or "tv". Returns TMDB's ``page`` and ``total_pages``
    plus ``results`` that are all movies or TV shows with ``media_type`` set.
    """
    params = {"query": query, "page": page, "include_adult": "false"}
    if media_filter in MEDIA_TYPES:
        data = _get(f"/search/{media_filter}", params)
        # Single-type endpoints don't include media_type, so add it.
        results = [{**r, "media_type": media_filter} for r in data.get("results", [])]
    else:
        data = _get("/search/multi", params)
        # Multi-search also returns people, which can't be saved.
        results = [r for r in data.get("results", []) if r.get("media_type") in MEDIA_TYPES]
    return {
        "results": results,
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 0),
    }


def get_details(media_type, tmdb_id):
    """Return TMDB's full details for one movie or TV show."""
    return _get(f"/{media_type}/{tmdb_id}")
