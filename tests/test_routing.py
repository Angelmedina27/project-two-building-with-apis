import pytest

from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def location(response):
    return response.headers.get("Location")


def test_redirects_follow_login_state_and_return_after_login(client, user):
    # A visitor is sent from home to login, and from a protected page to login with `next`.
    assert location(client.get("/")) == "/accounts/login/"
    assert location(client.get("/watchlist/")) == "/accounts/login/?next=/watchlist/"
    assert (
        location(client.get("/accounts/password_change/"))
        == "/accounts/login/?next=/accounts/password_change/"
    )

    # Logging in from that link returns the user to the page they asked for.
    response = client.post(
        "/accounts/login/",
        {"username": "alice", "password": PASSWORD, "next": "/accounts/password_change/"},
    )
    assert location(response) == "/accounts/password_change/"

    # Once logged in, home goes to the watchlist, which loads.
    assert location(client.get("/")) == "/watchlist/"
    assert client.get("/watchlist/").status_code == 200
