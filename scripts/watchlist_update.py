"""List your Cinemovtracker watchlist through the REST API and update one item's field.

Reads CINEMOVTRACKER_API_TOKEN (and optionally CINEMOVTRACKER_API_URL) from .env, lists every
saved item from GET /api/watchlist/, sends a PATCH for one field, and prints the item before
and after the change. The Django dev server must be running.

Run with:
    uv run scripts/watchlist_update.py                     # list, then prompt for the change
    uv run scripts/watchlist_update.py 3 status watched    # list, then update item 3
    uv run scripts/watchlist_update.py 3 rating 9
    uv run scripts/watchlist_update.py 3 rating none       # clear the rating
    uv run scripts/watchlist_update.py 3 notes "Rewatch with friends."
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 10
STATUSES = ["plan", "watching", "watched", "on_hold", "dropped"]
FIELDS = ["status", "rating", "notes"]
NOTES_PREVIEW = 60


class APIError(Exception):
    """A request failed in a way the script should report and stop on."""


def load_settings():
    """Load .env and return (token, base_url); token is None if missing or empty."""
    load_dotenv()
    token = os.environ.get("CINEMOVTRACKER_API_TOKEN", "").strip() or None
    base_url = os.environ.get("CINEMOVTRACKER_API_URL", "").strip() or DEFAULT_BASE_URL
    return token, base_url.rstrip("/")


def api_request(method, url, token, json=None):
    """Send one authenticated request and return its JSON, raising APIError on failure."""
    headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
    try:
        response = requests.request(
            method, url, headers=headers, json=json, timeout=TIMEOUT_SECONDS
        )
    except requests.Timeout as error:
        raise APIError(f"The server did not respond within {TIMEOUT_SECONDS} seconds.") from error
    except requests.ConnectionError as error:
        raise APIError(
            f"Could not connect to {url}. Is `uv run python manage.py runserver` running?"
        ) from error
    except requests.RequestException as error:
        raise APIError(f"Request failed: {error}") from error

    status = response.status_code
    if status == 401:
        raise APIError("The API rejected the token (401). Check CINEMOVTRACKER_API_TOKEN in .env.")
    if status == 404:
        raise APIError("That item does not exist or is not yours (404).")
    if status == 400:
        raise APIError(f"The API rejected the change (400): {describe_errors(response)}")
    if status != 200:
        raise APIError(f"Unexpected response from the API ({status}).")

    try:
        return response.json()
    except ValueError as error:
        raise APIError("The API sent a response that was not valid JSON.") from error


def describe_errors(response):
    """Turn a DRF validation error body into one readable line."""
    try:
        body = response.json()
    except ValueError:
        return response.text or "no details"
    if not isinstance(body, dict):
        return str(body)
    parts = []
    for field, messages in body.items():
        if isinstance(messages, list):
            messages = " ".join(str(m) for m in messages)
        parts.append(f"{field}: {messages}")
    return "; ".join(parts)


def list_items(base_url, token):
    """Return every watchlist item, following the API's page links."""
    items = []
    url = f"{base_url}/api/watchlist/"
    while url:
        page = api_request("GET", url, token)
        items.extend(page.get("results", []))
        url = page.get("next")
    return items


def update_item(base_url, token, item_id, field, value):
    """PATCH one field of one item and return the updated item."""
    return api_request("PATCH", f"{base_url}/api/watchlist/{item_id}/", token, {field: value})


def shorten(text, width=NOTES_PREVIEW):
    text = " ".join((text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def format_row(item):
    rating = item.get("rating")
    year = item.get("year") or "----"
    label = "Movie" if item.get("media_type") == "movie" else "TV"
    return (
        f"{item['id']:>4}  {label:<5}  {item.get('title', '(untitled)')} ({year})"
        f"  status={item.get('status')}  rating={rating if rating is not None else '-'}"
    )


def format_item(item):
    rating = item.get("rating")
    return "\n".join(
        [
            f"  id:         {item['id']}",
            f"  title:      {item.get('title')} ({item.get('year') or 'unknown year'})",
            f"  status:     {item.get('status')}",
            f"  rating:     {rating if rating is not None else '(none)'}",
            f"  notes:      {shorten(item.get('notes')) or '(none)'}",
            f"  updated_at: {item.get('updated_at')}",
        ]
    )


def parse_value(field, raw):
    """Convert the typed value to what the API expects, or raise ValueError."""
    raw = raw.strip()
    if field == "status":
        if raw not in STATUSES:
            raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
        return raw
    if field == "rating":
        if raw.lower() in ("", "none", "null"):
            return None
        if not raw.isdigit() or not 1 <= int(raw) <= 10:
            raise ValueError("rating must be a whole number from 1 to 10, or 'none' to clear it")
        return int(raw)
    return raw  # notes: any text, including empty to clear them


def prompt_change(items):
    """Ask which item, field, and value to change; return (item, field, value)."""
    ids = {item["id"]: item for item in items}
    while True:
        raw_id = input("\nItem id to update: ").strip()
        if raw_id.isdigit() and int(raw_id) in ids:
            item = ids[int(raw_id)]
            break
        print("Please enter one of the ids listed above.")
    while True:
        field = input(f"Field ({' / '.join(FIELDS)}): ").strip().lower()
        if field in FIELDS:
            break
        print(f"Please enter one of: {', '.join(FIELDS)}.")
    hints = {
        "status": ", ".join(STATUSES),
        "rating": "1-10, or none",
        "notes": "any text, or blank to clear",
    }
    while True:
        try:
            value = parse_value(field, input(f"New {field} ({hints[field]}): "))
        except ValueError as error:
            print(error)
            continue
        return item, field, value


def build_parser():
    parser = argparse.ArgumentParser(
        description="List your watchlist and update one field of one item via the API."
    )
    parser.add_argument("item_id", nargs="?", type=int, help="id of the item to update")
    parser.add_argument("field", nargs="?", choices=FIELDS, help="field to change")
    parser.add_argument("value", nargs="?", help="new value ('none' clears a rating)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.item_id is not None and (args.field is None or args.value is None):
        parser.error("give all three of item_id, field, and value, or none of them")

    token, base_url = load_settings()
    if not token:
        print(
            "CINEMOVTRACKER_API_TOKEN is missing or empty. Get a token from "
            f"{base_url}/api/auth/token/ and add it to the .env file at the repo root."
        )
        return 1

    try:
        items = list_items(base_url, token)
        print(f"Your watchlist ({len(items)} item(s)) from {base_url}/api/watchlist/:\n")
        if not items:
            print("  Nothing saved yet. Add a title on the website or via POST, then rerun.")
            return 0
        for item in items:
            print(format_row(item))

        if args.item_id is None:
            item, field, value = prompt_change(items)
        else:
            item = next((i for i in items if i["id"] == args.item_id), None)
            if item is None:
                print(f"\nNo item with id {args.item_id} is on your watchlist.")
                return 1
            field = args.field
            try:
                value = parse_value(field, args.value)
            except ValueError as error:
                print(f"\n{error}")
                return 1

        print(f"\nBefore:\n{format_item(item)}")
        print(f"\nPATCH {base_url}/api/watchlist/{item['id']}/  {{{field!r}: {value!r}}}")
        updated = update_item(base_url, token, item["id"], field, value)
        print(f"\nAfter:\n{format_item(updated)}")
    except APIError as error:
        print(f"\n{error}")
        return 1
    except KeyboardInterrupt, EOFError:
        print("\nCancelled; nothing was changed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
