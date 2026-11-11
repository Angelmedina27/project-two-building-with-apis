from django.urls import include, path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    # Built-in login, POST-only logout, and password change views.
    path("", include("django.contrib.auth.urls")),
]
