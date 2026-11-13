import pytest

from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


def test_status_change_saves_and_returns_the_row_marked_saved(client, user, make_item):
    item = make_item(status=WatchlistItem.Status.PLAN)
    client.force_login(user)

    response = client.post(f"/watchlist/{item.pk}/status/", {"status": "watching"}, headers=HTMX)
    html = response.content.decode()

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.status == WatchlistItem.Status.WATCHING
    # Only the re-rendered row comes back, with the new status selected and a confirmation.
    assert html.lstrip().startswith(f'<tr id="item-{item.pk}"')
    assert '<option value="watching" selected>' in html
    assert "Saved" in html
    assert "<html" not in html

    # An unknown code is rejected and the stored status is left alone.
    bad = client.post(f"/watchlist/{item.pk}/status/", {"status": "binged"}, headers=HTMX)
    assert bad.status_code == 400
    item.refresh_from_db()
    assert item.status == WatchlistItem.Status.WATCHING


def test_status_endpoint_is_post_only(client, user, make_item):
    item = make_item()
    client.force_login(user)
    assert client.get(f"/watchlist/{item.pk}/status/", headers=HTMX).status_code == 405


def test_status_change_on_someone_elses_item_is_not_found(client, user, other_user, make_item):
    theirs = make_item(user=other_user)
    client.force_login(user)

    response = client.post(f"/watchlist/{theirs.pk}/status/", {"status": "dropped"}, headers=HTMX)

    assert response.status_code == 404
    theirs.refresh_from_db()
    assert theirs.status == WatchlistItem.Status.PLAN


def test_expired_session_status_change_redirects_to_login_and_back(client, make_item):
    item = make_item()
    headers = {**HTMX, "HX-Current-URL": "http://testserver/watchlist/?status=plan"}

    response = client.post(f"/watchlist/{item.pk}/status/", {"status": "watched"}, headers=headers)

    assert response.status_code == 200
    assert response["HX-Redirect"] == "/accounts/login/?next=/watchlist/%3Fstatus%3Dplan"
    item.refresh_from_db()
    assert item.status == WatchlistItem.Status.PLAN


def test_watchlist_rows_have_a_status_dropdown_that_posts_on_change(client, user, make_item):
    item = make_item(status=WatchlistItem.Status.ON_HOLD)
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()

    assert f'hx-post="/watchlist/{item.pk}/status/" hx-trigger="change"' in html
    assert f'hx-target="#item-{item.pk}" hx-swap="outerHTML"' in html
    assert '<option value="on_hold" selected>On hold</option>' in html
    # The confirmation only appears after a change.
    assert "Saved" not in html
