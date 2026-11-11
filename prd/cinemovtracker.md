# PRD: Cinemovtracker

## Problem Statement

People who watch a lot of movies and TV lose track of what they want to watch, what they are in the middle of, and what they thought of things they finished. Notes end up spread across phone notes apps, streaming-service lists that only cover one service, and memory. They want one personal list that:

- lets them find any movie or TV show quickly,
- keeps what they saved even when an outside service is slow, down, or they are offline,
- records their own watch status, rating, and thoughts,
- is easy to search and sort once it grows to dozens of titles,
- can also be read and changed from scripts or other tools through an API, without anyone else seeing or changing their list.

## Solution

Cinemovtracker is a Django web app where a logged-in user searches The Movie Database (TMDB) for movies and TV shows and saves them to a personal watchlist. When a title is saved, the server fetches its details from TMDB and stores a copy locally, so the watchlist works without contacting TMDB. Each saved title carries the user's own status, optional 1–10 rating, and notes.

The watchlist page supports search by title, filtering by status and type, five sort orders, and pagination. Editing is quick: status changes save straight from the list, and a detail page holds the full form. A token- or session-authenticated DRF API exposes the same watchlist with full CRUD, always limited to the requesting user's own items.

Empty searches and TMDB failures (bad key, timeouts, rate limits, server errors, unknown titles) produce friendly messages or proper API error codes and never crash a page.

## User Stories

### Accounts

1. As a visitor, I want to create an account with a username and password, so that I can keep my own watchlist.
2. As a registered user, I want to log in, so that I can reach my watchlist and search.
3. As a logged-in user, I want to log out from the navbar, so that others on my computer can't use my account.
4. As a logged-in user, I want to change my password while logged in, so that I can keep my account secure.
5. As a visitor, I want the home page to send me to the login page, so that I know I need an account.
6. As a logged-in user, I want the home page to send me to my watchlist, so that I land on my list right away.
7. As a visitor, I want any protected page to redirect me to login and return me there afterward, so that I don't lose my place.

### Searching TMDB

8. As a logged-in user, I want to type a title and press Search, so that I can find movies and TV shows from TMDB.
9. As a logged-in user, I want results to appear without a full page reload, so that searching feels fast.
10. As a logged-in user, I want the search URL to update with my query, type, and page, so that Back, Refresh, and bookmarks work.
11. As a logged-in user, I want to filter search results to All, Movies, or TV, so that I see only the kind of title I'm looking for.
12. As a logged-in user, I want people (actors, directors) left out of results, so that every result is something I can save.
13. As a logged-in user, I want each result to show its poster, title, type, year, TMDB score, and a short overview, so that I can tell similar titles apart.
14. As a logged-in user, I want Previous and Next buttons with "Page X of Y", so that I can reach titles beyond the first 20 results.
15. As a logged-in user, I want an invalid page number in the URL to fall back to page 1, so that a bad link doesn't break the page.
16. As a logged-in user, I want an empty or whitespace-only search to show a friendly prompt instead of calling TMDB, so that I'm told what to do.
17. As a logged-in user, I want a clear "no movies or TV shows match" message, so that I know the search worked but found nothing.
18. As a logged-in user, I want a friendly alert when TMDB is down, slow, or rate-limiting, so that I know to try again later instead of seeing an error page.
19. As a logged-in user, I want a clear message when search isn't configured (missing or rejected API key), so that the app keeps working and I'm not shown technical details.
20. As a logged-in user, I want the search page to work without JavaScript as a normal form, so that it still functions if scripts fail.

### Saving to the watchlist

21. As a logged-in user, I want a Save button on each search result, so that I can add a title to my watchlist.
22. As a logged-in user, I want saving to happen in place and change the button to "Saved" with an Edit link, so that I can keep saving titles without losing my search.
23. As a logged-in user, I want results I already saved to show "On watchlist" instead of Save, so that I don't try to add them again.
24. As a logged-in user, I want a second save of the same title (double click, another tab) to show "On watchlist" rather than an error or a duplicate, so that my list stays clean.
25. As a logged-in user, I want a small "Couldn't save, try again" message if TMDB fails during save, with the button still available, so that I can retry.
26. As a logged-in user, I want new saves to start as "Plan to watch", so that saving reflects my intent without extra steps.
27. As a logged-in user, I want saved titles to keep their title, year, poster, overview, genres, TMDB score, and runtime or season count, so that my watchlist is complete without TMDB.

