from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from .. import services, tmdb
from ..models import WatchlistItem


class ServiceUnavailable(APIException):
    """503 for when TMDB can't be reached; DRF has no built-in exception for it."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


TMDB_FIELDS = [
    "title",
    "year",
    "poster_path",
    "overview",
    "vote_average",
    "genres",
    "runtime",
    "number_of_seasons",
    "cached_at",
]


class WatchlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchlistItem
        fields = [
            "id",
            "media_type",
            "tmdb_id",
            *TMDB_FIELDS,
            "status",
            "rating",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", *TMDB_FIELDS, "created_at", "updated_at"]

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        if self.instance is not None:
            # A saved item's identity is fixed: users delete and re-add instead.
            for field in ("media_type", "tmdb_id"):
                extra_kwargs.setdefault(field, {})["read_only"] = True
        return extra_kwargs

    def create(self, validated_data):
        # Only the identity and the user's own fields reach the service; TMDB fills the rest.
        user = validated_data.pop("user")
        media_type = validated_data.pop("media_type")
        tmdb_id = validated_data.pop("tmdb_id")
        try:
            return services.add_to_watchlist(user, media_type, tmdb_id, **validated_data)
        except services.AlreadyOnWatchlist:
            raise serializers.ValidationError(
                {"non_field_errors": ["This title is already on your watchlist."]}
            ) from None
        except tmdb.TMDBNotFound:
            kind = "movie" if media_type == WatchlistItem.MediaType.MOVIE else "TV show"
            raise serializers.ValidationError(
                {"tmdb_id": [f"No {kind} with TMDB ID {tmdb_id} exists."]}
            ) from None
        except tmdb.TMDBUnavailable:
            # Covers config errors too; the client logs those, and callers only need to retry.
            raise ServiceUnavailable(
                "TMDB is unavailable right now, so the title wasn't saved. Try again later."
            ) from None
