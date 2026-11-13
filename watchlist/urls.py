from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("watchlist/add/", views.add_item, name="add_item"),
    path("watchlist/<int:pk>/", views.item_detail, name="item_detail"),
    path("watchlist/<int:pk>/status/", views.item_status, name="item_status"),
    path("watchlist/<int:pk>/delete/", views.item_delete, name="item_delete"),
]