### Viewing and organizing the watchlist

28. As a logged-in user, I want a My Watchlist page listing only my saved titles, so that I can see everything I'm tracking.
29. As a logged-in user, I want my watchlist to load even when TMDB is unavailable or I'm offline, so that my data is always reachable.
30. As a logged-in user, I want to search my watchlist by title (case-insensitive, partial match), so that I can find a title fast.
31. As a logged-in user, I want to filter my watchlist by status, so that I can see, for example, only what I'm watching.
32. As a logged-in user, I want to filter my watchlist by Movies or TV, so that I can focus on one kind.
33. As a logged-in user, I want to sort by recently added (the default), title A–Z, my rating high to low (unrated last), release year newest first, or TMDB score high to low, so that I can view my list the way I need.
34. As a logged-in user, I want my watchlist split into pages of 10 with Previous/Next links that keep my search, filters, and sort, so that long lists stay manageable.
35. As a logged-in user, I want the watchlist controls to update the list without a full reload and keep the URL in sync, so that it's fast and bookmarkable.
36. As a logged-in user, I want unknown filter or sort values in the URL to be ignored, and out-of-range page numbers to show the nearest valid page, so that edited links never break the page.
37. As a logged-in user, I want a friendly empty state with a link to search when my watchlist (or a filtered view) is empty, so that I know what to do next.
38. As a logged-in user, I want posters to show a placeholder with the title's initials when there's no poster or images can't load, so that the layout stays tidy offline.

### Editing and deleting

39. As a logged-in user, I want a status dropdown on each watchlist row that saves as soon as I change it, so that the most common update takes one click.
40. As a logged-in user, I want a short "Saved" confirmation on that row, so that I know the change stuck.
41. As a logged-in user, I want to open a detail page for a title showing its stored TMDB info and my tracking fields, so that I can read about it and edit my details.
42. As a logged-in user, I want to edit status, rating, and notes in one form on the detail page, so that I can record my thoughts.
43. As a logged-in user, I want a clear error if my rating is outside 1–10 or not a whole number, so that I can fix it.
44. As a logged-in user, I want to leave rating blank, so that I don't have to rate things I haven't watched.
45. As a logged-in user, I want a clear error if my notes are too long, so that I know the limit.
46. As a logged-in user, I want a success message after saving changes, so that I know they were stored.
47. As a logged-in user, I want a Remove button that asks me to confirm in a modal before deleting, so that I don't delete titles by accident.
48. As a logged-in user, I want to return to my watchlist with a "Removed" message after deleting, so that I know it worked.
49. As a logged-in user, I want any attempt to open, edit, or delete someone else's item to show "not found", so that other people's lists stay private.
50. As a logged-in user whose session expired, I want quick actions (Save, status dropdown, list updates) to send me to the login page and back afterward, so that I never see a broken half-page.

### API

51. As an API client, I want to exchange my username and password for a token, so that I can call the API from scripts and tools.
52. As an API client, I want to authenticate with either my token or my logged-in browser session, so that I can use curl, Postman, or the browsable API.
53. As an anonymous client, I want every API endpoint to refuse me, so that no data is exposed without login.
54. As an API client, I want to list my watchlist items as paginated JSON (10 per page with count, next, and previous), so that I can process them in batches.
55. As an API client, I want the list endpoint to accept the same search, status, type, and sort parameters as the website, so that I get the same results either way.
56. As an API client, I want to create an item by sending only the media type and TMDB ID (plus optional status, rating, and notes), so that the server fills in trusted TMDB details.
57. As an API client, I want a 400 error with a clear message for invalid input, duplicates, or a TMDB ID that doesn't exist, so that I can correct my request.
58. As an API client, I want a 503 error with a clear message when TMDB is unavailable during create, with nothing saved, so that I know to retry later.
59. As an API client, I want to retrieve, fully update, partially update, and delete my own items, so that I have full CRUD.
60. As an API client, I want updates to change only status, rating, and notes, with TMDB fields and the title's identity read-only, so that items can't be corrupted or faked.
61. As an API client, I want requests for another user's item IDs to return 404, so that I can't discover or change their data.

