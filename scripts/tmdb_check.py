"""Interactive console check that TMDB_API_KEY in .env can reach the TMDB API.

Run with:  uv run scripts/tmdb_check.py
"""

import os
import sys
import textwrap

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.themoviedb.org/3"
TIMEOUT_SECONDS = 10
MAX_RESULTS = 10
OVERVIEW_WIDTH = 200


class FatalAPIError(Exception):
    """A problem no retry can fix (e.g. a bad key), so the script should stop."""


class APIError(Exception):
    """A problem with one request; the user can try again."""


def get_api_key():
    """Load .env and return TMDB_API_KEY, or None if it is missing or empty."""
    load_dotenv()
    key = os.environ.get("TMDB_API_KEY", "").strip()
    return key or None


def tmdb_get(path, api_key, params=None):
    """GET a TMDB endpoint and return its JSON, raising APIError/FatalAPIError."""
    query = {"api_key": api_key, **(params or {})}
    try:
        response = requests.get(f"{BASE_URL}{path}", params=query, timeout=TIMEOUT_SECONDS)
    except requests.Timeout:
        raise APIError(f"TMDB did not respond within {TIMEOUT_SECONDS} seconds.")
    except requests.ConnectionError:
        raise APIError("Could not connect to TMDB. Check your internet connection.")
    except requests.RequestException as error:
        raise APIError(f"Request failed: {error}")

    status = response.status_code
    if status == 401:
        raise FatalAPIError("TMDB rejected the API key (401). Check TMDB_API_KEY in .env.")
    if status == 404:
        raise APIError("TMDB could not find that item (404).")
    if status == 429:
        raise APIError("Too many requests (429). Wait a moment and try again.")
    if status >= 500:
        raise APIError(f"TMDB is having server trouble ({status}). Try again later.")
    if status != 200:
        raise APIError(f"Unexpected response from TMDB ({status}).")

    try:
        return response.json()
    except ValueError:
        raise APIError("TMDB sent a response that was not valid JSON.")


def search(query, api_key):
    """Return up to MAX_RESULTS movie/TV results for query (people are skipped)."""
    data = tmdb_get("/search/multi", api_key, {"query": query, "include_adult": "false"})
    results = [r for r in data.get("results", []) if r.get("media_type") in ("movie", "tv")]
    return results[:MAX_RESULTS]


def get_details(media_type, tmdb_id, api_key):
    """Return the full details for one movie or TV show."""
    return tmdb_get(f"/{media_type}/{tmdb_id}", api_key)


def title_of(item):
    # Movies use "title"; TV shows use "name".
    return item.get("title") or item.get("name") or "(untitled)"


def date_of(item):
    # Movies use "release_date"; TV shows use "first_air_date".
    return item.get("release_date") or item.get("first_air_date") or "unknown date"


def label_of(item):
    return "Movie" if item.get("media_type") == "movie" else "TV"


def shorten(text, width=OVERVIEW_WIDTH):
    if not text:
        return "No overview available."
    return textwrap.shorten(text, width=width, placeholder="...")


def format_result(number, item):
    rating = item.get("vote_average") or 0
    return (
        f"{number:>2}. [{label_of(item)}] {title_of(item)} ({date_of(item)})"
        f"  rating {rating:.1f}/10  id {item.get('id')}\n"
        f"    {shorten(item.get('overview'))}"
    )


def format_details(media_type, details):
    genres = ", ".join(g["name"] for g in details.get("genres", [])) or "none listed"
    lines = [
        "",
        f"=== {title_of(details)} ===",
        f"Type:     {'Movie' if media_type == 'movie' else 'TV show'}",
        f"Date:     {date_of(details)}",
        f"Status:   {details.get('status') or 'unknown'}",
        f"Genres:   {genres}",
    ]
    if media_type == "movie":
        runtime = details.get("runtime")
        lines.append(f"Runtime:  {f'{runtime} min' if runtime else 'unknown'}")
    else:
        lines.append(f"Seasons:  {details.get('number_of_seasons', 'unknown')}")
        lines.append(f"Episodes: {details.get('number_of_episodes', 'unknown')}")
    lines.append(f"Rating:   {(details.get('vote_average') or 0):.1f}/10")
    lines.append("")
    lines.append(textwrap.fill(details.get("overview") or "No overview available.", width=78))
    return "\n".join(lines)


def pick_result(results):
    """Ask for a result number; return the chosen item, or None to go back."""
    while True:
        choice = input(f"\nPick 1-{len(results)} for details, or press Enter to search again: ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice) - 1]
        print(f"Please enter a number from 1 to {len(results)}, or press Enter.")


def main():
    api_key = get_api_key()
    if not api_key:
        print("TMDB_API_KEY is missing or empty. Add it to the .env file at the repo root.")
        return 1

    print("TMDB check: search movies and TV shows. Press Enter or type q to quit.")
    try:
        while True:
            query = input("\nSearch: ").strip()
            if not query or query.lower() == "q":
                break

            try:
                results = search(query, api_key)
            except APIError as error:
                print(error)
                continue

            if not results:
                print(f'No movie or TV results for "{query}".')
                continue

            print()
            for number, item in enumerate(results, start=1):
                print(format_result(number, item))

            item = pick_result(results)
            if item is None:
                continue

            try:
                details = get_details(item["media_type"], item["id"], api_key)
            except APIError as error:
                print(error)
                continue
            print(format_details(item["media_type"], details))
    except FatalAPIError as error:
        print(error)
        return 1
    except (KeyboardInterrupt, EOFError):
        print()

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
