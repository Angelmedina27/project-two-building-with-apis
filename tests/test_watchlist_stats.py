import re

import pytest

from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
S = WatchlistItem.Status


def stat(html, key):
    match = re.search(rf'data-stat="{key}">(\d+)<', html)
    assert match, f"no {key} stat in page"
    return int(match.group(1))


def test_summary_shows_total_and_per_status_counts_for_my_items_only(
    client, user, other_user, make_item
):
    make_item(tmdb_id=1, status=S.PLAN)
    make_item(tmdb_id=2, status=S.PLAN)
    make_item(tmdb_id=3, status=S.WATCHING)
    make_item(tmdb_id=4, status=S.WATCHED)
    make_item(user=other_user, tmdb_id=5, status=S.DROPPED)  # Not mine; must not count.

    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    assert stat(html, "total") == 4
    assert stat(html, "plan") == 2
    assert stat(html, "watching") == 1
    assert stat(html, "on_hold") == 0
    assert stat(html, "watched") == 1
    assert stat(html, "dropped") == 0


def test_summary_sits_between_heading_and_filter_form_in_life_cycle_order(client, user):
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    assert html.index("My Watchlist</h1>") < html.index('id="watchlist-stats"')
    assert html.index('id="watchlist-stats"') < html.index('role="search"')
    labels = ["Total saved", "Plan to watch", "Watching", "On hold", "Watched", "Dropped"]
    positions = [html.index(f">{label}<") for label in labels]
    assert positions == sorted(positions)
    # All six counts are children of one non-wrapping flex row, so they sit side by side.
    summary = html[html.index('id="watchlist-stats"') : html.index("</section>")]
    assert 'class="flex flex-row flex-nowrap' in summary
    assert summary.count('class="flex-1 min-w-max') == 6
    # An empty watchlist still shows the cards, all at zero.
    assert stat(html, "total") == 0


def test_summary_counts_ignore_the_current_filters(client, user, make_item):
    make_item(tmdb_id=1, status=S.PLAN)
    make_item(tmdb_id=2, status=S.DROPPED)
    client.force_login(user)

    html = client.get("/watchlist/?status=plan").content.decode()

    assert stat(html, "total") == 2
    assert stat(html, "dropped") == 1


def test_inline_status_change_refreshes_the_summary_out_of_band(client, user, make_item):
    item = make_item(status=S.PLAN)
    client.force_login(user)

    html = client.post(
        f"/watchlist/{item.pk}/status/", {"status": "watched"}, headers=HTMX
    ).content.decode()

    assert 'id="watchlist-stats" aria-label="Watchlist summary" hx-swap-oob="true"' in html
    assert stat(html, "plan") == 0
    assert stat(html, "watched") == 1


def test_full_page_summary_is_not_marked_out_of_band(client, user):
    client.force_login(user)
    assert "hx-swap-oob" not in client.get("/watchlist/").content.decode()
