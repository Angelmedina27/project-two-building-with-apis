from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import patch_vary_headers

from . import tmdb
from .decorators import htmx_login_required, is_htmx
from .models import WatchlistItem

SEARCH_TYPES = {"all": "All", "movie": "Movies", "tv": "TV"}


def home(request):
    return redirect("watchlist" if request.user.is_authenticated else "login")


@login_required
def watchlist(request):
    # Reads only the local cache; the watchlist never calls TMDB.
    items = WatchlistItem.objects.filter(user=request.user)
    return render(request, "watchlist/list.html", {"items": items})


def _search_page(value):
    """A valid TMDB page number from the URL, or 1 for anything invalid."""
    try:
        page = int(value)
    except TypeError, ValueError:
        return 1
    return page if 1 <= page <= tmdb.MAX_SEARCH_PAGES else 1


def _result_card(result):
    return {
        "tmdb_id": result.get("id"),
        "media_type": result["media_type"],
        "media_label": "Movie" if result["media_type"] == "movie" else "TV",
        "title": tmdb.title_of(result),
        "year": tmdb.year_of(result),
        "poster_path": result.get("poster_path") or "",
        "vote_average": result.get("vote_average") or None,
        "overview": result.get("overview") or "",
    }


def _wants_fragment(request):
    # htmx asks for the full page when Back misses its history cache.
    return is_htmx(request) and request.headers.get("HX-History-Restore-Request") != "true"


@htmx_login_required
def search(request):
    query = request.GET.get("q", "").strip()
    media_filter = request.GET.get("type", "all")
    if media_filter not in SEARCH_TYPES:
        media_filter = "all"
    page = _search_page(request.GET.get("page"))

    context = {"query": query, "media_filter": media_filter, "search_types": SEARCH_TYPES}
    # Empty or whitespace-only queries never reach TMDB.
    if query:
        try:
            data = tmdb.search(query, media_filter, page)
        except tmdb.TMDBConfigError:
            context["error"] = "config"
        except tmdb.TMDBError:
            context["error"] = "unavailable"
        else:
            page = data["page"]
            total_pages = min(data["total_pages"], tmdb.MAX_SEARCH_PAGES)

            def page_url(number):
                params = {"q": query, "type": media_filter, "page": number}
                return f"{request.path}?{urlencode(params)}"

            context.update(
                results=[_result_card(r) for r in data["results"]],
                page=page,
                total_pages=total_pages,
                previous_url=page_url(page - 1) if page > 1 else None,
                next_url=page_url(page + 1) if page < total_pages else None,
            )

    template = (
        "watchlist/_search_results.html" if _wants_fragment(request) else "watchlist/search.html"
    )
    response = render(request, template, context)
    # The same URL returns a fragment or a full page, so caches must keep them apart.
    patch_vary_headers(response, ["HX-Request"])
    return response


@login_required
def item_detail(request, pk):
    # Placeholder until the detail page and edit form are built in Phase 6.
    item = get_object_or_404(WatchlistItem, pk=pk, user=request.user)
    return render(request, "watchlist/placeholder.html", {"heading": item.title})
