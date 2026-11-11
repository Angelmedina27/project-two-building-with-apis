# Plan: Cinemovtracker

> Source PRD: `prd/cinemovtracker.md` (written from the 2026-11-11 design interview)

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: Python 3.14 via uv; latest stable Django supporting 3.14 (verify version at build time) + Django REST Framework, `requests`, `python-dotenv`. SQLite. Dev deps: pytest, pytest-django, responses, ruff, pytailwindcss.
- **Project layout**: Django project package `config`; `manage.py` at repo root; project-level `templates/`, `static/`, and top-level `tests/`.
- **Apps**:
  - `accounts` — custom user model (plain `AbstractUser` subclass, set as `AUTH_USER_MODEL` from the first migration) and sign-up.
  - `watchlist` — model, TMDB client, shared services, shared filtering, web views/forms, API (sub-package), and the `refresh_tmdb` management command.
- **URLs**:
  - `/` → watchlist if logged in, otherwise login.
  - `/accounts/…` → login, logout (POST only), sign-up, password change (Django built-in auth views + sign-up view). After login → watchlist.
  - `/search/` (GET: `q`, `type`, `page`)
  - `/watchlist/` (GET: `q`, `status`, `media_type`, `sort`, `page`)
  - `/watchlist/add/` (POST only)
  - `/watchlist/<id>/` (detail + edit form)
  - `/watchlist/<id>/status/` (POST only)
  - `/watchlist/<id>/delete/` (POST only)
  - `/api/auth/token/` (POST, username/password → token)
  - `/api/watchlist/` and `/api/watchlist/<id>/` (DRF router, `ModelViewSet`)
  - Items are addressed by integer pk; every lookup is limited to the current user's items, so another user's ID returns 404.
- **Model**: a single table, `WatchlistItem`:
  - Owner: FK to user.
  - TMDB identity: `tmdb_id` (int) and `media_type` (movie / tv).
  - Cached TMDB fields: title, year, poster path, overview, vote average, genres (comma text), runtime (movie), number of seasons (tv), `cached_at`.
  - User fields: `status` (TextChoices: plan, watching, watched, on_hold, dropped; default plan), `rating` (optional, 1–10), `notes` (optional, ~2,000 char max via validator).
  - Timestamps: `created_at` and `updated_at`.
  - Constraint: `UniqueConstraint(user, tmdb_id, media_type)`.
- **TMDB access**: all HTTP goes through one client module in `watchlist`.
  - 10 s timeout, `api_key` query param.
  - Exceptions: `TMDBError` > `TMDBNotFound`, `TMDBUnavailable` > `TMDBConfigError`.
  - Views and the API catch only these; a missing key never stops Django from starting.
- **Shared logic**: an add-to-watchlist service and a refresh-item service (used by web Save, API create, and the refresh command), and one filtering function (used by the web list and the API list). The server never trusts client-supplied TMDB fields.
- **Auth**:
  - Web: session login with login-required views; HTMX endpoints use an HTMX-aware decorator that answers with `HX-Redirect` to login with `?next=`.
  - API: DRF Session + Token auth (built-in authtoken), `IsAuthenticated` by default.
- **Frontend**:
  - Server-rendered templates with Tailwind + DaisyUI (standalone CLI via pytailwindcss, no Node) and a vendored, pinned HTMX file. The compiled CSS is committed.
  - The CSRF token reaches HTMX through a header on `<body>`.
  - Posters are hotlinked from `image.tmdb.org` (w185 list, w342 detail), with an initials placeholder.
  - Editing UX follows prototype variant A (`prototypes/watchlist-edit.html`).
- **Testing**:
  - pytest-django with plain fixtures (two users and an item builder).
  - `responses` tests the TMDB client; views and the API use monkeypatched client functions.
  - A suite-wide fixture blocks real network calls.
- **Config**: `SECRET_KEY`, `DEBUG`, `TMDB_API_KEY` from `.env` (git-ignored); `.env.example` is committed. Ruff: line length 100, rules E, F, I, B, UP, DJ, migrations excluded.

---

## Phase 1: Project skeleton, accounts, and base layout

**User stories**: 1, 2, 3, 4, 5, 6, 7, 65, 67, 68, 69

### What to build

Stand up the Django project and the `accounts` app with the custom user model in its first migration. A visitor can sign up (which logs them in), log in, log out from a navbar POST form, and change their password. `/` sends visitors to login and logged-in users to the watchlist URL; a placeholder watchlist page is acceptable until Phase 2. Protected pages redirect to login and return the user afterward.

The base layout has:
- a navbar (Search, My Watchlist, username, Log out);
- a messages area;
- a footer with the TMDB logo and the required notice.

The layout uses Tailwind + DaisyUI from committed compiled CSS and loads the vendored HTMX with the CSRF header on `<body>`. Settings read from `.env`, and `.env.example` is committed. Ruff is configured, and pytest runs offline with network access blocked. The custom user is registered in the admin.

### Acceptance criteria

