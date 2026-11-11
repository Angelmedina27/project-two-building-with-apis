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