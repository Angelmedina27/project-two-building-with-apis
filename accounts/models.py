from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user model; a plain subclass so fields can be added later without a swap."""
