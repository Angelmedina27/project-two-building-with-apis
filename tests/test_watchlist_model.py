import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from watchlist.models import NOTES_MAX_LENGTH, WatchlistItem

pytestmark = pytest.mark.django_db


def test_a_user_can_save_a_title_once_but_other_users_can_save_it_too(make_item, other_user):
    make_item(tmdb_id=693134, media_type="movie")

    # The same TMDB ID as a TV show is a different title.
    make_item(tmdb_id=693134, media_type="tv")
    # Another user may save the same movie.
    make_item(user=other_user, tmdb_id=693134, media_type="movie")

    with pytest.raises(IntegrityError), transaction.atomic():
        make_item(tmdb_id=693134, media_type="movie")


def test_new_items_default_to_plan_to_watch_with_no_rating_or_notes(make_item):
    item = make_item()
    assert item.status == "plan"
    assert item.get_status_display() == "Plan to watch"
    assert item.rating is None
    assert item.notes == ""


@pytest.mark.parametrize("rating", [None, 1, 10])
def test_rating_accepts_blank_or_whole_numbers_from_1_to_10(make_item, rating):
    item = make_item(rating=rating)
    item.full_clean()


@pytest.mark.parametrize("rating", [0, 11])
def test_rating_outside_1_to_10_is_invalid(make_item, rating):
    item = make_item(rating=rating)
    with pytest.raises(ValidationError) as error:
        item.full_clean()
    assert "rating" in error.value.message_dict


def test_notes_up_to_the_limit_are_valid_and_longer_notes_are_not(make_item):
    item = make_item(notes="x" * NOTES_MAX_LENGTH)
    item.full_clean()

    item.notes = "x" * (NOTES_MAX_LENGTH + 1)
    with pytest.raises(ValidationError) as error:
        item.full_clean()
    assert "notes" in error.value.message_dict


def test_admin_lists_items_with_status_and_type_filters_and_title_search(admin_client, make_item):
    make_item(tmdb_id=1, title="Past Lives", status="watched")
    make_item(tmdb_id=2, title="Severance", media_type="tv")

    model_admin = admin.site._registry[WatchlistItem]
    assert list(model_admin.list_filter) == ["status", "media_type"]
    assert list(model_admin.search_fields) == ["title"]

    html = admin_client.get("/admin/watchlist/watchlistitem/?q=sever").content.decode()
    assert "Severance" in html
    assert "Past Lives" not in html

    html = admin_client.get(
        "/admin/watchlist/watchlistitem/?status__exact=watched"
    ).content.decode()
    assert "Past Lives" in html
    assert "Severance" not in html
