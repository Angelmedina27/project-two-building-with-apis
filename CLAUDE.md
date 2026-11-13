# Cinemovtracker

A Django web app and DRF API where logged-in users search TMDB for movies and TV shows and keep a personal watchlist.

## Stack
- Python 3.14, managed with **uv** (the only package manager; no Node.js on the dev machine).
- Django (latest stable supporting 3.14 — confirm version at build time), Django REST Framework, `requests`, `python-dotenv`, SQLite.
- Frontend: server-rendered Django templates, Tailwind CSS + DaisyUI built via pytailwindcss, HTMX as a local pinned static file. No JS framework.
- Dev: pytest, pytest-django, responses, ruff.

## Architecture decisions
- Custom user model set as the auth user model from the first migration.
- All TMDB HTTP calls go through one client module that raises a `TMDBError` hierarchy; views and the API catch only those, never raw `requests` exceptions.
- TMDB details are fetched server-side and cached locally on save; clients never supply TMDB field values. The watchlist itself never calls TMDB.
- Web views, the API, and the refresh command share the same add/refresh services and the same watchlist filtering function.
- Every item lookup is scoped to the requesting user; another user's item returns 404.
- API auth is session + DRF token; authenticated users only.
- Secrets and the TMDB API key come from a git-ignored `.env`; a missing key must not stop Django from starting.

## TMDB terms (non-negotiable)
- TMDB logo and the non-endorsement notice on every page; non-commercial only.
- Cached TMDB data must not be older than 6 months (refreshed at 150 days).

## Commands
- Install deps: `uv sync`
- Migrate / run: `uv run python manage.py migrate`, `uv run python manage.py runserver`
- Tests: `uv run pytest` (offline; real network calls fail the test)
- Lint / format: `uv run ruff check .`, `uv run ruff format .`
- Rebuild CSS (commit the output): `uv run tailwindcss -i static/src/input.css -o static/css/app.css --minify`

## Structure
- `config/` — settings (reads `.env`) and root URLs.
- `accounts/` — custom `User`, sign-up form/view, auth URLs under `/accounts/`.
- `watchlist/` — `/` redirect, `/watchlist/` list, `/search/` (HTMX results fragment or full page), `/watchlist/add/`, `/watchlist/<id>/` detail + `forms.py` edit form, `/watchlist/<id>/status/` (row fragment), `/watchlist/<id>/delete/` (POST); `tmdb.py` is the only TMDB HTTP client; `decorators.py` has `htmx_login_required` (use it on every HTMX endpoint).
- `templates/` — `base.html` (navbar, messages, TMDB footer), `registration/`, `accounts/`, `watchlist/`.
- `static/` — `src/` (Tailwind input + vendored DaisyUI plugin), `css/app.css` (compiled), `js/htmx.min.js`, `img/tmdb-logo.svg`.
- `tests/` — pytest suite; `conftest.py` blocks the network and provides `user`/`other_user`.

## References
- PRD: `prd/cinemovtracker.md`
- Implementation plan: `plans/cinemovtracker.md`
- Approved editing UI prototype (variant A): `prototypes/watchlist-edit.html`
- API research: `docs/research/free-media-apis.md`
