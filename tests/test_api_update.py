import pytest
from rest_framework.test import APIClient

from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

TAMPERING = {
    "media_type": "tv",
    "tmdb_id": 1399,
    "title": "Totally Fake",
    "year": 1999,
    "poster_path": "/evil.jpg",
    "overview": "Fake.",
    "vote_average": "10.0",
    "genres": "Fake",
    "runtime": 1,
    "number_of_seasons": 9,
    "cached_at": "2000-01-01T00:00:00Z",
    "created_at": "2000-01-01T00:00:00Z",
    "id": 999,
}


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.parametrize("method", ["put", "patch"])
def test_updates_change_only_the_users_fields(api, make_item, method):
    item = make_item()
    before = WatchlistItem.objects.filter(pk=item.pk).values().get()
    url = f"/api/watchlist/{item.pk}/"

    response = getattr(api, method)(
        url,
        {"status": "watched", "rating": 8, "notes": "Loved the sandworms.", **TAMPERING},
        format="json",
    )

    assert response.status_code == 200
    after = WatchlistItem.objects.filter(pk=item.pk).values().get()
    assert (after["status"], after["rating"], after["notes"]) == (
        "watched",
        8,
        "Loved the sandworms.",
    )
    unchanged = set(before) - {"status", "rating", "notes", "updated_at"}
    assert {k: after[k] for k in unchanged} == {k: before[k] for k in unchanged}
    assert response.json()["media_type"] == "movie"
    assert response.json()["title"] == "Dune: Part Two"


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"rating": 0}, "rating"),
        ({"rating": 11}, "rating"),
        ({"rating": 7.5}, "rating"),
        ({"notes": "x" * 2001}, "notes"),
    ],
)
def test_invalid_rating_or_notes_is_a_400_with_field_errors(api, make_item, data, field):
    item = make_item(rating=5, notes="Original.")

    response = api.patch(f"/api/watchlist/{item.pk}/", data, format="json")

    assert response.status_code == 400
    assert field in response.json()
    item.refresh_from_db()
    assert (item.rating, item.notes) == (5, "Original.")


def test_rating_can_be_cleared(api, make_item):
    item = make_item(rating=5)
    response = api.patch(f"/api/watchlist/{item.pk}/", {"rating": None}, format="json")
    assert response.status_code == 200
    item.refresh_from_db()
    assert item.rating is None
