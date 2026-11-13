import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from tests.conftest import PASSWORD
from watchlist import tmdb
from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


# --- Authentication -------------------------------------------------------------------------


def test_token_endpoint_exchanges_credentials_for_a_token(user):
    response = APIClient().post(
        "/api/auth/token/", {"username": "alice", "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    assert response.json() == {"token": Token.objects.get(user=user).key}


def test_token_endpoint_rejects_bad_credentials(user):
    response = APIClient().post(
        "/api/auth/token/", {"username": "alice", "password": "wrong"}, format="json"
    )
    assert response.status_code == 400
    assert "token" not in response.json()


def test_requests_work_with_a_token(user, make_item):
    make_item()
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.get("/api/watchlist/")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_requests_work_with_a_browser_session(client, user, make_item):
    make_item()
    client.force_login(user)
    response = client.get("/api/watchlist/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_the_browsable_api_renders_for_a_logged_in_user(client, user, make_item):
    make_item()
    client.force_login(user)
    response = client.get("/api/watchlist/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "Dune: Part Two" in response.content.decode()


def test_a_bad_token_is_refused(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
    assert client.get("/api/watchlist/").status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/watchlist/"),
        ("post", "/api/watchlist/"),
        ("get", "/api/watchlist/{pk}/"),
        ("put", "/api/watchlist/{pk}/"),
        ("patch", "/api/watchlist/{pk}/"),
        ("delete", "/api/watchlist/{pk}/"),
    ],
)
def test_anonymous_requests_are_refused(make_item, method, path):
    item = make_item()
    response = getattr(APIClient(), method)(
        path.format(pk=item.pk), {"status": "watched"}, format="json"
    )
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Token"
    item.refresh_from_db()
    assert item.status == "plan"
    assert WatchlistItem.objects.count() == 1


# --- List -----------------------------------------------------------------------------------


def test_list_is_paginated_ten_per_page(api, make_item):
    for n in range(12):
        make_item(tmdb_id=n + 1, title=f"Title {n}")

    first = api.get("/api/watchlist/").json()
    assert set(first) == {"count", "next", "previous", "results"}
    assert first["count"] == 12
    assert len(first["results"]) == 10
    assert first["previous"] is None
    assert first["next"].endswith("/api/watchlist/?page=2")

    second = api.get(first["next"]).json()
    assert len(second["results"]) == 2
    assert second["next"] is None
    assert second["previous"] is not None


def test_list_shows_only_my_items(api, make_item, other_user):
    mine = make_item()
    make_item(user=other_user, title="Someone Else's Movie")
    results = api.get("/api/watchlist/").json()["results"]
    assert [r["id"] for r in results] == [mine.pk]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "q=dune",
        "q=DUNE",
        "status=watched",
        "media_type=tv",
        "sort=title",
        "sort=rating",
        "sort=year",
        "sort=score",
        "status=bogus&media_type=bogus&sort=bogus",
        "q=the&media_type=movie&sort=rating",
    ],
)
def test_list_filters_match_the_website(client, api, user, make_item, query):
    make_item(tmdb_id=1, title="Dune: Part Two", year=2024, rating=9, vote_average="8.1")
    make_item(tmdb_id=2, title="The Bear", media_type="tv", year=2022, status="watching")
    make_item(tmdb_id=3, title="Arrival", year=2016, rating=7, status="watched", vote_average="7.6")
    make_item(tmdb_id=4, title="The Thing", year=1982, vote_average=None, status="watched")
    client.force_login(user)

    website = [item.pk for item in client.get(f"/watchlist/?{query}").context["items"]]
    api_ids = [r["id"] for r in api.get(f"/api/watchlist/?{query}").json()["results"]]

    assert api_ids == website


def test_detail_lookups_ignore_list_filters(api, make_item):
    item = make_item(status="plan")
    response = api.get(f"/api/watchlist/{item.pk}/?status=watched")
    assert response.status_code == 200


# --- Retrieve and delete; ownership ---------------------------------------------------------


def test_retrieve_returns_my_item(api, make_item):
    item = make_item()
    body = api.get(f"/api/watchlist/{item.pk}/").json()
    assert body["id"] == item.pk
    assert body["title"] == "Dune: Part Two"
    assert body["media_type"] == "movie"
    assert "user" not in body


def test_delete_removes_my_item(api, make_item):
    item = make_item()
    response = api.delete(f"/api/watchlist/{item.pk}/")
    assert response.status_code == 204
    assert not WatchlistItem.objects.exists()


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_another_users_item_is_not_found(api, make_item, other_user, method):
    theirs = make_item(user=other_user)
    response = getattr(api, method)(
        f"/api/watchlist/{theirs.pk}/", {"status": "watched"}, format="json"
    )
    assert response.status_code == 404
    theirs.refresh_from_db()
    assert theirs.status == "plan"


# --- Create input validation ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"tmdb_id": 693134}, "media_type"),
        ({"media_type": "movie"}, "tmdb_id"),
        ({"media_type": "person", "tmdb_id": 693134}, "media_type"),
        ({"media_type": "movie", "tmdb_id": "abc"}, "tmdb_id"),
        ({"media_type": "movie", "tmdb_id": -5}, "tmdb_id"),
        ({"media_type": "movie", "tmdb_id": 693134, "rating": 11}, "rating"),
        ({"media_type": "movie", "tmdb_id": 693134, "status": "bogus"}, "status"),
    ],
)
def test_invalid_create_input_is_a_400_without_calling_tmdb(api, monkeypatch, data, field):
    def fail(*args):
        raise AssertionError("TMDB must not be called for invalid input")

    monkeypatch.setattr(tmdb, "get_details", fail)
    response = api.post("/api/watchlist/", data, format="json")
    assert response.status_code == 400
    assert field in response.json()
    assert not WatchlistItem.objects.exists()
