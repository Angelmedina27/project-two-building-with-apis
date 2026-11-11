from django.contrib import admin

from .models import WatchlistItem


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ["title", "media_type", "year", "status", "rating", "user", "created_at"]
    list_filter = ["status", "media_type"]
    search_fields = ["title"]
    readonly_fields = ["created_at", "updated_at"]
