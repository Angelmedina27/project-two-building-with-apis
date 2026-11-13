from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from .views import WatchlistItemViewSet

router = DefaultRouter()
router.register("watchlist", WatchlistItemViewSet, basename="api-watchlist")

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token"),
    # Log in / log out links for the browsable API.
    path("auth/", include("rest_framework.urls")),
    *router.urls,
]
