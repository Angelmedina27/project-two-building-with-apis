from urllib.parse import urlencode, urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services, tmdb
from .decorators import htmx_login_required, is_htmx
from .filters import DEFAULT_SORT, SORTS, clean_filters, filter_watchlist
from .forms import WatchlistItemForm
from .models import WatchlistItem

SEARCH_TYPES = {"all": "All", "movie": "Movies", "tv": "TV"}


def home(request):
    return redirect("watchlist" if request.user.is_authenticated else "login")


WATCHLIST_PAGE_SIZE = 10


@htmx_login_required
def watchlist(request):
    # Reads only the local cache; the watchlist never calls TMDB.
    filters = clean_filters(request.GET)
    mine = WatchlistItem.objects.filter(user=request.user)
    items = filter_watchlist(mine, filters)
    # get_page turns a non-numeric page into 1 and an out-of-range page into the last one.
    page_obj = Paginator(items, WATCHLIST_PAGE_SIZE).get_page(request.GET.get("page"))

    # Links keep the current filters, leaving out empty ones and the default sort.
    kept = {
        key: value
        for key, value in filters.items()
        if value and not (key == "sort" and value == DEFAULT_SORT)
    }

    def page_url(number):
        return f"{request.path}?{urlencode({**kept, 'page': number})}"

    context = {
        "filters": filters,
        "status_choices": WatchlistItem.Status.choices,
        "sort_choices": [(value, label) for value, (label, _) in SORTS.items()],
        "page_obj": page_obj,
        "items": page_obj.object_list,
        # Tells "nothing matches these filters" apart from "nothing saved yet".
        "has_any_items": page_obj.paginator.count > 0 or mine.exists(),
        "previous_url": page_url(page_obj.previous_page_number())
        if page_obj.has_previous()
        else None,
        "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
    }
    template = (
        "watchlist/_watchlist_results.html" if _wants_fragment(request) else "watchlist/list.html"
    )
    response = render(request, template, context)
    # The same URL returns a fragment or a full page, so caches must keep them apart.
    patch_vary_headers(response, ["HX-Request"])
    return response


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
        "state": "form",
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

            results = [_result_card(r) for r in data["results"]]
            # One query for the (tmdb_id, media_type) pairs on this page the user has saved.
            saved = set(
                WatchlistItem.objects.filter(
                    user=request.user, tmdb_id__in={card["tmdb_id"] for card in results}
                ).values_list("tmdb_id", "media_type")
            )
            for card in results:
                if (card["tmdb_id"], card["media_type"]) in saved:
                    card["state"] = "on_watchlist"

            context.update(
                results=results,
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


SAVE_MESSAGES = {
    "saved": (messages.SUCCESS, "Saved “{title}” to your watchlist."),
    "on_watchlist": (messages.INFO, "That title is already on your watchlist."),
    "not_found": (messages.ERROR, "That title was not found on TMDB."),
    "error": (messages.WARNING, "Couldn't save that title right now. Please try again."),
}


def _back_to_search(request):
    """The search page the plain (non-htmx) Save form came from, or a fresh search."""
    referer = request.headers.get("Referer", "")
    if url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        parts = urlsplit(referer)
        if parts.path == reverse("search"):
            return parts.path + (f"?{parts.query}" if parts.query else "")
    return reverse("search")


@require_POST
@htmx_login_required
def add_item(request):
    # Only the title's identity is read from the client; TMDB fields come from TMDB.
    media_type = request.POST.get("media_type")
    try:
        tmdb_id = int(request.POST.get("tmdb_id", ""))
    except ValueError:
        tmdb_id = 0
    if media_type not in WatchlistItem.MediaType.values or tmdb_id < 1:
        return HttpResponseBadRequest("Invalid title.")

    item = None
    try:
        item = services.add_to_watchlist(request.user, media_type, tmdb_id)
    except services.AlreadyOnWatchlist:
        state = "on_watchlist"
    except tmdb.TMDBNotFound:
        state = "not_found"
    except tmdb.TMDBError:
        state = "error"
    else:
        state = "saved"

    if not is_htmx(request):
        level, text = SAVE_MESSAGES[state]
        messages.add_message(request, level, text.format(title=item.title if item else ""))
        return redirect(_back_to_search(request))

    slot = {"state": state, "item": item, "media_type": media_type, "tmdb_id": tmdb_id}
    return render(request, "watchlist/_save_button.html", {"slot": slot})


@login_required
def item_detail(request, pk):
    # Shows only the stored copy of the TMDB details; no TMDB call is made.
    item = get_object_or_404(WatchlistItem, pk=pk, user=request.user)
    if request.method == "POST":
        form = WatchlistItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Saved your changes to “{item.title}”.")
            return redirect("item_detail", pk=item.pk)
    else:
        form = WatchlistItemForm(instance=item)
    genres = [genre.strip() for genre in item.genres.split(",") if genre.strip()]
    return render(request, "watchlist/detail.html", {"item": item, "form": form, "genres": genres})


@require_POST
@htmx_login_required
def item_status(request, pk):
    item = get_object_or_404(WatchlistItem, pk=pk, user=request.user)
    status = request.POST.get("status")
    if status not in WatchlistItem.Status.values:
        return HttpResponseBadRequest("Invalid status.")
    item.status = status
    item.save(update_fields=["status", "updated_at"])
    context = {"item": item, "status_choices": WatchlistItem.Status.choices, "just_saved": True}
    return render(request, "watchlist/_watchlist_row.html", context)


@require_POST
@login_required
def item_delete(request, pk):
    item = get_object_or_404(WatchlistItem, pk=pk, user=request.user)
    title = item.title
    item.delete()
    messages.success(request, f"Removed “{title}” from your watchlist.")
    return redirect("watchlist")
