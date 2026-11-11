from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import WatchlistItem


def home(request):
    return redirect("watchlist" if request.user.is_authenticated else "login")


@login_required
def watchlist(request):
    # Reads only the local cache; the watchlist never calls TMDB.
    items = WatchlistItem.objects.filter(user=request.user)
    return render(request, "watchlist/list.html", {"items": items})


@login_required
def search(request):
    # Placeholder until TMDB search is built in Phase 3.
    return render(request, "watchlist/placeholder.html", {"heading": "Search"})


@login_required
def item_detail(request, pk):
    # Placeholder until the detail page and edit form are built in Phase 6.
    item = get_object_or_404(WatchlistItem, pk=pk, user=request.user)
    return render(request, "watchlist/placeholder.html", {"heading": item.title})
