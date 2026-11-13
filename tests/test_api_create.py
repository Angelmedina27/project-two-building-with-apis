import pytest
from rest_framework.test import APIClient

from watchlist import tmdb
from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

DUNE_DETAILS = {
    "id": 693134,
    "title": "Dune: Part Two",
    "release_date": "2024-02-27",
    "poster_path": "/dune.jpg",
    "overview": "Paul Atreides unites with Chani and the Fremen.",
    "vote_average": 8.149,
    "genres": [{"id": 878, "name": "Science Fiction"}, {"id": 12, "name": "Adventure"}],
    "runtime": 166,
}


@pytest.fixture
def api(user):
    # Return 500 responses instead of re-raising, so tests see what an API caller sees.
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    return client


def test_create_from_identity_only_fills_tmdb_fields_on_the_server(api, user, monkeypatch):
    calls = []

    def fetch(media_type, tmdb_id):
        calls.append((media_type, tmdb_id))
        return DUNE_DETAILS

    monkeypatch.setattr(tmdb, "get_details", fetch)

    response = api.post(
        "/api/watchlist/",
        {
            "media_type": "movie",
            "tmdb_id": 693134,
            "rating": 9,
            # A client can't fake TMDB data or the owner.
            "title": "Totally Fake",
            "vote_average": "10.0",
            "poster_path": "/evil.jpg",
            "user": 999,
        },
        format="json",
    )

    assert response.status_code == 201
    assert calls == [("movie", 693134)]
    body = response.json()
    assert body["title"] == "Dune: Part Two"
    assert body["year"] == 2024
    assert body["poster_path"] == "/dune.jpg"
    assert body["vote_average"] == "8.1"
    assert body["genres"] == "Science Fiction, Adventure"
    assert body["runtime"] == 166
    assert body["status"] == "plan"
    assert body["rating"] == 9
    item = WatchlistItem.objects.get()
    assert item.user == user
    assert item.title == "Dune: Part Two"
    assert body["id"] == item.pk


def _already_saved(make_item):
    make_item(tmdb_id=693134, media_type="movie")


def _raise(error):
    def fetch(media_type, tmdb_id):
        raise error

    return fetch


@pytest.mark.parametrize(
    ("setup", "fetch", "status", "message", "items_after"),
    [
        pytest.param(
            _already_saved,
            lambda media_type, tmdb_id: DUNE_DETAILS,
            400,
            "already on your watchlist",
            1,
            id="duplicate",
        ),
        pytest.param(
            None, _raise(tmdb.TMDBNotFound("404")), 400, "No movie with TMDB ID", 0, id="not-found"
        ),
        pytest.param(
            None,
            _raise(tmdb.TMDBUnavailable("HTTP 503")),
            503,
            "TMDB is unavailable",
            0,
            id="unavailable",
        ),
        pytest.param(
            None,
            _raise(tmdb.TMDBConfigError("missing key")),
            503,
            "TMDB is unavailable",
            0,
            id="config-error",
        ),
    ],
)
def test_create_failures_return_clear_errors_and_save_nothing(
    api, user, make_item, monkeypatch, setup, fetch, status, message, items_after
):
    if setup:
        setup(make_item)
    monkeypatch.setattr(tmdb, "get_details", fetch)

    response = api.post("/api/watchlist/", {"media_type": "movie", "tmdb_id": 693134})

    assert response.status_code == status
    assert response["Content-Type"] == "application/json"
    assert message in str(response.json())
    # No technical details (exception text) leak to the client.
    assert "missing key" not in str(response.json())
    assert "HTTP 503" not in str(response.json())
    assert WatchlistItem.objects.filter(user=user).count() == items_after
