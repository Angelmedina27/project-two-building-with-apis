# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-13 — Implemented Phase 6: Detail, editing, status change from the list, and delete

### Prompts
1. `/implement @prd/cinemovtracker.md @plans/cinemovtracker.md implement Phase 6`
2. Yes, I approve these three
3. Yes, I approve
4. Yes, move onto behavior 2
5. Yes, I approve
6. Yes, move onto behavior 3
7. Yes, I approve
8. Yes, go ahead
9. It passed, go ahead and update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude added `/watchlist/<id>/status/`, a POST-only view using `htmx_login_required` and scoped to the user's items:
    - It accepts only the five status codes; anything else gets a 400 and nothing is saved.
    - It returns the re-rendered row with "✓ Saved".
    - Each row moved into a new `_watchlist_row.html`, whose status dropdown posts on change and swaps only that row. The table gained a "My rating" column, as in prototype variant A.
  - Claude replaced the Phase 2 placeholder with the real detail page (`detail.html`) and deleted the placeholder template:
    - It shows the stored TMDB info: a w342 poster or initials placeholder, year, type, runtime or season count, genre badges, overview, TMDB score, and the cached date.
    - Its "Your tracking" card holds the new `WatchlistItemForm` from `watchlist/forms.py`, a model form for status, rating, and notes only, validated by the model's own validators.
    - A valid POST redirects back with "Saved your changes to …"; an invalid one re-renders with field errors.
  - Claude added `/watchlist/<id>/delete/`, POST-only and scoped to the user. It deletes the item and redirects to the watchlist with "Removed … from your watchlist." The only way to reach it in the UI is a DaisyUI `<dialog>` confirm modal on the detail page.
  - TDD covered three behaviors: the status quick-update (including rejecting an invalid code), detail form validation (out-of-range or fractional rating, notes too long, a blank rating allowed, the success message), and owner-only, POST-only delete.
  - Normal tests covered:
    - 404 for another user's item on view, edit, and status change;
    - the status endpoint rejecting GET;
    - the htmx login redirect after the session expires during a status change, returning to the current page;
    - the row dropdown markup;
    - the detail page showing cached fields for a movie and a TV show, poster or placeholder, with no TMDB call;
    - TMDB fields sent in the form being ignored;
    - the modal markup;
    - anonymous redirects for detail and delete.
  - The suite went from 134 to 146 tests. Ruff check and format pass, the CSS was rebuilt, and the CLAUDE.md structure notes list the new routes.
  - The user verified the phase manually in the browser.
- **Deviations:**
  - None. The user approved each proposed behavior and test as written.
- **Sideways:**
  - Claude's first scripted edit to `watchlist/views.py` crashed. Python read the file with the Windows default encoding instead of UTF-8 (the file contains curly quotes), so the stub view was never written and the first test run failed on a missing attribute rather than an assertion. Claude reran the edit with explicit UTF-8, and RED then failed on an assertion as intended.
  - After behavior 1, an existing Phase 5 test failed. It asserted that no option on the page was `selected` except the default sort, and the new row dropdowns always have a selected option. Claude noted this as a mechanical repair and limited the check to the controls form; what the test asserts did not change.

## 2026-11-13 — Implemented Phase 5: Organizing the watchlist

