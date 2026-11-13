from urllib.parse import parse_qs, urlsplit

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from watchlist import tmdb

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}

DUNE = {
    "id": 693134,
    "media_type": "movie",
    "title": "Dune: Part Two",
    "release_date": "2024-02-27",
    "poster_path": "/dune.jpg",
    "vote_average": 8.149,
    "overview": "Paul Atreides unites with Chani and the Fremen.",
}
SHOGUN = {
    "id": 126308,
    "media_type": "tv",
    "name": "Shōgun",
    "first_air_date": "2024-02-27",
    "poster_path": None,
    "vote_average": 8.6,
    "overview": "",
}


@pytest.fixture
def fake_search(monkeypatch):
    """Replace the TMDB search call; returns the list of calls and lets tests set the reply."""

    class Fake:
        calls = []
        reply = {"results": [DUNE, SHOGUN], "page": 1, "total_pages": 1}
        error = None

        def __call__(self, query, media_filter="all", page=1):
            self.calls.append((query, media_filter, page))
            if self.error:
                raise self.error
            return self.reply

    fake = Fake()
    fake.calls = []
    monkeypatch.setattr(tmdb, "search", fake)
    return fake


@pytest.fixture
def logged_in(client, user):
    client.force_login(user)
    return client


def test_anonymous_search_redirects_to_login(client):
    response = client.get("/search/?q=dune")
    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/?next=/search/%3Fq%3Ddune"


def test_anonymous_htmx_search_gets_hx_redirect(client):
    response = client.get("/search/?q=dune", headers=HTMX)
    assert response.status_code == 200
    assert response["HX-Redirect"] == "/accounts/login/?next=/search/%3Fq%3Ddune"


@pytest.mark.parametrize("url", ["/search/", "/search/?q=", "/search/?q=%20%20%20"])
def test_empty_or_whitespace_query_shows_prompt_without_calling_tmdb(logged_in, fake_search, url):
    response = logged_in.get(url)
    assert response.status_code == 200
    assert "Type a title above and press Search." in response.content.decode()
    assert fake_search.calls == []


def test_results_show_poster_title_type_year_score_and_overview(logged_in, fake_search):
    html = logged_in.get("/search/?q=dune").content.decode()

    assert "Dune: Part Two" in html
    assert "Shōgun" in html
    assert ">Movie<" in html and ">TV<" in html
    assert "2024" in html
    assert "★ 8.1" in html and "★ 8.6" in html
    assert "Paul Atreides unites with Chani and the Fremen." in html
    assert "No overview available." in html
    assert 'src="https://image.tmdb.org/t/p/w185/dune.jpg"' in html
    assert "<span>S</span>" in html  # Shōgun has no poster, so it gets the initials placeholder.


def test_query_is_trimmed_and_type_and_page_are_passed_to_tmdb(logged_in, fake_search):
    logged_in.get("/search/?q=%20dune%20&type=tv&page=3")
    assert fake_search.calls == [("dune", "tv", 3)]


@pytest.mark.parametrize("page", ["abc", "0", "-2", "501", ""])
def test_invalid_page_falls_back_to_page_one(logged_in, fake_search, page):
    response = logged_in.get(f"/search/?q=dune&page={page}")
    assert response.status_code == 200
    assert fake_search.calls == [("dune", "all", 1)]


def test_unknown_type_falls_back_to_all(logged_in, fake_search):
    logged_in.get("/search/?q=dune&type=person")
    assert fake_search.calls == [("dune", "all", 1)]


def test_no_results_shows_friendly_message(logged_in, fake_search):
    fake_search.reply = {"results": [], "page": 1, "total_pages": 0}
    response = logged_in.get("/search/?q=zzzzqqq")
    assert response.status_code == 200
    assert "No movies or TV shows match “zzzzqqq”." in response.content.decode()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (tmdb.TMDBUnavailable("TMDB returned HTTP 503."), "TMDB isn't responding right now."),
        (tmdb.TMDBConfigError("TMDB rejected the API key."), "Search isn't set up right now"),
        (tmdb.TMDBNotFound("TMDB has no such title."), "TMDB isn't responding right now."),
    ],
)
def test_tmdb_errors_show_a_friendly_alert_with_200(logged_in, fake_search, error, message):
    fake_search.error = error
    for headers in ({}, HTMX):
        response = logged_in.get("/search/?q=dune", headers=headers)
        html = response.content.decode()
        assert response.status_code == 200
        assert message in html
        assert 'role="alert"' in html
        # No technical details leak to the page.
        assert str(error) not in html
        assert "API key" not in html


def test_htmx_request_returns_only_the_results_fragment(logged_in, fake_search):
    response = logged_in.get("/search/?q=dune", headers=HTMX)
    html = response.content.decode()

    assert "Dune: Part Two" in html
    assert "<html" not in html
    assert 'id="search-results"' not in html
    assert "not endorsed or certified by TMDB" not in html
    assert "HX-Request" in response["Vary"]


