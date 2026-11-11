import pytest

from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_signup_creates_user_logs_them_in_and_lands_on_watchlist(client, django_user_model):
    response = client.post(
        "/accounts/signup/",
        {"username": "carol", "password1": PASSWORD, "password2": PASSWORD},
    )

    assert django_user_model.objects.filter(username="carol").exists()
    assert response.headers.get("Location") == "/watchlist/"
    # The new user is already logged in: the protected watchlist loads instead of redirecting.
    assert client.get("/watchlist/").status_code == 200