### Prompts
1. `/implement @prd/cinemovtracker.md @plans/cinemovtracker.md implement Phase 5`
2. Yes, I approve
3. Yes, I approve
4. Yes, move onto behavior 2
5. Yes, I approve
6. Yes, go ahead with behavior 3
7. Yes, I approve
8. Yes, go ahead
9. This phase passed. Go ahead and update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude added `watchlist/filters.py`, shared by the web list now and by the API in Phase 7:
    - `clean_filters(params)` keeps only recognized values: a trimmed `q`, a `status` from the model's choices, `movie`/`tv`, and a sort from the whitelist. Anything else becomes empty or the default sort. It accepts a dict or a `QueryDict`.
    - `filter_watchlist(queryset, params)` applies a case-insensitive title substring plus exact status and type filters. It then orders by the `SORTS` whitelist: recent (default), title A–Z, rating, year, and TMDB score. The last three put missing values last with `nulls_last=True`, and ties fall back to newest first.
  - Claude rebuilt `/watchlist/`:
    - It now uses `htmx_login_required` and the shared filter, with 10 items per page through `Paginator.get_page`. A non-numeric page shows page 1 and an out-of-range page shows the last one.
    - Previous/Next links keep every non-empty filter and leave out the default sort.
    - htmx requests get only `_watchlist_results.html`; history-restore and normal requests get the full page. Responses vary on `HX-Request`.
  - `list.html` gained a GET controls form (search, status, type, sort, Apply). htmx upgrades it to swap the list region and push the URL whenever a control changes or the form is submitted.
  - The list region shows the total match count, plus the rating and TMDB score on each row. A filtered view with no matches gets its own empty state with Clear filters and Search TMDB; a truly empty watchlist keeps the original one.
  - TDD covered three behaviors: combined filters with unknown values ignored, the rating sort with unrated last, and pagination falling back to the nearest valid page while keeping parameters. Normal tests covered the other sorts, each filter on its own, owner scoping, `QueryDict` input, 10 per page with `q`/`media_type` kept in links, no pagination on a single page, fragment versus full page (including history restore), the controls showing the current selection and the defaults, the filtered empty state, and anonymous htmx and normal redirects.
  - The suite went from 113 to 133 tests; Ruff check and format pass; the CSS was rebuilt for the new classes.
  - The user verified the phase manually in the browser.
- **Deviations:**
  - None. The user approved each proposed behavior and test as written.
  - When presenting behavior 3's test, Claude pointed out that it requires empty parameters to be left out of pagination links. The user accepted that without changes.
  - In behavior 2, Claude added all five sort orders, not just the rating one the test needed, because they are one data table. It said so in the GREEN summary.
- **Sideways:** Nothing went wrong. Each RED was a real assertion failure on the first run, with no scaffolding fixes needed.

## 2026-11-13 — Implemented Phase 4: Save from search

### Prompts
1. `/implement @prd/cinemovtracker.md @plans/cinemovtracker.md implement Phase 4`
2. Yes I approve the behaviors
3. Yes, I approve the test.
4. Yes, move onto behavior 2
5. Yes, I approve the test.
6. Yes go ahead with behavior 3
7. Yes, I approve the test.
8. Yes, go ahead
9. It passed. Go ahead and update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude added `watchlist/services.py` with `add_to_watchlist(user, media_type, tmdb_id, **user_fields)`:
    - It fetches TMDB details and maps title/name, year, poster, overview, the score rounded to one decimal (0 → none), joined genres, runtime (movies) or seasons (TV), and `cached_at`. Status defaults to plan.
    - It raises `AlreadyOnWatchlist` before calling TMDB when the title is already saved. It also raises it when a concurrent save hits the unique constraint, which is caught inside a savepoint and confirmed against the database.
    - TMDB errors propagate, and nothing is saved.
  - Claude added POST-only `/watchlist/add/` (`add_item`), protected by `htmx_login_required`:
    - It reads only `media_type` and `tmdb_id`; invalid values return 400 without calling TMDB.
    - htmx requests get the `_save_button.html` fragment in one of four states: Saved + Edit link, On watchlist, not found on TMDB, or Couldn't save, try again (with the button kept). Every state is a 200.
    - Plain form posts add a message and redirect back to the same-site `/search/` referer, otherwise to `/search/`.
  - Search result cards now include the Save slot. Already-saved titles show "On watchlist", found with one query on (tmdb_id, media_type) limited to the ids on the page.
  - TDD covered three behaviors: the service's field mapping, the four fragment states (including a real unique-constraint race), and the one-query marking. Normal tests covered TMDB failure in the service, duplicates, GET rejection (405), ignored client-sent fields, invalid input, the non-htmx redirect and messages, and the session-expired login redirects.
  - The suite went from 85 to 113 tests; Ruff check and format pass; the CSS was rebuilt for the new classes.
  - The user verified the phase manually in the browser.
- **Deviations:** None. The user approved each proposed behavior and test as written. "Nothing saved on TMDB failure" was tested as a normal test after behavior 1's GREEN, to keep to one test per cycle; Claude said so when presenting the test.
- **Sideways:**
  - Claude's first service stub raised `NotImplementedError`, which wouldn't have been a real assertion RED. It was changed to a no-op before the run.
  - Behavior 2's test expected an HTML-escaped apostrophe (`Couldn&#x27;t`), but Django doesn't escape literal template text. Claude made a mechanical fix to the expected string and noted it; what the test asserts didn't change.
  - The non-htmx redirect test followed the redirect onto the search page, which tried a real TMDB call and was caught by the network block. It was fixed by stubbing `tmdb.search` in that test.
  - `git status` showed a change to `PROMPTS.md` that Claude didn't make: the user's typo fix in the Phase 3 entry ("behavior 23" → "behavior 2"). Claude pointed it out and left it in place.

