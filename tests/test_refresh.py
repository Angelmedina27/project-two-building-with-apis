from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from watchlist import services, tmdb
from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

UPDATED_MOVIE = {
    "id": 693134,
    "title": "Dune: Part Two (Remastered)",
    "release_date": "2025-03-01",
    "poster_path": "/new-poster.jpg",
    "overview": "A new overview.",
    "vote_average": 8.47,
    "genres": [{"id": 18, "name": "Drama"}],
    "runtime": 170,
}


def test_refresh_item_updates_cached_fields_and_keeps_user_fields(user, make_item, monkeypatch):
    old = timezone.now() - timedelta(days=200)
    item = make_item(cached_at=old, status="watched", rating=9, notes="Loved the sandworms.")
    calls = []

    def fake(media_type, tmdb_id):
        calls.append((media_type, tmdb_id))
        return UPDATED_MOVIE

    monkeypatch.setattr(tmdb, "get_details", fake)
    before = timezone.now()

    services.refresh_item(item)

    item = WatchlistItem.objects.get(pk=item.pk)
    assert calls == [("movie", 693134)]
    assert (
        item.title,
        item.year,
        item.poster_path,
        item.overview,
        item.vote_average,
        item.genres,
        item.runtime,
    ) == (
        "Dune: Part Two (Remastered)",
        2025,
        "/new-poster.jpg",
        "A new overview.",
        Decimal("8.5"),
        "Drama",
        170,
    )
    assert item.cached_at >= before
    assert (item.status, item.rating, item.notes, item.user, item.tmdb_id) == (
        "watched",
        9,
        "Loved the sandworms.",
        user,
        693134,
    )


def test_command_refreshes_only_items_cached_more_than_150_days_ago(make_item, monkeypatch):
    now = timezone.now()
    stale = make_item(tmdb_id=1, title="Stale", cached_at=now - timedelta(days=151))
    fresh = make_item(tmdb_id=2, title="Fresh", cached_at=now - timedelta(days=149))
    calls = []

    def fake(media_type, tmdb_id):
        calls.append((media_type, tmdb_id))
        return {**UPDATED_MOVIE, "id": tmdb_id}

    monkeypatch.setattr(tmdb, "get_details", fake)

    call_command("refresh_tmdb", stdout=StringIO())

    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert calls == [("movie", 1)]
    assert stale.title == "Dune: Part Two (Remastered)"
    assert stale.cached_at >= now
    assert fresh.title == "Fresh"
    assert fresh.cached_at == now - timedelta(days=149)


def test_command_logs_and_skips_a_failing_item_and_prints_a_summary(make_item, monkeypatch, caplog):
    old = timezone.now() - timedelta(days=200)
    first = make_item(tmdb_id=1, title="First", cached_at=old)
    broken = make_item(tmdb_id=2, title="Broken", cached_at=old)
    last = make_item(tmdb_id=3, title="Last", cached_at=old)

    def fake(media_type, tmdb_id):
        if tmdb_id == 2:
            raise tmdb.TMDBUnavailable("TMDB returned HTTP 503.")
        return {**UPDATED_MOVIE, "id": tmdb_id}

    monkeypatch.setattr(tmdb, "get_details", fake)
    out = StringIO()

    call_command("refresh_tmdb", stdout=out)

    for item in (first, broken, last):
        item.refresh_from_db()
    assert first.title == last.title == "Dune: Part Two (Remastered)"
    assert (broken.title, broken.cached_at) == ("Broken", old)
    failures = [r for r in caplog.records if r.levelname in ("WARNING", "ERROR")]
    assert len(failures) == 1
    assert "Broken" in failures[0].getMessage()
    assert "Refreshed 2 item(s); 1 failed." in out.getvalue()


@pytest.mark.parametrize(
    "error",
    [
        tmdb.TMDBNotFound("TMDB has no such title."),
        tmdb.TMDBConfigError("TMDB API key is missing."),
    ],
)
def test_refresh_item_failure_changes_nothing(make_item, monkeypatch, error):
    old = timezone.now() - timedelta(days=200)
    item = make_item(cached_at=old)

    def fail(media_type, tmdb_id):
        raise error

    monkeypatch.setattr(tmdb, "get_details", fail)

    with pytest.raises(type(error)):
        services.refresh_item(item)
    item.refresh_from_db()
    assert (item.title, item.cached_at) == ("Dune: Part Two", old)


def test_command_skips_not_found_and_config_errors(make_item, monkeypatch):
    old = timezone.now() - timedelta(days=200)
    make_item(tmdb_id=1, cached_at=old)
    make_item(tmdb_id=2, cached_at=old)
    errors = {1: tmdb.TMDBNotFound("gone"), 2: tmdb.TMDBConfigError("no key")}

    def fail(media_type, tmdb_id):
        raise errors[tmdb_id]

    monkeypatch.setattr(tmdb, "get_details", fail)
    out = StringIO()

    call_command("refresh_tmdb", stdout=out)

    assert "Refreshed 0 item(s); 2 failed." in out.getvalue()


def test_command_with_nothing_stale_makes_no_tmdb_calls(make_item, monkeypatch):
    make_item()

    def fail(media_type, tmdb_id):
        raise AssertionError("TMDB should not be called")

    monkeypatch.setattr(tmdb, "get_details", fail)
    out = StringIO()

    call_command("refresh_tmdb", stdout=out)

    assert "Refreshed 0 item(s); 0 failed." in out.getvalue()


def test_command_refreshes_every_users_stale_items(user, other_user, make_item, monkeypatch):
    old = timezone.now() - timedelta(days=200)
    mine = make_item(cached_at=old)
    theirs = make_item(user=other_user, cached_at=old)
    monkeypatch.setattr(tmdb, "get_details", lambda media_type, tmdb_id: UPDATED_MOVIE)

    call_command("refresh_tmdb", stdout=StringIO())

    for item in (mine, theirs):
        item.refresh_from_db()
        assert item.title == "Dune: Part Two (Remastered)"
