from rest_framework import viewsets

from ..filters import filter_watchlist
from ..models import WatchlistItem
from .serializers import WatchlistItemSerializer


class WatchlistItemViewSet(viewsets.ModelViewSet):
    """CRUD for the requesting user's watchlist; other users' items are invisible (404)."""

    serializer_class = WatchlistItemSerializer

    def get_queryset(self):
        mine = WatchlistItem.objects.filter(user=self.request.user)
        if self.action == "list":
            # Same q/status/media_type/sort parameters as the website's list.
            return filter_watchlist(mine, self.request.query_params)
        return mine

    def perform_create(self, serializer):
        # The owner always comes from the request, never from the input.
        serializer.save(user=self.request.user)
