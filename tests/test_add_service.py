from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from watchlist import services, tmdb
from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

MOVIE_DETAILS = {
    "id": 693134,
    "title": "Dune: Part Two",
    "release_date": "2024-02-27",
    "poster_path": "/dune.jpg",
    "overview": "Paul Atreides unites with Chani and the Fremen.",
    "vote_average": 8.149,
    "genres": [{"id": 878, "name": "Science Fiction"}, {"id": 12, "name": "Adventure"}],
    "runtime": 166,
}
TV_DETAILS = {
    "id": 126308,
    "name": "Shōgun",
    "first_air_date": "2024-02-27",
    "poster_path": None,
    "overview": "",
    "vote_average": 8.6,
    "genres": [{"id": 18, "name": "Drama"}],
    "number_of_seasons": 2,
}

CACHED_FIELDS = [
    "tmdb_id",
    "media_type",
    "title",
    "year",
    "poster_path",
    "overview",
    "vote_average",
    "genres",
    "runtime",
    "number_of_seasons",
    "status",
]


@pytest.fixture
def fake_details(monkeypatch):
    """Replace the TMDB details call with canned movie and TV replies."""
    calls = []

    def fake(media_type, tmdb_id):
        calls.append((media_type, tmdb_id))
        return {"movie": MOVIE_DETAILS, "tv": TV_DETAILS}[media_type]

    monkeypatch.setattr(tmdb, "get_details", fake)
    return calls


@pytest.mark.parametrize(
    ("media_type", "tmdb_id", "expected"),
    [
        pytest.param(
            "movie",
            693134,
            {
                "tmdb_id": 693134,
                "media_type": "movie",
                "title": "Dune: Part Two",
                "year": 2024,
                "poster_path": "/dune.jpg",
                "overview": "Paul Atreides unites with Chani and the Fremen.",
                "vote_average": Decimal("8.1"),
                "genres": "Science Fiction, Adventure",
                "runtime": 166,
                "number_of_seasons": None,
                "status": "plan",
            },
            id="movie",
        ),
        pytest.param(
            "tv",
            126308,
            {
                "tmdb_id": 126308,
                "media_type": "tv",
                "title": "Shōgun",
                "year": 2024,
                "poster_path": "",
                "overview": "",
                "vote_average": Decimal("8.6"),
                "genres": "Drama",
                "runtime": None,
                "number_of_seasons": 2,
                "status": "plan",
            },
            id="tv",
        ),
    ],
)
def test_add_saves_every_cached_tmdb_field_with_status_plan(
    user, fake_details, media_type, tmdb_id, expected
):
    before = timezone.now()

    services.add_to_watchlist(user, media_type, tmdb_id)

    saved = list(WatchlistItem.objects.filter(user=user).values(*CACHED_FIELDS, "cached_at"))
    assert [{k: v for k, v in row.items() if k != "cached_at"} for row in saved] == [expected]
    assert fake_details == [(media_type, tmdb_id)]
    assert before <= saved[0]["cached_at"] <= timezone.now() + timedelta(seconds=1)


@pytest.mark.parametrize(
    "error",
    [
        tmdb.TMDBNotFound("TMDB has no such title."),
        tmdb.TMDBUnavailable("TMDB did not respond in time."),
        tmdb.TMDBConfigError("TMDB API key is missing."),
    ],
)
def test_tmdb_failure_raises_and_saves_nothing(user, monkeypatch, error):
    def fail(media_type, tmdb_id):
        raise error

    monkeypatch.setattr(tmdb, "get_details", fail)

    with pytest.raises(type(error)):
        services.add_to_watchlist(user, "movie", 693134)
    assert not WatchlistItem.objects.exists()


def test_duplicate_raises_already_on_watchlist_without_calling_tmdb(user, fake_details, make_item):
    make_item(tmdb_id=693134, media_type="movie")
    with pytest.raises(services.AlreadyOnWatchlist):
        services.add_to_watchlist(user, "movie", 693134)
    assert fake_details == []
    assert WatchlistItem.objects.count() == 1


def test_another_user_or_other_media_type_is_not_a_duplicate(
    user, other_user, fake_details, make_item
):
    make_item(user=other_user, tmdb_id=693134, media_type="movie")
    make_item(tmdb_id=693134, media_type="tv", title="Dune: Prophecy")
    item = services.add_to_watchlist(user, "movie", 693134)
    assert item.user == user and item.media_type == "movie"


def test_zero_vote_average_and_missing_fields_are_stored_as_blank(user, monkeypatch):
    monkeypatch.setattr(
        tmdb,
        "get_details",
        lambda media_type, tmdb_id: {"id": 1, "title": "Obscure", "vote_average": 0},
    )
    item = services.add_to_watchlist(user, "movie", 1)
    assert (item.vote_average, item.year, item.genres, item.runtime, item.poster_path) == (
        None,
        None,
        "",
        None,
        "",
    )
