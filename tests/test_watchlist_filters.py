import pytest

from watchlist.filters import filter_watchlist
from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db


def titles(queryset):
    return sorted(item.title for item in queryset)


def test_q_status_and_type_combine_and_unknown_values_are_ignored(user, make_item):
    make_item(tmdb_id=1, title="The Bear", media_type="tv", status="watching")
    make_item(tmdb_id=2, title="Bear Story", media_type="movie", status="watching")
    make_item(tmdb_id=3, title="Teddy BEAR Picnic", media_type="tv", status="plan")
    make_item(tmdb_id=4, title="Severance", media_type="tv", status="watching")
    mine = WatchlistItem.objects.filter(user=user)

    # q is a case-insensitive substring; status and media_type narrow it further.
    combined = {"q": "bear", "status": "watching", "media_type": "tv"}
    assert titles(filter_watchlist(mine, combined)) == ["The Bear"]
    assert titles(filter_watchlist(mine, {"q": "  bEaR "})) == [
        "Bear Story",
        "Teddy BEAR Picnic",
        "The Bear",
    ]

    # Unknown values are ignored rather than matching nothing or raising.
    junk = {"status": "binged", "media_type": "game", "sort": "chaos"}
    assert titles(filter_watchlist(mine, junk)) == titles(mine)


def test_rating_sort_is_high_to_low_with_unrated_last(user, make_item):
    # Created in this order, so the default newest-first order would put unrated first.
    make_item(tmdb_id=1, title="Three", rating=3)
    make_item(tmdb_id=2, title="Nine", rating=9)
    make_item(tmdb_id=3, title="Seven", rating=7)
    make_item(tmdb_id=4, title="Unrated", rating=None)
    mine = WatchlistItem.objects.filter(user=user)

    result = [item.title for item in filter_watchlist(mine, {"sort": "rating"})]

    assert result == ["Nine", "Seven", "Three", "Unrated"]


def ordered(queryset, sort):
    return [item.title for item in filter_watchlist(queryset, {"sort": sort})]


def test_default_and_recent_sorts_are_newest_first(user, make_item):
    make_item(tmdb_id=1, title="First")
    make_item(tmdb_id=2, title="Second")
    make_item(tmdb_id=3, title="Third")
    mine = WatchlistItem.objects.filter(user=user)

    assert [item.title for item in filter_watchlist(mine, {})] == ["Third", "Second", "First"]
    assert ordered(mine, "recent") == ["Third", "Second", "First"]
    assert ordered(mine, "bogus") == ["Third", "Second", "First"]


def test_title_sort_is_a_to_z(user, make_item):
    make_item(tmdb_id=1, title="Severance")
    make_item(tmdb_id=2, title="Arrival")
    make_item(tmdb_id=3, title="Monk")
    mine = WatchlistItem.objects.filter(user=user)

    assert ordered(mine, "title") == ["Arrival", "Monk", "Severance"]


def test_year_sort_is_newest_first_with_unknown_years_last(user, make_item):
    make_item(tmdb_id=1, title="Old", year=1999)
    make_item(tmdb_id=2, title="Unknown", year=None)
    make_item(tmdb_id=3, title="New", year=2024)
    mine = WatchlistItem.objects.filter(user=user)

    assert ordered(mine, "year") == ["New", "Old", "Unknown"]


def test_score_sort_is_high_to_low_with_unscored_last(user, make_item):
    make_item(tmdb_id=1, title="Low", vote_average="5.5")
    make_item(tmdb_id=2, title="Unscored", vote_average=None)
    make_item(tmdb_id=3, title="High", vote_average="8.7")
    mine = WatchlistItem.objects.filter(user=user)

    assert ordered(mine, "score") == ["High", "Low", "Unscored"]


def test_status_and_type_filter_on_their_own(user, make_item):
    make_item(tmdb_id=1, title="Movie Watched", media_type="movie", status="watched")
    make_item(tmdb_id=2, title="Show Dropped", media_type="tv", status="dropped")
    make_item(tmdb_id=3, title="Show Watched", media_type="tv", status="watched")
    mine = WatchlistItem.objects.filter(user=user)

    assert titles(filter_watchlist(mine, {"status": "watched"})) == [
        "Movie Watched",
        "Show Watched",
    ]
    assert titles(filter_watchlist(mine, {"media_type": "tv"})) == [
        "Show Dropped",
        "Show Watched",
    ]
    assert titles(filter_watchlist(mine, {"status": "on_hold"})) == []


def test_filters_never_widen_the_given_queryset(user, other_user, make_item):
    make_item(tmdb_id=1, title="Mine")
    make_item(user=other_user, tmdb_id=1, title="Theirs")
    mine = WatchlistItem.objects.filter(user=user)

    assert titles(filter_watchlist(mine, {"sort": "title"})) == ["Mine"]


def test_filters_accept_a_querydict():
    from django.http import QueryDict

    from watchlist.filters import clean_filters

    params = QueryDict("q=+dune+&status=watching&media_type=movie&sort=score&page=3")
    assert clean_filters(params) == {
        "q": "dune",
        "status": "watching",
        "media_type": "movie",
        "sort": "score",
    }