## 2026-11-13 — Implemented Phase 3: TMDB search (client, page, HTMX, and paging)

### Prompts
1. `/implement @prd/cinemovtracker.md @plans/cinemovtracker.md implement Phase 3`
2. Yes I approve the behaviors
3. Yes, I approve the test.
4. Yes, move onto behavior 2
5. Yes, I approve the test.
6. Yes, move onto behavior 3
7. Yes, I approve this test.
8. Yes, go ahead with the rest
9. Phase 3 passed. Now update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude added `watchlist/tmdb.py`, the only module that makes TMDB HTTP calls:
    - one private `_get()` with a 10-second timeout and the `api_key` query parameter
    - the exception hierarchy `TMDBError` > `TMDBNotFound`, `TMDBUnavailable` > `TMDBConfigError`
    - 404 → not found; timeout, connection error, 429, 5xx, other non-200s and invalid JSON → unavailable; missing key or 401 → config error, logged at error level without the key
    - `search()`: All uses multi-search with people removed; Movies and TV use their own endpoints, and the client adds the media type to their results; TMDB's page and total pages pass through
    - `get_details()`, plus `title_of()` and `year_of()` helpers for Phase 4
  - Claude added `watchlist/decorators.py` with `htmx_login_required`:
    - Logged-out HTMX requests get a 200 response with an `HX-Redirect` to login.
    - `next` is the request path for GETs. For POSTs it comes from `HX-Current-URL`, which must be on the same site; otherwise it's `/`.
    - Normal requests get Django's standard login redirect.
  - `/search/` replaced the placeholder:
    - It's a GET form that works without JavaScript. With htmx it swaps only the results region and pushes the URL.
    - It returns the full page on an htmx history-restore request and sets `Vary: HX-Request`.
    - Result cards show a w185 poster or initials, title, Movie/TV badge, year, ★ score and a short overview.
    - "Page X of Y" with Previous/Next links keeps q and type. Total pages are capped at TMDB's 500.
    - Invalid page values fall back to page 1, and an unknown type falls back to All.
    - Empty or whitespace queries show a prompt without calling TMDB. Also covered: no results, and friendly alerts for unavailable and config errors, all with a 200 response and no technical details.
  - Three behaviors were built test-first, each approved at its red and green steps:
    1. TMDB failures map to the exception hierarchy
    2. Each filter uses the right search endpoint and results contain only saveable titles
    3. The HTMX-aware login redirect
  - Normal tests cover the search page and the rest of the client: success, key and timeout, and the title/year helpers.
  - The CSS was rebuilt for the new DaisyUI classes, and CLAUDE.md's structure notes were updated.
  - All 83 tests and Ruff pass, and `manage.py check` passes with no key set. I verified the phase in my browser.
- **Deviations:**
  - I approved all three TDD behaviors and every test as proposed, without changes.
  - My "move onto behavior 23" was a typo; Claude read it as behavior 2 and said so.
  - Claude made a few choices the plan didn't spell out:
    - An unknown filter falls back to All in the client.
    - The decorator takes `next` for POST requests from `HX-Current-URL` and checks it against the current host.
    - Page values above 500 fall back to page 1 instead of being clamped.
    - `TMDBNotFound` during search shows the "unavailable" alert.
    - The pager is hidden when there's only one page.
- **Sideways:**
  - The first full test run had one failure, a mistake in Claude's own test. It expected "SH" initials for "Shōgun", but the `initials` filter takes one letter per word, so the right value is "S". Claude fixed the test, not the app.
  - Ruff's formatter rewrapped one line in `views.py`. No lint errors came up.
  - Claude didn't run the dev server itself. Checking in the browser was left to me, and it passed.

## 2026-11-11 — Implemented Phase 2: WatchlistItem model and read-only My Watchlist page

