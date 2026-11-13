# Cinemovtracker

CIDM 3312 Project #2. A Django web app and REST API where logged-in users search
[The Movie Database (TMDB)](https://www.themoviedb.org/) for movies and TV shows and keep a
personal watchlist with their own status, rating (1–10), and notes.

- Search TMDB by title (All / Movies / TV) and save results with one click.
- Saved titles keep a local copy of their TMDB details, so the watchlist works even when TMDB
  is down or you are offline (posters and search need internet access).
- Search, filter, sort, and page through your watchlist; change status inline; edit or remove
  titles from a detail page.
- A token- or session-authenticated REST API with full CRUD over your own watchlist.

This product uses the TMDB API but is not endorsed or certified by TMDB.

## Stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- Django 6.1, Django REST Framework, `requests`, `python-dotenv`, SQLite
- Server-rendered templates with Tailwind CSS + DaisyUI and HTMX 2 (vendored in `static/`).
  There is no Node.js and no JavaScript framework.
- Dev tools: pytest, pytest-django, responses, Ruff, pytailwindcss

## Setup

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). uv installs Python 3.14
for you if you don't have it.

```bash
git clone <this repo>
cd project-two-building-with-apis
uv sync                       # creates .venv and installs all dependencies
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
```

Edit `.env` and set `TMDB_API_KEY` to your TMDB **v3 API key**. You can find it at
<https://www.themoviedb.org/settings/api> (a free TMDB account is required). The app starts
without a key, but search and saving show a "search isn't configured" message until one is set.
`SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are optional and have development defaults.
`.env` is git-ignored, so never commit it.

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser   # optional, for /admin/
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/>, sign up, and start searching. No frontend build step is needed
because the compiled CSS (`static/css/app.css`) is committed.

## Working on the styles (Tailwind)

Tailwind runs as the standalone CLI through `pytailwindcss`, so no Node.js is needed. The first
run downloads the CLI binary. DaisyUI is loaded as a plugin file from `static/src/`.

```bash
# Rebuild on every template change while developing:
uv run tailwindcss -i static/src/input.css -o static/css/app.css --watch

# One-off minified build (do this before committing):
uv run tailwindcss -i static/src/input.css -o static/css/app.css --minify
```

Commit `static/css/app.css` after changing styles or adding new classes to templates.

## Tests and linting

```bash
uv run pytest              # full suite; runs offline and needs no TMDB key
uv run ruff check .        # lint
uv run ruff format .       # format
```

The tests never touch the network. A suite-wide fixture makes any real connection attempt
fail the test. TMDB HTTP behavior is tested with `responses`, and views and the API use faked
client functions.

## REST API

Every endpoint requires authentication, either a DRF token or a logged-in browser session (the
browsable API works at <http://127.0.0.1:8000/api/watchlist/>). Each user sees and changes only
their own items, and another user's item ID returns 404.

| Method | URL | Purpose |
| --- | --- | --- |
| POST | `/api/auth/token/` | Exchange `username` + `password` for a token |
| GET | `/api/watchlist/` | List your items (paginated, 10 per page) |
| POST | `/api/watchlist/` | Add a title by `media_type` + `tmdb_id` |
| GET | `/api/watchlist/<id>/` | Retrieve one item |
| PUT / PATCH | `/api/watchlist/<id>/` | Update `status`, `rating`, `notes` |
| DELETE | `/api/watchlist/<id>/` | Remove an item |

The list accepts the same query parameters as the website:
- `q`: title contains, case-insensitive.
- `status`: one of `plan`, `watching`, `watched`, `on_hold`, `dropped`.
- `media_type`: `movie` or `tv`.
- `sort`: `recent` (default), `title`, `rating`, `year`, or `score`.
- `page`: page number.

Example session with curl:

```bash
# 1. Get a token
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
     -d "username=alice" -d "password=your-password"
# {"token":"9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