### Data freshness and operations

62. As the developer, I want a management command that refreshes stored TMDB details older than 150 days, so that the app follows TMDB's 6-month caching rule.
63. As the developer, I want that command to skip and log titles that fail to refresh and keep going, so that one bad title doesn't stop the run.
64. As the developer, I want a missing or rejected TMDB key logged as an error without crashing the app, so that I can diagnose it while the watchlist keeps working.
65. As the developer, I want an example environment file listing the required settings, so that anyone cloning the repo knows what to set.
66. As the developer, I want saved items and users visible in the Django admin with status and type filters, so that I can inspect and fix data.
67. As the developer, I want the test suite to run offline without a TMDB key and to block real network calls, so that tests are fast and reliable.
68. As a grader, I want to run the app after syncing dependencies without a frontend build step, so that setup is simple.
69. As any user, I want the TMDB logo and the notice "This product uses the TMDB API but is not endorsed or certified by TMDB" on every page, so that the app meets TMDB's attribution terms.

## Implementation Decisions

### Stack and tooling
- Python 3.14, managed with uv. The latest stable Django release that officially supports Python 3.14 (confirm the exact version when building), plus Django REST Framework, `requests`, and `python-dotenv`.
- SQLite database.
- Dev dependencies: pytest, pytest-django, responses, ruff, and pytailwindcss.
- Ruff is configured in the project's pyproject: line length 100; rule sets E, F, I, B, UP, and DJ; migrations excluded.
- Secret key, debug flag, and TMDB API key are read from a `.env` file, with safe development defaults for the first two. A committed example env file lists `TMDB_API_KEY`. The real `.env` stays git-ignored.