### Prompts
1. `/implement @prd/cinemovtracker.md @plans/cinemovtracker.md implement Phase 2`
2. Yes I approve those three
3. Yes, I approve the test
4. Yes move onto behavior 2
5. Yes, I approve the test.
6. Yes, move on to behavior 3.
7. Yes, I approve the test.
8. Yes, go ahead
9. Phase 2 passes. Please update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude added the `WatchlistItem` model in a single `0001` migration. It has:
    - the TMDB identity (`tmdb_id`, `media_type`) and every cached TMDB field
    - status (default "Plan to watch"), an optional 1–10 rating, and notes capped at 2,000 characters by a validator
    - `created_at` and `updated_at`, newest-first ordering, and a `unique_title_per_user` constraint
  - `WatchlistItem` is registered in the admin with status and media-type filters and title search.
  - `/watchlist/` now lists only the logged-in user's items in the variant A table: poster, linked title, year · type, and a colored status badge. It reads only the local database and never calls TMDB. An empty list shows a friendly message with a Search TMDB button.
  - Posters load from TMDB at w185. A new `initials` template filter and a reusable `_poster.html` partial show an initials placeholder ("Dune: Part Two" → DP) when there's no poster path, and an `onerror` swap shows it when an image fails to load.
  - Three behaviors were built test-first, each approved at its red and green steps:
    1. One title per user, while other users can save the same title
    2. The watchlist shows only my items, newest first
    3. The w185 poster or the initials placeholder
  - 12 more normal tests cover:
    - the status default
    - rating and notes validation
    - the admin filters and search
    - the empty state
    - the row links
    - the broken-image fallback
    - 404 for another user's detail URL
  - A `make_item` fixture was added to `conftest.py`.
  - All 38 tests and Ruff pass, and the CSS was rebuilt for the new classes. I verified the phase in my browser.
- **Deviations:**
  - I approved all three TDD behaviors and every test as proposed, without changes.
  - Claude added two things the plan didn't spell out:
    - a placeholder `/watchlist/<id>/` page, already scoped to the owner, so row links don't 404 before Phase 6
    - a default of the current time for `cached_at`, so items can be added in the admin without filling it in
  - Claude proposed the initials rule (first character of the first two words, uppercased) itself, and the poster test fixed it in place.
- **Sideways:**
  - Claude regenerated the uncommitted `0001` migration twice instead of stacking new migrations: once to add the unique constraint after the RED step, and once for the `cached_at` default.
  - Ruff's formatter reformatted one file. No lint errors came up.
  - Claude didn't run the dev server itself. Checking in the browser was left to me, and it passed.

## 2026-11-11 — Implemented Phase 1: project skeleton, accounts, and base layout

### Prompts
1. `/implement @prd/cinemovtracker.md @plans/cinemovtracker.md implement Phase 1`
2. Yes I approve those three
3. Yes I approve this test
4. Yes, continue to behavior 2
5. Yes I approve the test
6. Yes, continue onto behavior 3
7. Yes
8. Yes go ahead
9. Phase 1 passes in the browser and the TMDB logo is saved at static/img/tmdb-logo.svg. Please update CLAUDE.md with only the verified commands and actual folder structure created in Phase 1, and update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude checked PyPI before installing. It added Django 6.1.3 (officially supports Python 3.14), DRF 3.18.3, and the dev tools: pytest, pytest-django, responses, ruff, and pytailwindcss.
  - It created the `config` project, the `accounts` app, and a `watchlist` app. The custom `User` model is in the first migration and registered in the admin.
  - Accounts features:
    - sign-up, which logs the new user in and goes to the watchlist
    - Django's built-in login, POST-only logout, and password change
    - `/` redirects by login state
    - login-protected placeholder pages for `/watchlist/` and `/search/`
  - `base.html` has the navbar, the messages area, the HTMX CSRF header on `<body>`, and a footer with the TMDB logo and notice.
  - Frontend files:
    - Tailwind v4.3.5 runs through pytailwindcss with the vendored DaisyUI 5.7.50 plugin, and the compiled CSS is committed.
    - HTMX 2.0.11 is vendored as a pinned static file.
  - `.env.example` lists `TMDB_API_KEY`. Settings read `.env` and fall back to safe dev defaults.
  - Ruff is configured in `pyproject.toml`.
  - Three behaviors were built test-first, each approved at its red and green steps:
    1. A suite-wide fixture that blocks the network
    2. The `/` and `next` redirects
    3. Sign-up
  - 20 more normal tests cover logout, login, password change, invalid sign-up, attribution on every page, the layout, messages, starting without a key, and the admin.
  - All 23 tests and Ruff pass. A real `runserver` was checked with curl. I verified the phase in my browser.
  - CLAUDE.md now lists the verified commands and the actual folder structure.