TOKEN=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# 2. Add a title. Only the identity is sent; the server fetches the TMDB details.
curl -X POST http://127.0.0.1:8000/api/watchlist/ \
     -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     -d '{"media_type": "movie", "tmdb_id": 693134, "status": "watching"}'

# 3. List what you're watching, best rated first
curl "http://127.0.0.1:8000/api/watchlist/?status=watching&sort=rating" \
     -H "Authorization: Token $TOKEN"

# 4. Rate it and add notes
curl -X PATCH http://127.0.0.1:8000/api/watchlist/1/ \
     -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     -d '{"status": "watched", "rating": 9, "notes": "Loved the sandworms."}'

# 5. Delete it
curl -X DELETE http://127.0.0.1:8000/api/watchlist/1/ -H "Authorization: Token $TOKEN"
```

Errors:
- **400**: invalid input, a title that's already on your watchlist, or a TMDB ID that doesn't
  exist.
- **401**: no or bad credentials.
- **404**: the item doesn't exist or isn't yours.
- **503**: TMDB is unavailable while adding a title. Nothing is saved, so try again later.

`media_type`, `tmdb_id`, and all TMDB fields can't be changed after creation. To switch to a
different title, delete the item and add the new one.

## Keeping TMDB data fresh (`refresh_tmdb`)

TMDB's terms forbid caching their content for more than 6 months. The `refresh_tmdb` command
re-fetches the details of every saved title cached more than **150 days** ago, which leaves a
safety margin. Your status, rating, and notes are never touched. A title that fails to refresh
(TMDB down, title removed, bad key) is logged and skipped, and the run continues. The command
finishes with a summary:

```bash
uv run python manage.py refresh_tmdb
# Refreshed 12 item(s); 1 failed.
```

Run it at least monthly. To schedule it daily:

- **Windows (Task Scheduler):**

  ```powershell
  schtasks /Create /SC DAILY /ST 03:00 /TN "Cinemovtracker refresh" `
    /TR "cmd /c cd /d C:\path\to\project-two-building-with-apis && uv run python manage.py refresh_tmdb"
  ```

- **macOS / Linux (cron):** `crontab -e`, then add:

  ```cron
  0 3 * * * cd /path/to/project-two-building-with-apis && uv run python manage.py refresh_tmdb
  ```

## Design notes: what was deliberately skipped

- **No caching of TMDB search responses.** Search runs only when you submit a query, so TMDB's
  rate limit (around 40 requests per second) isn't a realistic risk. A 429 response is still
  handled as "TMDB unavailable". Caching search results would also mean tracking another set of
  TMDB content against the 6-month rule for no real benefit. Only the details of titles you save
  are stored, and `refresh_tmdb` keeps those within the limit.
- **No local poster storage.** Posters are loaded directly from TMDB's image server
  (`image.tmdb.org`), at w185 in lists and w342 on the detail page. Downloading them would mean
  storing more TMDB content that would also need refreshing and purging under the terms. When a
  poster is missing or can't load (for example, offline), a placeholder with the title's
  initials is shown instead.

## Project layout

```
config/       settings (reads .env) and root URLs
accounts/     custom User model, sign-up
watchlist/    model, TMDB client (tmdb.py), services, filtering, views, forms,
              api/ (DRF), management/commands/refresh_tmdb.py
templates/    base layout (navbar, messages, TMDB footer) and page templates
static/       Tailwind input + DaisyUI plugin, compiled CSS, vendored HTMX, TMDB logo
tests/        pytest suite
```

Planning documents: `prd/cinemovtracker.md` (requirements), `plans/cinemovtracker.md`
(implementation phases), `prototypes/watchlist-edit.html` (approved editing UI), and
`docs/research/free-media-apis.md` (API research).

## TMDB attribution

<img src="static/img/tmdb-logo.svg" alt="TMDB logo" width="120">

This product uses the TMDB API but is not endorsed or certified by TMDB. Data and images come
from [TMDB](https://www.themoviedb.org/). The app is non-commercial.
