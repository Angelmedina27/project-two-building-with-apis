from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("watchlist/<int:pk>/", views.item_detail, name="item_detail"),
]
