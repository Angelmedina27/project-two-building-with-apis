from datetime import timedelta

import pytest
from django.utils import timezone

from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db


def test_watchlist_lists_only_my_items_newest_first(client, user, other_user, make_item):
    now = timezone.now()
    older = make_item(tmdb_id=1, title="Past Lives")
    newer = make_item(tmdb_id=2, media_type="tv", title="Severance")
    make_item(user=other_user, tmdb_id=3, title="Bob's Secret Movie")
    WatchlistItem.objects.filter(pk=older.pk).update(created_at=now - timedelta(days=2))
    WatchlistItem.objects.filter(pk=newer.pk).update(created_at=now - timedelta(days=1))

    client.force_login(user)
    # The suite-wide network block fails this request if the page tries to reach TMDB.
    response = client.get("/watchlist/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Severance" in html
    assert "Past Lives" in html
    assert html.index("Severance") < html.index("Past Lives")
    assert "Bob&#x27;s Secret Movie" not in html and "Bob's Secret Movie" not in html


def test_posters_use_tmdb_w185_image_or_an_initials_placeholder(client, user, make_item):
    make_item(tmdb_id=1, title="Dune: Part Two", poster_path="")
    make_item(tmdb_id=2, title="the bear", media_type="tv", poster_path="")
    make_item(tmdb_id=3, title="Severance", media_type="tv", poster_path="/sev.jpg")

    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    # Items without a poster path get a placeholder with up to two uppercase initials.
    assert ">DP<" in html
    assert ">TB<" in html
    # Items with a poster path are hotlinked from TMDB at w185, and only those.
    assert 'src="https://image.tmdb.org/t/p/w185/sev.jpg"' in html
    assert html.count("image.tmdb.org") == 1


def test_empty_watchlist_shows_empty_state_with_search_link(client, user, other_user, make_item):
    make_item(user=other_user)  # Someone else's item must not count as mine.
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    assert "Your watchlist is empty." in html
    assert '<a href="/search/" class="btn btn-primary' in html
    assert "<table" not in html


def test_rows_link_to_the_detail_page(client, user, make_item):
    item = make_item()
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()
    assert f'href="/watchlist/{item.pk}/"' in html


def test_broken_poster_images_swap_to_the_placeholder(client, user, make_item):
    make_item(title="Severance", poster_path="/sev.jpg")
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    # The placeholder is rendered hidden behind the image, and the image reveals it on error.
    assert 'onerror="this.hidden = true; this.nextElementSibling.hidden = false;"' in html
    assert 'hidden aria-hidden="true"><span>S</span>' in html


def test_detail_url_is_scoped_to_the_owner(client, user, other_user, make_item):
    mine = make_item()
    theirs = make_item(user=other_user)
    client.force_login(user)

    assert client.get(f"/watchlist/{mine.pk}/").status_code == 200
    assert client.get(f"/watchlist/{theirs.pk}/").status_code == 404
