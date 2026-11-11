from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def home(request):
    return redirect("watchlist" if request.user.is_authenticated else "login")


@login_required
def watchlist(request):
    # Placeholder until the WatchlistItem list is built in Phase 2.
    return render(request, "watchlist/placeholder.html", {"heading": "My Watchlist"})


@login_required
def search(request):
    # Placeholder until TMDB search is built in Phase 3.
    return render(request, "watchlist/placeholder.html", {"heading": "Search"})