### Project structure
- A Django project package named `config`, with two apps:
  - **accounts**: a custom user model (a plain subclass of Django's abstract user) set as the auth user model from the first migration, plus a sign-up view.
  - **watchlist**: the model, the TMDB client, the services, the filtering, the web views and forms, the API (as a sub-package), and the refresh management command.
- Project-level templates and static directories and a top-level tests directory. `manage.py` sits at the repo root.
- The existing TMDB check script stays as a research artifact. Its timeout, auth style, people filtering, and status-code handling carry over into the TMDB client.

### Data model: `WatchlistItem` (single table)
- Owner: a foreign key to the user.
- TMDB identity: `tmdb_id` (integer) and `media_type` (movie or tv). Movie and TV IDs are separate namespaces, so both are needed.
- Cached TMDB fields: title, release/first-air year, poster path, overview, TMDB vote average, genres (comma-separated text), runtime in minutes (movies), number of seasons (TV), and a `cached_at` timestamp.
- User fields:
  - status: text choices with stored codes plan, watching, watched, on_hold, and dropped; default plan.
  - rating: optional positive small integer with min 1 and max 10 validators.
  - notes: optional text, max about 2,000 characters, enforced by a validator.
- `created_at` (set on creation) and `updated_at` (set on every save).
- A unique constraint on (user, tmdb_id, media_type). Different users may save the same title.
- TMDB data is intentionally duplicated per user. This trades storage for a simpler single-model design.

### TMDB client
- One service module in the watchlist app handles all TMDB HTTP calls: search, search by type, and details. It uses a 10-second timeout and the `api_key` query parameter.
- Exception hierarchy: a base `TMDBError`, with `TMDBNotFound` and `TMDBUnavailable` under it, and `TMDBConfigError` as a subclass of `TMDBUnavailable`.
  - 404 → not found.
  - Timeout, connection error, 429, 5xx, and invalid JSON → unavailable.
  - Missing key or 401 → config error, which is also logged at error level.
- Views and the API catch `TMDBError` subclasses only. Raw `requests` exceptions never reach views. A missing key never stops Django from starting.
- Search endpoint by filter: All uses multi-search with person results removed; Movies uses movie search; TV uses TV search. The client adds the media type to single-type results, which don't include it.
- Paging passes TMDB's page number through and reads TMDB's total-page count. TMDB caps this at 500.
- No caching of search responses. The rate limit (about 40 requests per second) isn't a realistic risk with submit-based search, and 429 is handled as unavailable.

### Services (shared logic)
- An "add to watchlist" service takes a user, media type, and TMDB ID (plus optional user fields). It fetches TMDB details, maps them to the cached fields, and creates the item. It never accepts TMDB field values from the client. If the fetch fails, nothing is created.
- A "refresh item" service re-fetches details and updates cached fields and `cached_at`.
- The web Save action, the API create endpoint, and the refresh command all use these services.

### Watchlist filtering
- One shared function takes a queryset that is already limited to the user, plus request parameters, and applies:
  - `q`: case-insensitive title substring.
  - `status`: one of the five codes.
  - `media_type`: movie or tv.
  - `sort`: chosen from a whitelist mapping — recently added (default, newest first), title A–Z, rating high to low with nulls last, year newest, and TMDB score high to low.
- Unknown or invalid values are ignored and the defaults apply.
- The website view and the API list endpoint both use this function.

### Web views and URLs
- `/` redirects to the watchlist when logged in, otherwise to login.
- Accounts URLs:
  - Login and logout come from Django's built-in auth views. Logout is POST-only and appears as a navbar form.
  - Sign-up uses Django's user-creation form and logs the user in, then goes to the watchlist.
  - Password change comes from the built-in views.
  - After login, users go to the watchlist.
- `/search/` is a GET form (query, type, page).
  - HTMX submits it and swaps only the results region, pushing the URL to history. Without JavaScript it falls back to a full page.
  - Empty or whitespace queries skip TMDB entirely.
  - TMDB errors render a DaisyUI alert in the results region with a 200 response.
  - Already-saved results are marked using one database query for the current user's (tmdb_id, media_type) pairs.
- `/watchlist/add/` is POST-only. It receives just the media type and TMDB ID and returns a small HTML fragment that replaces the Save button with one of four states:
  - saved, with a link to the detail page;
  - already on the watchlist (including after a unique-constraint race);
  - not found;
  - couldn't save, try again.
  Non-HTMX POSTs redirect back to the search page with a message.
- `/watchlist/` is the list with search, filter, sort, and 10-per-page pagination.
  - HTMX swaps the list region and pushes the URL to history.
  - Pagination links keep all current parameters.
  - Out-of-range pages show the nearest valid page.
  - No TMDB calls are made.
- `/watchlist/<id>/status/` is POST-only and triggered by the row's status dropdown on change. It validates the status code, saves it, and returns the re-rendered row with a "Saved" indicator.
- `/watchlist/<id>/` is the detail page with stored TMDB info and a model form for status, rating, and notes.
  - A valid POST redirects back with a success message.
  - An invalid POST re-renders with field errors.
- `/watchlist/<id>/delete/` is POST-only. The detail page's Remove button opens a DaisyUI confirm modal that submits here, then redirects to the watchlist with a "Removed" message.
- Every item lookup is limited to the current user's items. Another user's item ID returns 404.
- An HTMX-aware login-required decorator: for HTMX requests from users who aren't logged in, it returns an `HX-Redirect` header pointing to the login page with a `next` value for the current page. Normal requests use standard login-required behavior. It applies to all HTMX endpoints and fragment responses.
- The CSRF token is supplied to all HTMX requests through a header set once on the page body.
- Django messages are shown in the base layout.

### Frontend
- Server-rendered Django templates styled with Tailwind CSS and DaisyUI, with interactivity from HTMX. There is no JavaScript framework.
- Tailwind is built with the standalone CLI through pytailwindcss, so no Node.js is needed (it isn't installed on the dev machine). DaisyUI is loaded as its standalone plugin file. HTMX is saved locally as a pinned static file.
- The compiled CSS is committed, so the app runs without a build step. A watch command is documented for development.
- The base layout includes a navbar (Search, My Watchlist, username, Log out), a messages area, and a footer with the TMDB logo and the required notice.
- Posters come from TMDB's image server, at w185 on lists and search results and w342 on the detail page. A DaisyUI placeholder with the title's initials appears when there's no poster path or the image fails to load. No images are downloaded or stored locally.
- The editing UX follows the approved prototype, variant A: a list table with an inline status dropdown, a detail page with the full form, and a confirm modal for delete.

### API (DRF)
- Default authentication: session and token, using DRF's built-in authtoken app. A token endpoint exchanges a username and password for a token.
- Default permission: authenticated users only.
- A model viewset with a router at `/api/watchlist/` supports list, create, retrieve, update, partial update, and destroy.
- The viewset's queryset is always limited to the requesting user, so other users' items return 404. The owner is set from the request user on create and is never part of the input.
- Serializer rules:
  - On create, media type and TMDB ID are required, and status, rating, and notes are optional.
  - After create, media type and TMDB ID are read-only.
  - All cached TMDB fields, timestamps, and the ID are always read-only.
- Create calls the shared add-to-watchlist service:
  - Duplicate → 400 with a clear message.
  - TMDB not found → 400.
  - TMDB unavailable or config error → 503 via DRF's service-unavailable exception, with a JSON detail message. Nothing is saved.
- Rating range and notes length are validated through the model validators, so they return 400 with field errors.
- The list endpoint uses the shared filtering function with the same query parameter names as the website, and page-number pagination at 10 per page.

### Management command
- `refresh_tmdb` selects items whose `cached_at` is older than 150 days, a safety margin under TMDB's 6-month limit. It refreshes each item through the shared service, logs and skips failures, and prints a summary of how many were refreshed and how many failed.
- It is run manually or by an OS scheduler, as documented in the README.

### Admin
- `WatchlistItem` is registered with list filters for status and media type and search by title. The custom user model is registered with Django's standard user admin.

### Testing approach
- pytest with pytest-django. Plain fixtures (two users and an item-builder helper) are used instead of factory_boy.
- The TMDB client is tested at the HTTP layer with `responses`, covering 200, 401, 404, 429, 5xx, timeout, connection error, invalid JSON, people filtering, the per-type endpoint choice, and the missing key.
- View and API tests replace the TMDB client functions with monkeypatched fakes that return sample data or raise the custom exceptions.
- A suite-wide fixture blocks real network access, so tests need no key and no internet connection.
- Areas to test:
  - Model: constraints, defaults, and validators.
  - The filtering function directly: every filter, sort, and invalid value.
  - Search page: empty query, no results, errors, already-saved marking, and paging.
  - Save fragment states.
  - Status quick-update.
  - Detail form validation.
  - Delete, POST-only.
  - Ownership isolation (404) on both web and API.
  - The HTMX login redirect.
  - API create, update, and read-only rules, including 400 and 503 responses.
  - Token authentication and anonymous rejection.
  - The refresh command, including skipping failures.

## Out of Scope

- TV episode progress tracking, such as an episodes-watched counter or TVmaze episode lists. The "Watching" status and notes cover this for now.
- Password reset by email (no email backend). Password change while logged in and admin resets are available.
- Social features: public or shared lists, following, and comments.
- Games, music, or any provider other than TMDB (IGDB, MusicBrainz, and others).
- Deployment to a hosting service. The app runs locally on the development server with SQLite.
- Recommendations or "similar titles".
- A separate JavaScript single-page frontend. The API serves scripts, tools, and grading, not the website.
- Caching TMDB search responses.
- Downloading or storing poster images locally.
- Changing a saved item's TMDB identity. Users delete the item and re-add it instead.
- Genre filtering and searching inside notes on the watchlist.
- JWT or other token schemes with expiry.

## Further Notes

- **TMDB terms:** non-commercial use only, the TMDB logo and notice are required, no caching of TMDB content for more than 6 months, and cached content must be purged if API access ends. The 150-day refresh command is how the app meets the caching rule. No ads or paid features should be added.
- **"Works offline" definition:** all watchlist data (titles, overviews, user status, ratings, and notes) and all watchlist pages work without TMDB. Poster images and TMDB search need internet access and degrade gracefully without it.
- **Decision rationale** comes from a design interview held on 2026-11-11. The editing UX was chosen after comparing three variants in a throwaway prototype kept in the repo's prototypes folder, with the decision recorded at the top of that file.
- **README:** should cover setup (uv sync, env file, migrate, runserver), the Tailwind watch command, running tests and Ruff, getting an API token and example curl calls, running the refresh command, and why search caching and local poster storage were deliberately skipped.
- **Versions:** exact versions of Django, DRF, Tailwind, DaisyUI, and HTMX should be checked against current official sources at build time rather than assumed.
- **Background research:** see the free media API research note and the TMDB check script in the repo.
