import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.loader import render_to_string

pytestmark = pytest.mark.django_db

NOTICE = "This product uses the TMDB API but is not endorsed or certified by TMDB"
ANONYMOUS_PAGES = ["/accounts/login/", "/accounts/signup/"]
LOGGED_IN_PAGES = [
    "/watchlist/",
    "/search/",
    "/accounts/password_change/",
    "/accounts/password_change/done/",
]


def assert_tmdb_attribution(response):
    html = response.content.decode()
    assert response.status_code == 200
    assert NOTICE in html
    assert "img/tmdb-logo.svg" in html


@pytest.mark.parametrize("path", ANONYMOUS_PAGES)
def test_anonymous_pages_show_tmdb_logo_and_notice(client, path):
    assert_tmdb_attribution(client.get(path))


@pytest.mark.parametrize("path", LOGGED_IN_PAGES)
def test_logged_in_pages_show_tmdb_logo_and_notice(client, user, path):
    client.force_login(user)
    assert_tmdb_attribution(client.get(path))


def test_navbar_shows_links_username_and_post_logout_form(client, user):
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()
    assert 'href="/search/"' in html
    assert 'href="/watchlist/"' in html
    assert "alice" in html
    assert '<form method="post" action="/accounts/logout/">' in html


def test_base_layout_loads_compiled_css_and_htmx_with_csrf_header(client, user):
    client.force_login(user)
    html = client.get("/watchlist/").content.decode()
    assert "css/app.css" in html
    assert "js/htmx.min.js" in html
    assert 'hx-headers=\'{"X-CSRFToken": "' in html


def test_messages_are_shown_in_the_layout(rf, user):
    request = rf.get("/watchlist/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    messages.success(request, "Changes saved")

    html = render_to_string("base.html", request=request)
    assert "Changes saved" in html
    assert "alert-success" in html


def test_django_starts_without_tmdb_key():
    root = Path(__file__).resolve().parent.parent
    env = {**os.environ, "TMDB_API_KEY": ""}
    result = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
