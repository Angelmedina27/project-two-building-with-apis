import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model

from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def is_logged_in(client):
    # The watchlist is protected, so a 200 means the session is authenticated.
    return client.get("/watchlist/").status_code == 200


def test_login_with_valid_credentials_lands_on_watchlist(client, user):
    response = client.post("/accounts/login/", {"username": "alice", "password": PASSWORD})
    assert response.headers.get("Location") == "/watchlist/"
    assert is_logged_in(client)


def test_login_with_wrong_password_shows_error(client, user):
    response = client.post("/accounts/login/", {"username": "alice", "password": "nope"})
    assert response.status_code == 200
    assert "correct username and password" in response.content.decode()
    assert not is_logged_in(client)


def test_logout_with_get_does_not_log_out(client, user):
    client.force_login(user)
    response = client.get("/accounts/logout/")
    assert response.status_code == 405
    assert is_logged_in(client)


def test_logout_with_post_logs_out_and_goes_to_login(client, user):
    client.force_login(user)
    response = client.post("/accounts/logout/")
    assert response.headers.get("Location") == "/accounts/login/"
    assert not is_logged_in(client)


def test_signup_with_mismatched_passwords_shows_error_and_creates_nothing(client):
    response = client.post(
        "/accounts/signup/",
        {"username": "carol", "password1": PASSWORD, "password2": "different-password-1"},
    )
    assert response.status_code == 200
    assert "didn’t match" in response.content.decode()
    assert not get_user_model().objects.filter(username="carol").exists()
    assert not is_logged_in(client)


def test_signup_page_sends_logged_in_user_to_watchlist(client, user):
    client.force_login(user)
    response = client.get("/accounts/signup/")
    assert response.headers.get("Location") == "/watchlist/"


def test_password_change_updates_password_and_keeps_user_logged_in(client, user):
    client.force_login(user)
    new_password = "a-brand-new-passphrase-42"
    response = client.post(
        "/accounts/password_change/",
        {"old_password": PASSWORD, "new_password1": new_password, "new_password2": new_password},
    )
    assert response.headers.get("Location") == "/accounts/password_change/done/"
    assert is_logged_in(client)

    user.refresh_from_db()
    assert user.check_password(new_password)


def test_password_change_rejects_wrong_old_password(client, user):
    client.force_login(user)
    response = client.post(
        "/accounts/password_change/",
        {
            "old_password": "wrong",
            "new_password1": "x-new-pass-123",
            "new_password2": "x-new-pass-123",
        },
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_custom_user_is_the_auth_model_and_registered_in_admin():
    user_model = get_user_model()
    assert user_model._meta.label == "accounts.User"
    assert admin.site.is_registered(user_model)


def test_admin_user_list_loads_for_superuser(client, django_user_model):
    superuser = django_user_model.objects.create_superuser("admin", "a@example.com", PASSWORD)
    client.force_login(superuser)
    assert client.get("/admin/accounts/user/").status_code == 200