- **Deviations:**
  - I approved all three TDD behaviors and every test as proposed, without changes.
  - Claude added two things the plan didn't spell out:
    - a placeholder `/search/` page, so the navbar link doesn't 404 before Phase 3
    - a sign-up guard that sends logged-in users to their watchlist. Claude said this was outside strict TDD and covered it with a normal test.
- **Sideways:**
  - Downloading the TMDB logo returned 403. A retry with a browser user agent was blocked by the auto-mode classifier as bot-check circumvention. Claude stopped and asked me to download the logo by hand, which I did.
  - Claude's first messages test asserted nothing useful. It caught this itself and replaced it with one that renders a message through `base.html`.
  - The first full test run took 24 seconds because of PBKDF2 password hashing. Claude added an autouse fixture that switches tests to a fast hasher, which brought the run down to about 2 seconds.
  - Ruff flagged B904 in `scripts/tmdb_check.py`. Claude added exception chaining (`from error`), which doesn't change behavior. Ruff's formatter also removed the parentheses from an `except` clause, a form that is valid in Python 3.14.

## 2026-11-11 — Wrote the initial CLAUDE.md from the PRD

### Prompts
1. Create the initial CLAUDE.md for this project and keep it to about 20 to 30 lines. Include only a one-line project description, the approved technology stack and package manager, durable project-wide architecture decisions already established in the PRD, and short pointers to the PRD, plan, and prototypes instead of repeating their details. Do not add commands yet because the project tooling has not been installed or verified. Do not predict project structure, paths, template conventions, URL conventions, or testing commands that do not exist yet. Do not copy business requirements, user stories, implementation phases, rejected alternatives, or detailed feature rules into CLAUDE.md, and do not invent new architectural conventions.
2. I approve this initial CLAUDE.md. Please update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude read the PRD's Implementation Decisions section, `pyproject.toml`, `.python-version`, the README, and the list of files in the repo.
  - It wrote a 29-line `CLAUDE.md` at the repo root with these sections:
    - **Description:** one line saying what the app is.
    - **Stack:** the approved stack, with uv as the only package manager and no Node.js.
    - **Architecture decisions:** seven taken from the PRD:
      - the custom user model from the first migration
      - one TMDB client that raises a `TMDBError` hierarchy
      - TMDB data fetched and cached on the server, never supplied by the client
      - shared services and filtering for the web views, API, and refresh command
      - every lookup limited to the current user, with 404 for another user's item
      - session and token auth for the API
      - secrets in `.env`, and a missing key never stops Django from starting
    - **TMDB terms:** the logo and notice on every page, and cached data kept under 6 months old.
    - **References:** pointers to the PRD, the plan, the variant A prototype, and the research note.
  - I approved it as written. It wasn't committed in this session.
- **Deviations:**
  - No questions were asked and no recommendation was overridden.
  - Claude chose to leave out the `config`, `accounts`, and `watchlist` package names, the URL routes, and the Ruff rule settings, even though the PRD names them. It treated them as predicted structure or tooling details, as the prompt asked, and said so in its summary.
- **Sideways:**
  - The first combined read of the PRD, config, README, plan, and prototype produced too much output and was saved to a file. Claude then read the PRD's stack and architecture sections with a targeted search and a line-range read. The plan and prototype were only referenced by path, not read.

## 2026-11-11 — Turned the Cinemovtracker PRD into an 8-phase plan made of thin, end-to-end slices

### Prompts
1. `/prd-to-plan`
2. Yes this level of detail works for me. Yes go ahead and combine those that you suggested. 3 and 4 combined, 7 and 8 combined, and 9 and 10 combined. Also just keep phase 2 as it is with the model and read-only watchlist.
3. Update PROMPTS.md with our session log using the standard format.

### Summary
- **Outcome:**
  - Claude read `prd/cinemovtracker.md` and the existing repo. There's no Django code yet, only the TMDB check script and the research note.
  - It proposed 11 thin phases, each cutting through every layer and listing the PRD user stories it covers. I approved combining the search phases (3 + 4), the editing phases (7 + 8), and the API phases (9 + 10).
  - The final plan was written to `plans/cinemovtracker.md`. It has 8 phases:
    1. Project skeleton, accounts, and base layout
    2. WatchlistItem model and a read-only My Watchlist page
    3. TMDB search
    4. Save from search
    5. Organizing the watchlist
    6. Detail page, editing, status change from the list, and delete
    7. REST API
    8. `refresh_tmdb` command and README
  - The plan opens with the decisions every phase relies on: URLs, the model, which app owns what, login, frontend, testing, and config. Each phase has its own acceptance checklist.
  - Claude's project memory was updated to say the plan is approved and Phase 1 is next. No application code was written.