- [ ] `uv sync`, `migrate`, and `runserver` work with no frontend build step.
- [ ] Sign up creates a user, logs them in, and lands on the watchlist URL.
- [ ] Login, POST-only logout, and password change work; GET logout does not log out.
- [ ] `/` redirects according to login state; a protected page redirects to login with `next` and returns afterward.
- [ ] Every page shows the TMDB logo and "This product uses the TMDB API but is not endorsed or certified by TMDB".
- [ ] `.env.example` lists `TMDB_API_KEY`; the app starts with no key set.
- [ ] Tests pass with no internet and no key; any attempted real network call fails the test.
- [ ] Ruff passes.

---

## Phase 2: WatchlistItem model and read-only My Watchlist page

**User stories**: 28, 29, 37, 38, 66

### What to build

Add the `WatchlistItem` model with all cached TMDB fields, user fields, timestamps, validators, and the unique constraint. Register it in the admin with status and media-type filters and title search.

`/watchlist/` lists only the current user's items, newest first, in the variant A table layout:
- poster, title, type, year, and status are shown;
- each row links to the (future) detail URL;
- no TMDB calls are made.

Show a friendly empty state with a link to Search. Posters fall back to an initials placeholder when the path is missing or the image fails to load. Items are created through the admin for now.

### Acceptance criteria

- [ ] Model defaults (status = plan), rating 1–10 validation, notes length validation, and the (user, tmdb_id, media_type) uniqueness are covered by tests; two users can save the same title.
- [ ] The watchlist shows only the logged-in user's items and makes no TMDB calls.
- [ ] The empty watchlist shows the empty state with a Search link.
- [ ] Items with no poster path render the initials placeholder; broken images switch to it too.
- [ ] The admin lists items with status and type filters and title search.

---

## Phase 3: TMDB search (client, page, HTMX, and paging)

**User stories**: 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 50 (decorator introduced here), 64

### What to build

Build the TMDB client:
- search for All / Movies / TV and a details call;
- All uses multi-search with people removed, while single-type results get their media type added;
- status codes map to the custom exception hierarchy, and a missing key or 401 is logged at error level.

`/search/` is a GET form (query, type, page):
- Without JavaScript it renders a full page.
- With HTMX it swaps only the results region and pushes the URL.
- Each result card shows poster, title, type, year, TMDB score, and a short overview.
- Previous/Next with "Page X of Y" uses TMDB's page counts; invalid page values fall back to page 1.

Error and empty states:
- Empty or whitespace-only queries show a prompt without calling TMDB.
- No results shows a "no movies or TV shows match" message.
- Unavailable and config errors render a friendly DaisyUI alert with a 200 response.

Introduce the HTMX-aware login-required decorator here and apply it to the search endpoint.

### Acceptance criteria

- [ ] Client tests (via `responses`) cover 200, 401, 404, 429, 5xx, timeout, connection error, invalid JSON, people filtering, per-type endpoint choice, and a missing key.
- [ ] Empty or whitespace query makes no TMDB call and shows the prompt.
- [ ] No-results, unavailable, and config-error states each render their message with HTTP 200 and no technical details.
- [ ] The HTMX request returns only the results fragment; the non-HTMX request returns the full page; the URL reflects q/type/page.
- [ ] Paging shows "Page X of Y" with working Previous/Next; a bad `page` value falls back to page 1.
- [ ] An anonymous HTMX request gets an `HX-Redirect` to login with `next`; an anonymous normal request gets a standard redirect.

---

## Phase 4: Save from search

**User stories**: 21, 22, 23, 24, 25, 26, 27

### What to build

Add the shared add-to-watchlist service. It takes a user, media type, and TMDB ID (plus optional user fields), fetches details, maps them to the cached fields, and creates the item; on fetch failure nothing is saved.

POST-only `/watchlist/add/` accepts just media type and TMDB ID and returns a fragment that replaces the Save button with one of four states:
- **Saved**, with an Edit link to the detail URL;
- **On watchlist**, including the unique-constraint race;
- **Not found**;
- **Couldn't save, try again**, with the button still available.

Non-HTMX POSTs redirect back to search with a message. Search results already on the user's watchlist show "On watchlist", found with one query for the user's (tmdb_id, media_type) pairs. New items start as Plan to watch.

### Acceptance criteria

- [ ] Saving creates an item with every cached field (title, year, poster, overview, genres, score, runtime or seasons, `cached_at`) and status plan.
- [ ] Each of the four fragment states is returned for its scenario; a second save of the same title never creates a duplicate or error page.
- [ ] A TMDB failure during save creates nothing and leaves a retryable button.
- [ ] Already-saved results show "On watchlist", and marking uses a single query.
- [ ] GET to the add URL is rejected; client-sent TMDB fields are ignored.
- [ ] Session-expired HTMX save triggers the login redirect.

---

## Phase 5: Organizing the watchlist

**User stories**: 30, 31, 32, 33, 34, 35, 36

### What to build