def test_normal_request_returns_full_page_with_form_filled_in(logged_in, fake_search):
    html = logged_in.get("/search/?q=dune&type=movie").content.decode()

    assert "<html" in html
    assert 'id="search-results"' in html
    assert 'value="dune"' in html
    assert '<option value="movie" selected>' in html
    # The form works without JavaScript and htmx pushes its GET URL into history.
    assert 'method="get" action="/search/"' in html
    assert 'hx-push-url="true"' in html
    assert "not endorsed or certified by TMDB" in html


def test_history_restore_request_gets_the_full_page(logged_in, fake_search):
    headers = {**HTMX, "HX-History-Restore-Request": "true"}
    html = logged_in.get("/search/?q=dune", headers=headers).content.decode()
    assert "<html" in html


def _page_links(html):
    """Map 'previous'/'next' to the query params of each pagination link."""
    links = {}
    for label, marker in (("previous", "« Previous"), ("next", "Next »")):
        before = html.split(marker)[0]
        tag = before[before.rfind("<") :]
        if tag.startswith("<a "):
            href = tag.split('href="')[1].split('"')[0].replace("&amp;", "&")
            links[label] = {k: v[0] for k, v in parse_qs(urlsplit(href).query).items()}
    return links


def test_paging_shows_page_x_of_y_with_links_that_keep_query_and_type(logged_in, fake_search):
    fake_search.reply = {"results": [DUNE], "page": 2, "total_pages": 7}
    html = logged_in.get("/search/?q=dune&type=movie&page=2").content.decode()

    assert "Page 2 of 7" in html
    links = _page_links(html)
    assert links["previous"] == {"q": "dune", "type": "movie", "page": "1"}
    assert links["next"] == {"q": "dune", "type": "movie", "page": "3"}


def test_first_and_last_pages_disable_the_missing_direction(logged_in, fake_search):
    fake_search.reply = {"results": [DUNE], "page": 1, "total_pages": 3}
    assert set(_page_links(logged_in.get("/search/?q=dune").content.decode())) == {"next"}

    fake_search.reply = {"results": [DUNE], "page": 3, "total_pages": 3}
    html = logged_in.get("/search/?q=dune&page=3").content.decode()
    assert set(_page_links(html)) == {"previous"}


def test_total_pages_are_capped_at_tmdbs_limit(logged_in, fake_search):
    fake_search.reply = {"results": [DUNE], "page": 500, "total_pages": 1234}
    html = logged_in.get("/search/?q=the&page=500").content.decode()
    assert "Page 500 of 500" in html
    assert "next" not in _page_links(html)


def test_single_page_of_results_has_no_pager(logged_in, fake_search):
    html = logged_in.get("/search/?q=dune").content.decode()
    assert "Page 1 of 1" not in html


def _card(html, title):
    """The HTML of the search result card with this title."""
    cards = html.split("<li ")[1:]
    return next(card for card in cards if title in card)


def _watchlist_queries(queries):
    return [q["sql"] for q in queries if "watchlist_watchlistitem" in q["sql"]]


def test_already_saved_results_show_on_watchlist_using_one_query(
    logged_in, fake_search, user, other_user, make_item
):
    dune_tv_namesake = {**SHOGUN, "id": DUNE["id"], "name": "Dune: Prophecy"}
    severance = {**SHOGUN, "id": 95396, "name": "Severance"}
    make_item(tmdb_id=DUNE["id"], media_type="movie")  # alice saved the Dune movie...
    make_item(user=other_user, tmdb_id=SHOGUN["id"], media_type="tv")  # ...bob saved Shōgun.

    fake_search.reply = {"results": [DUNE, SHOGUN, dune_tv_namesake], "page": 1, "total_pages": 1}
    with CaptureQueriesContext(connection) as three_results:
        html = logged_in.get("/search/?q=dune").content.decode()

    saved_card = _card(html, "Dune: Part Two")
    assert "On watchlist" in saved_card
    assert 'hx-post="/watchlist/add/"' not in saved_card
    # Another user's save and a TV show sharing the movie's TMDB id are still saveable.
    for title in ("Shōgun", "Dune: Prophecy"):
        card = _card(html, title)
        assert "On watchlist" not in card
        assert 'hx-post="/watchlist/add/"' in card

    # Marking costs one query no matter how many results there are.
    fake_search.reply = {
        "results": [DUNE, SHOGUN, dune_tv_namesake, severance] * 5,
        "page": 1,
        "total_pages": 1,
    }
    with CaptureQueriesContext(connection) as twenty_results:
        logged_in.get("/search/?q=dune")
    assert len(_watchlist_queries(three_results.captured_queries)) == 1
    assert len(_watchlist_queries(twenty_results.captured_queries)) == 1
