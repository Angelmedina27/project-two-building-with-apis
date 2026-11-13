import pytest

from watchlist import tmdb
from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
SAVE_FORM = 'hx-post="/watchlist/add/"'

DUNE_DETAILS = {
    "id": 693134,
    "title": "Dune: Part Two",
    "release_date": "2024-02-27",
    "poster_path": "/dune.jpg",
    "overview": "Paul Atreides unites with Chani and the Fremen.",
    "vote_average": 8.149,
    "genres": [{"id": 878, "name": "Science Fiction"}],
    "runtime": 166,
}


@pytest.fixture
def logged_in(client, user):
    client.force_login(user)
    return client


def _details_ok(user, make_item):
    return lambda media_type, tmdb_id: DUNE_DETAILS


def _details_race(user, make_item):
    # Another tab saves the same title while this request is still waiting on TMDB.
    def fetch(media_type, tmdb_id):
        make_item(tmdb_id=tmdb_id, media_type=media_type)
        return DUNE_DETAILS

    return fetch


def _raises(error):
    def factory(user, make_item):
        def fetch(media_type, tmdb_id):
            raise error

        return fetch

    return factory


@pytest.mark.parametrize(
    ("already_saved", "details", "shows", "save_button_remains", "items_after"),
    [
        pytest.param(False, _details_ok, ["Saved", "Edit"], False, 1, id="saved"),
        pytest.param(True, _details_ok, ["On watchlist"], False, 1, id="already-saved"),
        pytest.param(False, _details_race, ["On watchlist"], False, 1, id="race"),
        pytest.param(
            False,
            _raises(tmdb.TMDBNotFound("404")),
            ["not found on TMDB"],
            False,
            0,
            id="not-found",
        ),
        pytest.param(
            False,
            _raises(tmdb.TMDBUnavailable("HTTP 503")),
            ["Couldn't save, try again"],
            True,
            0,
            id="unavailable",
        ),
        pytest.param(
            False,
            _raises(tmdb.TMDBConfigError("missing key")),
            ["Couldn't save, try again"],
            True,
            0,
            id="config-error",
        ),
    ],
)
def test_save_returns_the_fragment_for_each_outcome(
    logged_in,
    user,
    make_item,
    monkeypatch,
    already_saved,
    details,
    shows,
    save_button_remains,
    items_after,
):
    if already_saved:
        make_item(tmdb_id=693134, media_type="movie")
    monkeypatch.setattr(tmdb, "get_details", details(user, make_item))

    response = logged_in.post(
        "/watchlist/add/", {"media_type": "movie", "tmdb_id": "693134"}, headers=HTMX
    )
    html = response.content.decode()

    # htmx only swaps 2xx responses, so every outcome is a 200 fragment, never an error page.
    assert response.status_code == 200
    assert "<html" not in html
    for text in shows:
        assert text in html
    assert (SAVE_FORM in html) is save_button_remains
    assert WatchlistItem.objects.filter(user=user).count() == items_after
    if "Edit" in shows:
        item = WatchlistItem.objects.get(user=user)
        assert f'href="/watchlist/{item.pk}/"' in html


@pytest.fixture
def fake_details(monkeypatch):
    calls = []

    def fetch(media_type, tmdb_id):
        calls.append((media_type, tmdb_id))
        return DUNE_DETAILS

    monkeypatch.setattr(tmdb, "get_details", fetch)
    return calls


def test_get_is_rejected(logged_in, fake_details):
    response = logged_in.get("/watchlist/add/?media_type=movie&tmdb_id=693134")
    assert response.status_code == 405
    assert not WatchlistItem.objects.exists()
    assert fake_details == []


def test_client_sent_tmdb_and_user_fields_are_ignored(logged_in, user, fake_details):
    logged_in.post(
        "/watchlist/add/",
        {
            "media_type": "movie",
            "tmdb_id": "693134",
            "title": "Totally Fake",
            "vote_average": "10",
            "poster_path": "/evil.jpg",
            "status": "watched",
            "user": "999",
        },
        headers=HTMX,
    )
    item = WatchlistItem.objects.get()
    assert item.user == user
    assert item.title == "Dune: Part Two"
    assert str(item.vote_average) == "8.1"
    assert item.poster_path == "/dune.jpg"
    assert item.status == "plan"


@pytest.mark.parametrize(
    "data",
    [
        {"media_type": "person", "tmdb_id": "693134"},
        {"media_type": "movie", "tmdb_id": "abc"},
        {"media_type": "movie", "tmdb_id": "0"},
        {"media_type": "movie", "tmdb_id": "-5"},
        {"media_type": "movie"},
        {},
    ],
)
def test_invalid_identity_is_a_bad_request_without_calling_tmdb(logged_in, fake_details, data):
    response = logged_in.post("/watchlist/add/", data, headers=HTMX)
    assert response.status_code == 400
    assert fake_details == []
    assert not WatchlistItem.objects.exists()


def test_non_htmx_save_redirects_back_to_the_search_with_a_message(
    logged_in, fake_details, monkeypatch
):
    reply = {"results": [], "page": 1, "total_pages": 0}
    monkeypatch.setattr(tmdb, "search", lambda *args: reply)
    response = logged_in.post(
        "/watchlist/add/",
        {"media_type": "movie", "tmdb_id": "693134"},
        headers={"Referer": "http://testserver/search/?q=dune&type=movie&page=2"},
        follow=True,
    )
    assert response.redirect_chain == [("/search/?q=dune&type=movie&page=2", 302)]
    assert "Saved “Dune: Part Two” to your watchlist." in response.content.decode()
    assert WatchlistItem.objects.count() == 1


@pytest.mark.parametrize(
    "referer",
    ["https://evil.example/search/?q=x", "http://testserver/watchlist/", ""],
)
def test_non_htmx_save_only_returns_to_a_same_site_search_page(logged_in, fake_details, referer):
    headers = {"Referer": referer} if referer else {}
    response = logged_in.post(
        "/watchlist/add/", {"media_type": "movie", "tmdb_id": "693134"}, headers=headers
    )
    assert response.status_code == 302
    assert response["Location"] == "/search/"


def test_non_htmx_failed_save_shows_a_retry_message(logged_in, monkeypatch):
    def fail(media_type, tmdb_id):
        raise tmdb.TMDBUnavailable("HTTP 503")

    monkeypatch.setattr(tmdb, "get_details", fail)
    response = logged_in.post(
        "/watchlist/add/", {"media_type": "movie", "tmdb_id": "693134"}, follow=True
    )
    assert "Couldn&#x27;t save that title right now. Please try again." in response.content.decode()
    assert not WatchlistItem.objects.exists()


def test_session_expired_htmx_save_redirects_to_login_and_back(client, fake_details):
    response = client.post(
        "/watchlist/add/",
        {"media_type": "movie", "tmdb_id": "693134"},
        headers={**HTMX, "HX-Current-URL": "http://testserver/search/?q=dune"},
    )
    assert response.status_code == 200
    assert response["HX-Redirect"] == "/accounts/login/?next=/search/%3Fq%3Ddune"
    assert fake_details == []
    assert not WatchlistItem.objects.exists()


def test_anonymous_plain_save_gets_a_standard_login_redirect(client, fake_details):
    response = client.post("/watchlist/add/", {"media_type": "movie", "tmdb_id": "693134"})
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")
    assert not WatchlistItem.objects.exists()