Add the shared filtering function. It takes a user-scoped queryset plus request parameters and applies:
- `q` (case-insensitive title substring);
- `status`;
- `media_type`;
- `sort`, from a whitelist: recent (default), title A–Z, rating high to low with nulls last, year newest, TMDB score high to low.

Unknown values are ignored.

Wire it into `/watchlist/`:
- search, status, type, and sort controls;
- 10 items per page with Previous/Next links that keep all current parameters;
- out-of-range pages show the nearest valid page;
- HTMX swaps the list region and pushes the URL;
- the filtered empty state links to search.

### Acceptance criteria

- [ ] The filter function is tested directly for each filter, each sort (including nulls-last rating), and invalid values.
- [ ] Pagination is 10 per page; links preserve q/status/media_type/sort.
- [ ] Out-of-range and non-numeric page values show the nearest valid page.
- [ ] HTMX requests return only the list region and update the URL; non-HTMX requests return the full page.
- [ ] A filtered view with no matches shows the empty state.

---

## Phase 6: Detail, editing, status change from the list, and delete

**User stories**: 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49

### What to build

`/watchlist/<id>/` shows the stored TMDB info (w342 poster or placeholder) and a model form for status, rating, and notes.
- A valid POST redirects back with a success message.
- An invalid POST re-renders with field errors (rating outside 1–10 or not whole; notes too long). A blank rating is allowed.

The detail page's Remove button opens a DaisyUI confirm modal that POSTs to `/watchlist/<id>/delete/`. Delete then redirects to the watchlist with a "Removed" message.

Each watchlist row gets a status dropdown that POSTs to `/watchlist/<id>/status/` on change. The endpoint validates the code, saves it, and returns the re-rendered row with a "Saved" indicator; it uses the HTMX login decorator.

All three endpoints look up items scoped to the current user.

### Acceptance criteria

- [ ] The detail page shows the cached TMDB fields and the user fields without calling TMDB.
- [ ] Form validation errors for rating and notes; blank rating saves; success message on save.
- [ ] Delete is POST-only, removes the item, and redirects with "Removed"; the modal is the only route to it in the UI.
- [ ] The status endpoint saves a valid code and returns the row with "Saved"; an invalid code is rejected without saving.
- [ ] Another user's item ID returns 404 on detail, edit, status, and delete.
- [ ] A session-expired status change triggers the HTMX login redirect.

---

## Phase 7: REST API

**User stories**: 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61

### What to build

Add DRF with session + token authentication and authenticated-only default permission. POST `/api/auth/token/` exchanges a username and password for a token.

A `ModelViewSet` at `/api/watchlist/`:
- its queryset is always limited to the request user; the owner is set from the request on create;
- list uses the shared filtering function with the website's parameter names and page-number pagination at 10 per page.

Create:
- requires media type and TMDB ID, with optional status, rating, and notes;
- calls the shared add service;
- a duplicate or TMDB not found returns 400;
- TMDB unavailable or config error returns 503 with a JSON detail, and nothing is saved.

Update and partial update change only status, rating, and notes. Identity, cached TMDB fields, timestamps, and id are read-only. Rating and notes validation returns 400 with field errors. Delete removes the user's own item.

### Acceptance criteria

- [ ] The token endpoint returns a token for valid credentials; requests work with that token or with a browser session.
- [ ] Anonymous requests to every API endpoint are refused.
- [ ] The list returns `count`/`next`/`previous`/`results`, 10 per page, honoring q/status/media_type/sort exactly as the website does.
- [ ] Create with only media type and TMDB ID returns 201 with server-filled TMDB fields; client-sent TMDB fields are ignored.
- [ ] Duplicate and unknown-TMDB-ID creates return 400 with a clear message; a TMDB outage returns 503 and saves nothing.
- [ ] PUT/PATCH change only status/rating/notes; attempts to change identity or TMDB fields have no effect; invalid rating/notes return 400.
- [ ] Retrieve, update, and delete on another user's item ID return 404.

---

## Phase 8: TMDB refresh command and README

**User stories**: 62, 63, 65 (README part)

### What to build

Add the shared refresh-item service, which re-fetches details and updates the cached fields and `cached_at`. The `refresh_tmdb` management command:
- selects items cached more than 150 days ago;
- refreshes each one through the service;
- logs and skips failures;
- prints a summary of refreshed and failed counts.

Write the README:
- setup: uv sync, `.env` from the example, migrate, runserver;
- the Tailwind watch command;
- running tests and Ruff;
- getting an API token, with example curl calls;
- running or scheduling the refresh command;
- why search caching and local poster storage were deliberately skipped (TMDB terms).

### Acceptance criteria

- [ ] Only items older than 150 days are refreshed; fresh items are untouched.
- [ ] Refreshed items have updated cached fields and a new `cached_at`.
- [ ] One failing item is logged and skipped while the rest refresh; the summary counts are correct.
- [ ] The README covers every topic listed above, and a fresh clone can be set up by following it.