- **Deviations:**
  - Claude asked three questions: was the level of detail right, which phases should be combined, and should Phase 2 add the model before saving from search exists (so Phase 2 could only be checked using the admin).
  - I accepted all three suggested merges and kept Phase 2 as proposed. No recommendation was overridden.
- **Sideways:**
  - The PRD wasn't already loaded in the conversation, as the skill expects, so Claude found it in `prd/` instead of asking me for it.
  - The first command that read the PRD, README, config, and memory files produced too much output and was saved to a file. Claude then read that file in full.
  - The PRD didn't specify the exact login and account URLs, so Claude picked Django's standard `/accounts/…` paths and said so in its summary.

## 2026-11-11 — Designed Cinemovtracker in a grill-me session, prototyped the watchlist editing UI, and wrote the PRD

### Prompts
1. `/grill-me` I want to build a new Django app called Cinemovtracker that lets users search for movies and TV shows and save them to a personal watchlist. I am building this with Django, Django REST Framework, uv, SQLite, Ruff, Tailwind CSS with DaisyUI, HTMX for interactivity, and pytest. Based on my research in docs/research/free-media-apis.md and scripts/tmdb_check.py, logged-in users need to be able to search the TMDB API for movies and shows, save them locally so they work offline, and add their own watch status, personal rating, and notes. Users also need to search, filter, sort, and paginate their saved watchlist, and the app needs a full CRUD DRF API where users must log in and can only view or change their own items. Finally, make sure it handles empty searches and TMDB API errors cleanly without crashing.
2. Option A (data model: one `WatchlistItem` table)
3. Option A (duplicates: unique constraint on user + tmdb_id + media_type)
4. Option B (five watch statuses)
5. Option A (rating: whole number 1–10)
6. Option B′ (on save, server fetches TMDB details and stores the richer field set)
7. Option A (6-month rule: `refresh_tmdb` management command)
8. Yes I am okay with the customer user model. Option A
9. Option B and yes include the filters
10. Option B (TMDB paging: Prev/Next with per-type search endpoints)
11. Option A (Save button: in-place HTMX swap)
12. `/prototype` Before I pick choose, build a quick UI prototype comparing how the My Watchlist page and item editing flow look for each option.
13. After looking at the options, I want to go with option A
14. Option B (watchlist: title search, status/type filters, 5 sorts, 10 per page)
15. Option B (API auth: session + token)
16. Option A (API: TMDB identity set once on create; 503 on TMDB outage)
17. Option A (shared filtering function for web and API)
18. Option A (TMDB client module with an exception hierarchy; never crash on a missing key)
19. Option A (tests: `responses` for HTTP, `monkeypatch` for views/API)
20. Option A (frontend: Tailwind standalone CLI + DaisyUI plugin file + local HTMX)
21. Option A (layout: `config` project with `accounts` and `watchlist` apps)
22. Option A (posters from TMDB's image server with a placeholder fallback)
23. Option A (no TMDB search caching)
24. Option A (HTMX-aware login redirect)
25. Option A (out-of-scope list accepted as proposed)
26. `/to-prd`
27. Update PROMPTS.md with our session log using the standard format

### Summary
- **Outcome:** A 23-question grill-me session settled the Cinemovtracker design: data model, duplicates, statuses, rating, cached TMDB fields, the 6-month refresh, accounts, TMDB search and paging, the Save flow, editing UI, watchlist controls, API auth and contract, shared filtering, the TMDB error hierarchy, the test strategy, frontend tooling, project layout, posters, caching, HTMX login redirects, and scope. The questions about editing and deleting were answered with a throwaway UI prototype, `prototypes/watchlist-edit.html`, which compares three variants (A, B, C) with a switcher, a request log, and a state panel. Variant A was chosen, and the decision is recorded at the top of that file. The PRD was written to `prd/cinemovtracker.md`, with 69 user stories, the implementation decisions, the out-of-scope list, and notes. A summary of the decisions was also saved to Claude's project memory. No application code was written.
- **Deviations:**
  - For question 1, I chose Option A (one `WatchlistItem` table) over the recommended Option B (a shared `Title` table plus `WatchlistEntry`). This accepts duplicated TMDB data per user in exchange for a simpler model.
  - For question 11 (editing UI), I asked for a UI prototype before deciding instead of answering directly, then picked A, the recommended option.
  - Every other answer matched the recommendation. A few sub-questions were never answered explicitly and were treated as accepted: "Plan to watch" as the default status, rating being optional, 503 for TMDB outages, and the `/` redirect. So were the defaults Claude stated without asking: Django version, admin, Ruff rules, and `.env` settings.
- **Sideways:**
  - In question 5, Claude realized partway through its own question that the "never trust client TMDB data" rule meant both original options needed a server-side TMDB call. It rewrote the options as A′/B′ inside the same message instead of starting the question over.
  - Node.js isn't installed, so the prototype's JavaScript couldn't be syntax-checked. The prototype was opened in the browser but not verified by Claude. This finding also shaped question 18: standalone Tailwind CLI, no Node.
  - The first command that read the research note produced too much output and was saved to a file. The relevant TMDB sections were then read with a targeted search.
  - The prototype loads Tailwind and DaisyUI from CDNs, which is fine for a throwaway file. The real app will serve them locally so it works offline.

## 2026-11-11 — Researched free media APIs, chose TMDB, built a TMDB check script with uv

### Prompts
1. `/research` Find free external APIs for a Django application where users search for items, save them, and add their own notes, ratings, or progress. Explore topics such as movies, television, games, or music. Compare promising providers using official documentation, including available data, free limits, signup requirements, etc...
2. Let's go with TMDB
3. `/grill-me` I want to write a short console script (in scripts/) to verify that I can access the TMDB API using my TMDB_API_KEY in .env before building my project. This script belongs to a future Django project that will use uv, so please set it up with uv. It needs to accept user input (like a movie/TV search phrase), fetch results from TMDB, display the title, release date, and details clearly, and handle empty results or failed requests cleanly.
4. Option A (uv setup: root `pyproject.toml` via `uv init`)
5. Option A (HTTP library: `requests`)
6. Option A (loading `.env`: `python-dotenv`)
7. Option A (search endpoint: `/search/multi`)
8. Option B (details: search, then pick a result for `/movie/{id}` or `/tv/{id}`)
9. Option A (interaction: loop until quit)
10. Option A (errors: specific message per case, keep looping)
11. Option A (structure: one file, small functions, no automated tests)
12. Yes build it
13. Walk me through scripts/tmdb_check.py briefly so I understand how the API requests get made, retrieved, and displayed.
14. Okay good, Update PROMPTS.md with our session log using the standard format

### Summary
- **Outcome:** A background agent wrote `docs/research/free-media-apis.md`, comparing movie/TV, game and music APIs from official docs. It recommended TMDB for movies and TV, IGDB for games and MusicBrainz for music, with TVmaze as an option for episode tracking. TMDB was chosen. A grill-me session settled 8 design decisions. Then a uv project was set up at the repo root (`pyproject.toml`, `uv.lock`, `.python-version` for Python 3.14, with `requests` and `python-dotenv`), and `scripts/tmdb_check.py` was built. It was run against the live API: movie and TV searches with details, no-results, invalid menu input, a bad key (401), a missing key, no connection, and quitting all behaved as designed. The session ended with a walkthrough of how the script makes, retrieves and displays requests.
- **Deviations:** None. Every grill-me answer matched the recommended option, including Option B for question 5. One follow-up question asked for the script walkthrough.
- **Sideways:**
  - Research gaps: RAWG returned "server down" (522), and Discogs and Giant Bomb refused access (403). Deezer's docs need a login. RAWG's and Discogs' limits come only from search snippets, and the note flags all four providers as unverified.
  - Trakt's and AniList's docs sites wouldn't load, so their details were read from their official GitHub repos instead.
  - The research agent did the reading itself rather than spawning another background agent as the research skill describes.
  - `uv init --bare` didn't create `.python-version`, so it was added with `uv python pin 3.14`.
  - The 404, 429, 5xx and timeout messages weren't tested, because those errors couldn't easily be triggered.
  - VS Code showed Pylance "import could not be resolved" warnings because it wasn't using the project's `.venv`. The fix is to select `.venv\Scripts\python.exe` as the interpreter.