import socket

import pytest

PASSWORD = "correct-horse-battery-staple"


def _blocked(*args, **kwargs):
    raise RuntimeError("Network access is blocked in tests; mock the call with `responses`.")


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail any test that tries to resolve a host or open a real socket connection."""
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)


@pytest.fixture(autouse=True)
def fast_password_hashing(settings):
    # The production PBKDF2 hasher is deliberately slow; tests don't need that.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password=PASSWORD)


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="bob", password=PASSWORD)


@pytest.fixture
def make_item(user):
    """Build a saved WatchlistItem with sample cached TMDB data; override any field by keyword."""
    from django.utils import timezone

    from watchlist.models import WatchlistItem

    def build(**fields):
        values = {
            "user": user,
            "tmdb_id": 693134,
            "media_type": WatchlistItem.MediaType.MOVIE,
            "title": "Dune: Part Two",
            "year": 2024,
            "poster_path": "/czembW0Rk1Ke7lCJGahbOhdCuhV.jpg",
            "overview": "Paul Atreides unites with the Fremen.",
            "vote_average": "8.1",
            "genres": "Science Fiction, Adventure",
            "runtime": 166,
            "cached_at": timezone.now(),
            **fields,
        }
        return WatchlistItem.objects.create(**values)

    return build
