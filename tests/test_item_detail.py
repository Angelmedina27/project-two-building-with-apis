import pytest

from watchlist.models import NOTES_MAX_LENGTH, WatchlistItem

pytestmark = pytest.mark.django_db


def test_detail_form_rejects_bad_input_and_saves_good_input(client, user, make_item):
    item = make_item(status=WatchlistItem.Status.PLAN, rating=None, notes="")
    client.force_login(user)
    url = f"/watchlist/{item.pk}/"

    # Rating out of range and notes too long: re-rendered with field errors, nothing saved.
    bad = client.post(
        url, {"status": "watched", "rating": "11", "notes": "x" * (NOTES_MAX_LENGTH + 1)}
    )
    html = bad.content.decode()
    assert bad.status_code == 200
    assert "Ensure this value is less than or equal to 10." in html
    assert f"Ensure this value has at most {NOTES_MAX_LENGTH} characters" in html
    item.refresh_from_db()
    assert (item.status, item.rating, item.notes) == ("plan", None, "")

    # A whole number is required.
    fractional = client.post(url, {"status": "watched", "rating": "7.5", "notes": ""})
    assert "Enter a whole number." in fractional.content.decode()

    # Valid input with a blank rating saves and redirects back with a success message.
    good = client.post(url, {"status": "watched", "rating": "", "notes": "Loved the sandworms."})
    assert good.status_code == 302
    assert good.url == url
    item.refresh_from_db()
    assert (item.status, item.rating, item.notes) == ("watched", None, "Loved the sandworms.")
    assert "Saved your changes" in client.get(url).content.decode()


def test_detail_page_shows_cached_tmdb_info_and_my_fields(client, user, make_item):
    item = make_item(status=WatchlistItem.Status.WATCHING, rating=8, notes="Rewatch in IMAX.")
    client.force_login(user)
    # The suite-wide network block fails this request if the page tries to reach TMDB.
    html = client.get(f"/watchlist/{item.pk}/").content.decode()

    assert "<h1" in html and "Dune: Part Two" in html
    assert "2024 · Movie" in html and "166 min" in html
    assert '<span class="badge badge-outline badge-sm">Science Fiction</span>' in html
    assert "Paul Atreides unites with the Fremen." in html
    assert "TMDB score 8.1/10" in html
    assert 'src="https://image.tmdb.org/t/p/w342/czembW0Rk1Ke7lCJGahbOhdCuhV.jpg"' in html
    assert '<option value="watching" selected>Watching</option>' in html
    assert 'name="rating" value="8"' in html
    assert "Rewatch in IMAX.</textarea>" in html


def test_tv_detail_shows_seasons_and_a_placeholder_without_a_poster(client, user, make_item):
    item = make_item(
        media_type="tv", title="Severance", poster_path="", runtime=None, number_of_seasons=2
    )
    client.force_login(user)
    html = client.get(f"/watchlist/{item.pk}/").content.decode()

    assert "2 seasons" in html
    assert "image.tmdb.org" not in html
    assert "><span>S</span>" in html


def test_detail_form_ignores_cached_tmdb_fields(client, user, make_item):
    item = make_item()
    client.force_login(user)
    client.post(
        f"/watchlist/{item.pk}/",
        {"status": "watched", "rating": "9", "notes": "", "title": "Hacked", "tmdb_id": "1"},
    )
    item.refresh_from_db()
    assert (item.title, item.tmdb_id, item.rating) == ("Dune: Part Two", 693134, 9)


def test_detail_page_has_a_remove_confirm_modal(client, user, make_item):
    item = make_item()
    client.force_login(user)
    html = client.get(f"/watchlist/{item.pk}/").content.decode()

    assert "showModal()" in html
    assert '<dialog id="remove-modal" class="modal"' in html
    assert f'<form method="post" action="/watchlist/{item.pk}/delete/">' in html


def test_someone_elses_item_is_not_found_on_view_and_edit(client, user, other_user, make_item):
    theirs = make_item(user=other_user, notes="private")
    client.force_login(user)

    assert client.get(f"/watchlist/{theirs.pk}/").status_code == 404
    edit = client.post(f"/watchlist/{theirs.pk}/", {"status": "dropped", "notes": "mine now"})
    assert edit.status_code == 404
    theirs.refresh_from_db()
    assert (theirs.status, theirs.notes) == ("plan", "private")


def test_anonymous_detail_and_delete_redirect_to_login(client, make_item):
    item = make_item()
    detail = client.get(f"/watchlist/{item.pk}/")
    assert detail.status_code == 302
    assert detail.url == f"/accounts/login/?next=/watchlist/{item.pk}/"

    delete = client.post(f"/watchlist/{item.pk}/delete/")
    assert delete.status_code == 302 and delete.url.startswith("/accounts/login/")
    assert WatchlistItem.objects.filter(pk=item.pk).exists()
