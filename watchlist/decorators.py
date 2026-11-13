from functools import wraps
from urllib.parse import urlsplit

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme


def is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _return_path(request):
    """Where to send the user after login: the page they were looking at."""
    if request.method == "GET":
        # GET endpoints here also render as full pages, so the request URL itself works.
        return request.get_full_path()
    # A POST fragment (e.g. Save) can't be revisited; return to the browser's page instead.
    current = request.headers.get("HX-Current-URL", "")
    if url_has_allowed_host_and_scheme(
        current, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        parts = urlsplit(current)
        return parts.path + (f"?{parts.query}" if parts.query else "")
    return "/"


def htmx_login_required(view):
    """Like ``login_required``, but HTMX requests get an ``HX-Redirect`` to the login page.

    A plain 302 would make htmx swap the login page into a fragment; ``HX-Redirect`` makes
    it load the login page in full, with ``next`` pointing back to the user's page.
    """
    protected = login_required(view)

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if is_htmx(request) and not request.user.is_authenticated:
            login_url = redirect_to_login(_return_path(request)).url
            response = HttpResponse(status=200)
            response["HX-Redirect"] = login_url
            return response
        return protected(request, *args, **kwargs)

    return wrapper
