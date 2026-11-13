from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse

from watchlist.decorators import htmx_login_required


def _login_target(url):
    """Split a login redirect into (path, next)."""
    parts = urlsplit(url)
    return parts.path, parse_qs(parts.query).get("next", [None])[0]


@pytest.mark.parametrize(
    ("method", "headers", "status", "redirect_header", "expected_next"),
    [
        pytest.param("get", {}, 302, "Location", "/search/?q=dune", id="normal-get"),
        pytest.param(
            "get", {"HX-Request": "true"}, 200, "HX-Redirect", "/search/?q=dune", id="htmx-get"
        ),
        pytest.param(
            "post",
            {"HX-Request": "true", "HX-Current-URL": "http://testserver/search/?q=dune&page=2"},
            200,
            "HX-Redirect",
            "/search/?q=dune&page=2",
            id="htmx-post-returns-to-current-page",
        ),
        pytest.param(
            "post",
            {"HX-Request": "true", "HX-Current-URL": "https://evil.example/phish"},
            200,
            "HX-Redirect",
            "/",
            id="htmx-post-ignores-foreign-current-url",
        ),
    ],
)
def test_anonymous_requests_are_sent_to_login_and_back(
    rf, method, headers, status, redirect_header, expected_next
):
    called = []

    @htmx_login_required
    def view(request):
        called.append(True)
        return HttpResponse("secret")

    request = getattr(rf, method)("/search/?q=dune", headers=headers)
    request.user = AnonymousUser()
    response = view(request)

    assert not called
    assert response.status_code == status
    # HTMX requests get a header htmx follows with a full-page redirect;
    # normal requests get Django's standard login redirect.
    assert redirect_header in response.headers
    assert _login_target(response.headers[redirect_header]) == ("/accounts/login/", expected_next)
