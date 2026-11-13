import pytest

from watchlist.models import WatchlistItem

pytestmark = pytest.mark.django_db


def test_delete_is_post_only_and_limited_to_my_items(client, user, other_user, make_item):
    mine = make_item(title="Dune: Part Two")
    theirs = make_item(user=other_user, title="Bob's Movie")
    client.force_login(user)

    # GET never deletes.
    assert client.get(f"/watchlist/{mine.pk}/delete/").status_code == 405
    assert WatchlistItem.objects.filter(pk=mine.pk).exists()

    # Someone else's item is "not found" and stays put.
    assert client.post(f"/watchlist/{theirs.pk}/delete/").status_code == 404
    assert WatchlistItem.objects.filter(pk=theirs.pk).exists()

    # POST on my own item removes it and returns to the watchlist with a message.
    response = client.post(f"/watchlist/{mine.pk}/delete/", follow=True)
    assert response.redirect_chain == [("/watchlist/", 302)]
    assert not WatchlistItem.objects.filter(pk=mine.pk).exists()
    assert "Removed “Dune: Part Two” from your watchlist." in response.content.decode()
