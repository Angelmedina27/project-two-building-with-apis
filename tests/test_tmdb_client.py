import logging

import pytest
import requests
import responses

from watchlist import tmdb

DETAILS_URL = "https://api.themoviedb.org/3/movie/693134"


@pytest.fixture(autouse=True)
def api_key(settings):
    settings.TMDB_API_KEY = "test-key"


@pytest.mark.parametrize(
    ("key", "mock", "expected", "logs_error"),
    [
        pytest.param("", None, tmdb.TMDBConfigError, True, id="missing-key"),
        pytest.param("test-key", {"status": 401}, tmdb.TMDBConfigError, True, id="401"),
        pytest.param("test-key", {"status": 404}, tmdb.TMDBNotFound, False, id="404"),
        pytest.param("test-key", {"status": 429}, tmdb.TMDBUnavailable, False, id="429"),
        pytest.param("test-key", {"status": 500}, tmdb.TMDBUnavailable, False, id="500"),
        pytest.param("test-key", {"status": 503}, tmdb.TMDBUnavailable, False, id="503"),
        pytest.param(
            "test-key", {"body": requests.Timeout()}, tmdb.TMDBUnavailable, False, id="timeout"
        ),
        pytest.param(
            "test-key",
            {"body": requests.ConnectionError()},
            tmdb.TMDBUnavailable,
            False,
            id="connection-error",
        ),
        pytest.param(
            "test-key",
            {"status": 200, "body": "<html>not json</html>"},
            tmdb.TMDBUnavailable,
            False,
            id="invalid-json",
        ),
    ],
)
@responses.activate
def test_failures_raise_the_tmdb_exception_hierarchy(
    settings, caplog, key, mock, expected, logs_error
):
    settings.TMDB_API_KEY = key
    if mock is not None:
        responses.get(DETAILS_URL, **mock)
    # With no mock registered, any HTTP call would surface as a connection error instead.

    with caplog.at_level(logging.ERROR, logger="watchlist.tmdb"):
        with pytest.raises(expected) as raised:
            tmdb.get_details("movie", 693134)

    # Config errors are a kind of "unavailable", and everything is a TMDBError.
    assert isinstance(raised.value, tmdb.TMDBError)
    assert issubclass(tmdb.TMDBConfigError, tmdb.TMDBUnavailable)
    # A missing key never makes a request at all.
    assert len(responses.calls) == (0 if mock is None else 1)
    # Only key problems are logged at error level, and the key itself is never logged.
    error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert bool(error_logs) is logs_error
    assert all("test-key" not in r.getMessage() for r in caplog.records)


MOVIE = {"id": 693134, "title": "Dune: Part Two", "release_date": "2024-02-27"}
SHOW = {"id": 1399, "name": "Dune: Prophecy", "first_air_date": "2024-11-17"}
PERSON = {"id": 1, "name": "Denis Villeneuve", "known_for_department": "Directing"}


@pytest.mark.parametrize(
    ("media_filter", "path", "tmdb_results", "expected"),
    [
        pytest.param(
            "all",
            "/search/multi",
            [
                {**MOVIE, "media_type": "movie"},
                {**PERSON, "media_type": "person"},
                {**SHOW, "media_type": "tv"},
            ],
            [(693134, "movie"), (1399, "tv")],
            id="all-drops-people",
        ),
        pytest.param("movie", "/search/movie", [MOVIE], [(693134, "movie")], id="movie"),
        pytest.param("tv", "/search/tv", [SHOW], [(1399, "tv")], id="tv"),
    ],
)
@responses.activate
def test_search_uses_the_endpoint_for_the_filter_and_returns_only_saveable_titles(
    media_filter, path, tmdb_results, expected
):
    responses.get(
        f"https://api.themoviedb.org/3{path}",
        json={"page": 2, "total_pages": 7, "results": tmdb_results},
    )

    data = tmdb.search("dune", media_filter, page=2)

    # Exactly one request, to the endpoint for this filter, with the query and page passed on.
    assert len(responses.calls) == 1
    request = responses.calls[0].request
    assert request.path_url.startswith(f"/3{path}?")
    assert request.params["query"] == "dune"
    assert request.params["page"] == "2"
    assert request.params["include_adult"] == "false"
    # Every result is a movie or TV show with its media type set; people are gone.
    assert [(r["id"], r["media_type"]) for r in data["results"]] == expected
    # TMDB's paging passes straight through.
    assert (data["page"], data["total_pages"]) == (2, 7)


@responses.activate
def test_get_details_returns_tmdb_json_and_sends_key_and_timeout(monkeypatch):
    responses.get(DETAILS_URL, json={"id": 693134, "title": "Dune: Part Two"})
    sent = {}
    real_get = requests.get

    def spy(*args, **kwargs):
        sent.update(kwargs)
        return real_get(*args, **kwargs)

    monkeypatch.setattr(tmdb.requests, "get", spy)

    assert tmdb.get_details("movie", 693134) == {"id": 693134, "title": "Dune: Part Two"}
    assert responses.calls[0].request.params["api_key"] == "test-key"
    assert sent["timeout"] == 10


@pytest.mark.parametrize(
    ("data", "title", "year"),
    [
        ({"title": "Dune: Part Two", "release_date": "2024-02-27"}, "Dune: Part Two", 2024),
        ({"name": "Shōgun", "first_air_date": "2024-02-27"}, "Shōgun", 2024),
        ({"title": "Untitled Project", "release_date": ""}, "Untitled Project", None),
        ({}, "(untitled)", None),
    ],
)
def test_title_and_year_helpers_handle_movies_tv_and_gaps(data, title, year):
    assert tmdb.title_of(data) == title
    assert tmdb.year_of(data) == year
