# Free media APIs for a "search, save, track" Django app

Researched 2026-11-11 using primary sources only (official docs, terms, and official GitHub repos). All pages were accessed on 2026-11-11. Where an official page could not be fetched, this note says so.

## 1. Question and bottom line

**Question:** Which free external APIs best support a Django app where users search for movies, TV, games, or music, save items to their own list, and add notes, ratings, or progress?

**Recommendation:**

1. **TMDB (movies and TV).** One key covers both domains. It offers search, detail, and posters, and IDs are stable integers. It is free for non-commercial use if you show the TMDB logo and notice, and the rate limit is about 40 requests per second. Storage rule: don't cache TMDB content for more than 6 months. Store the TMDB ID and refresh the display fields.
2. **IGDB (games).** Free, and it explicitly encourages you to store and serve the data yourself. The cost is setup friction: you need a Twitch account with 2FA, and your server must fetch and refresh a client-credentials token.
3. **MusicBrainz plus Cover Art Archive (music).** No key is needed, and the core data is CC0. You need a descriptive `User-Agent` and must stay at 1 request per second or less.

**TV episode-progress add-on or fallback:** TVmaze needs no key and has episode lists per show (`/shows/:id/episodes`), which suits an "episodes watched" counter. It is CC BY-SA, so credit TVmaze.
**Fallbacks:** OMDb for movies (simplest key, 1,000 requests per day, but non-commercial and its posters are for Patreon supporters only). RAWG for games, if its site is back up; it was unreachable when I checked.

## 2. Comparison

| Provider | Domain | Search? | Auth | Signup friction | Free limits | Storage / attribution |
|---|---|---|---|---|---|---|
| **TMDB** | Movies, TV | Yes | API key or Bearer read token | Low (account, then API settings) | ~40 req/s | Non-commercial only; logo and notice required; no caching over 6 months |
| **TVmaze** | TV + episodes | Yes (fuzzy) | None (public API) | None | 20 req per 10 s per IP | CC BY-SA 4.0, credit TVmaze; images cacheable indefinitely |
| **OMDb** | Movies, TV | Yes (`s=`) | API key (email) | Low | 1,000 req/day | Personal and non-commercial use only; Poster API for patrons only |
| **Trakt** | Movies, TV (tracking) | Yes | `trakt-api-key` (client_id); OAuth for user data | Medium (verified GitHub account; production review) | 500 GET per 5 min | Free incl. commercial; must cache images (no hotlinking); "uses Trakt" notice |
| **IGDB** | Games | Yes (Apicalypse) | Twitch client-credentials Bearer + Client-ID | Medium-high (Twitch, 2FA, app) | 4 req/s, 8 concurrent | Storing encouraged; free (commercial via partnership + attribution) |
| **RAWG** | Games | Yes | API key | Low | 20,000 req/month (not verified live) | Backlink on every page using data (not verified live) |
| **Giant Bomb** | Games | Yes | API key | Low | Not verified (page blocked) | Non-commercial (not verified) |
| **MusicBrainz** | Music | Yes (Lucene) | None for reads; UA required | None | ~1 req/s per IP | Core data CC0; supplementary CC BY-NC-SA |
| **Last.fm** | Music | Yes | API key | Low | Unstated ("several calls per second" can mean suspension) | Non-commercial; 100 MB storage cap; **images excluded** |
| **Spotify** | Music | Yes (max 10 per page) | OAuth (client credentials) | **High** (owner needs Premium; 5 users) | Unpublished quota | Commercial use barred; link back to Spotify required |
| **Discogs** | Music (releases) | Yes | Key/secret or token | Low | 60/min authed, 25/min unauthed (search snippet only) | Not verified (page blocked) |
| **Deezer** | Music | Yes | None for public catalog (unverified) | Unknown | Not verified | Not verified (docs need login) |
| **Jikan** (bonus) | Anime/manga (MAL) | Yes | None | None | 3/s, 60/min | Unofficial MAL scraper; respect MAL terms |
| **AniList** (bonus) | Anime/manga | Yes (GraphQL) | None for public reads | None | 90/min (currently 30/min) | **Bans use in competing list/tracker apps** |
| **Open Library** (bonus) | Books | Yes | None; UA + email recommended | None | 1/s (3/s if identified) | No bulk downloading |
| **Google Books** (bonus) | Books | Yes | API key | Low (Google Cloud) | Not stated on usage page | Not checked |

## 3. Per-provider details

### Movies and TV

#### TMDB (The Movie Database)
- **Data:** Search and detail endpoints for movies, TV, and people. Image URLs are `https://image.tmdb.org/t/p/{size}{file_path}`, e.g. `.../w500/1E5b...jpg` ([Image basics](https://developer.themoviedb.org/docs/image-basics)). The integer IDs are what you store in your models.
- **Rate limit:** "somewhere in the 40 requests per second range". The older 40-per-10-seconds limit was turned off on 2019-12-16. Respect 429 responses ([Rate limiting](https://developer.themoviedb.org/docs/rate-limiting)).
- **Auth:** Request a key from the API link in your account settings ([Getting started](https://developer.themoviedb.org/docs/getting-started)). Two options: an `api_key` query parameter, or the "API Read Access Token" as `Authorization: Bearer`. The Bearer token is the default and gives the same access ([Application auth](https://developer.themoviedb.org/docs/authentication-application)).
- **Terms:** "free to use for non-commercial purposes as long as you attribute TMDB"; commercial use needs a license ([FAQ](https://developer.themoviedb.org/docs/faq)).
  - You must use the TMDB logo and show the notice "This product uses the TMDB API but is not endorsed or certified by TMDB" ([FAQ](https://developer.themoviedb.org/docs/faq)).
  - Prohibited: caching "for longer than 6 months", making derivatives, and using TMDB data for AI/ML training. On termination you must purge cached content ([API Terms](https://www.themoviedb.org/api-terms-of-use)).
- **Django gotchas:**
  - Keep the token in settings or an environment variable.
  - In your saved-item model, store `tmdb_id` plus the media type, because movie and TV IDs are separate namespaces.
  - Treat the title and `poster_path` you store as a cache with a refresh timestamp under 6 months. This is my reading of the 6-month rule, not TMDB's wording.

#### TVmaze
- **Data:**
  - Show search: `/search/shows?q=` (fuzzy, ranked by relevance) and `/singlesearch/shows?q=` ([API](https://www.tvmaze.com/api)).
  - Lookup by IMDb or TheTVDB ID: `/lookup/shows` ([API](https://www.tvmaze.com/api)).
  - Show details: `/shows/:id`; episodes: `/shows/:id/episodes` and `/shows/:id/episodebynumber?season=&number=` ([API](https://www.tvmaze.com/api)).
  - Images come in "medium" and "original" sizes ([API](https://www.tvmaze.com/api)).
- **Rate limit:** "at least 20 calls every 10 seconds per IP"; responses return 429 when exceeded ([API](https://www.tvmaze.com/api)).
- **Auth:** None for the public API. A separate user-level API exists for Premium members ([API](https://www.tvmaze.com/api)).
- **Terms:** CC BY-SA 4.0, so credit TVmaze and follow ShareAlike. "Images can safely be cached indefinitely." Responses are cached for 60 minutes on TVmaze's side ([API](https://www.tvmaze.com/api)).
- **Gotcha:** The docs suggest storing the show ID or URL ([API](https://www.tvmaze.com/api)). Image URLs change when the primary image changes, so re-fetch rather than relying on stored image URLs.

#### OMDb
- **Data:** `s=` search with `type=movie|series|episode` and `page=1–100`; `i=` lookup by IMDb ID; `t=` lookup by title. Output is JSON (default) or XML. "The Poster API is only available to patrons" ([OMDb](https://www.omdbapi.com/)).
- **Limit and signup:** "FREE! (1,000 daily limit)". The key arrives by email ([API key page](https://www.omdbapi.com/apikey.aspx)).
- **Terms:** The site is for personal use, with no "commercial endeavors". Graphics and photographs are protected ([Legal](https://www.omdbapi.com/legal.htm)). The home page says content is "licensed under CC BY-NC 4.0" ([OMDb](https://www.omdbapi.com/)).
- **Gotcha:** IMDb `tt…` IDs are good to store. However, the 1,000/day cap is easy to hit if every search keystroke calls the API.

#### Trakt
- **Data:**
  - Search: `/search/movie?query=` and `/search/movie/exact?query=` (same pattern for `show`) ([Search guide](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/search.md)).
  - Media objects carry `trakt`, `slug`, `imdb`, and `tmdb` IDs ([Images guide](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/images.md)).
  - Images come via `?extended=full` in WebP. "All images are required to be cached in your app or server… Hotlinking images is not allowed and will be blocked" ([Images guide](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/images.md)).
- **Headers:** `trakt-api-key: <client_id>`, `trakt-api-version: 2`, `Content-Type: application/json`, and a `User-Agent`. All POST, PUT, and DELETE calls require OAuth ([Required headers](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/required-headers.md)).
- **Rate limits (Standard tier, updated 2026-10-13):** 500 GET calls per 5 minutes (unauthenticated limits apply per client ID and public IP), and 1 authenticated write per second ([Rate limits](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/rate-limiting.md)).
- **Signup:** Creating an app requires "a verified GitHub account". Apps start in Development mode (you plus 16 invitees). Production needs a review, a privacy policy link, and a "uses Trakt but is not endorsed" notice. There is no Client Secret by default; you must request one if your server exchanges tokens ([Create an app](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/create-an-app.md)).
- **Terms:** Standard access is "free for commercial and noncommercial use". Bulk harvesting and catalog mirroring are prohibited ([API Use Policy](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/api-use-policy.md)).
- **Verdict:** It is designed for syncing with a user's Trakt account, which is more than this project needs. Read-only metadata is possible, but TMDB is simpler. The live portal (developer.trakt.tv) is a JavaScript app that did not render for my fetch tool, so I read the same guides from Trakt's official repo.

### Video games

#### IGDB (owned by Twitch)
- **Signup:** You need a Twitch account with two-factor authentication and an app registered in the Twitch Developer Portal. Set the Client Type to Confidential to get a secret, and enter `localhost` as the OAuth redirect URL ([IGDB docs](https://api-docs.igdb.com/)).
- **Auth:**
  - Get a token with `POST https://id.twitch.tv/oauth2/token?client_id=…&client_secret=…&grant_type=client_credentials`. The response includes `expires_in` (example: 5,587,808 s, about 65 days), and the token "must be refreshed" ([IGDB docs](https://api-docs.igdb.com/)).
  - Send the headers `Client-ID` and `Authorization: Bearer …` ([IGDB docs](https://api-docs.igdb.com/)).
- **Requests:** Mostly POST to `https://api.igdb.com/v4/{endpoint}` with an Apicalypse body, e.g. `search "Halo"; fields name,cover.image_id;` ([IGDB docs](https://api-docs.igdb.com/)).
- **Images:** `https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg`. Sizes include `cover_small`, `cover_big` (264×374), and `_2x` retina variants ([IGDB docs](https://api-docs.igdb.com/)).
- **Rate limit:** "4 requests per second" and up to 8 open requests ([IGDB docs](https://api-docs.igdb.com/)).
- **Terms:** "free for non-commercial usage under the terms of the Twitch Developer Service Agreement"; commercial use goes through a partnership (partner@igdb.com) ([IGDB docs](https://api-docs.igdb.com/)).
  - Storing data is welcome: "we prefer if you store and serve the data to your end users" ([IGDB FAQ](https://api-docs.igdb.com/)).
  - The docs say it cannot be called directly from browsers because of CORS. Calls from a Django server are fine ([IGDB docs](https://api-docs.igdb.com/)).
- **Gotchas:**
  - Cache the token, for example in the Django cache or DB with its expiry, and re-fetch it on a 401.
  - Several field names changed in a 2025 migration (e.g. `category` → `type`), and the old names were removed after 31 August. Use the current field names ([IGDB docs, "Important Changes"](https://api-docs.igdb.com/)).

#### RAWG
- **Could not verify live.** rawg.io/apidocs, api.rawg.io/docs, and rawg.io/tos_api all returned HTTP 522 (origin down) on 2026-11-11. The following comes from search-engine extracts of those official pages and should be re-checked before relying on it:
  - Free tier is up to 20,000 requests per month.
  - You must "attribute RAWG as the source… and add an active hyperlink from every page where the data of RAWG is used".
  - The pricing tier and ToS wording disagree on whether commercial use is free ([apidocs](https://rawg.io/apidocs), [ToS](https://rawg.io/tos_api)).
- **Gotcha:** A provider whose own site is down is a risk for a graded demo.

#### Giant Bomb
- **Could not verify.** giantbomb.com/api returned HTTP 403 to my fetch tool. Search results came only from user forum threads, which are not primary sources, so no limits or terms are claimed here. If you consider it, check [giantbomb.com/api](https://www.giantbomb.com/api/) yourself.

### Music

#### MusicBrainz + Cover Art Archive
- **Data:**
  - Search: `/ws/2/<entity>?query=…&limit=&offset=`. Lookup: `/ws/2/<entity>/<MBID>?inc=…`, where MBIDs are UUIDs suitable for storing ([API](https://musicbrainz.org/doc/MusicBrainz_API)).
  - XML is the default; request JSON with `fmt=json` or `Accept: application/json` ([API](https://musicbrainz.org/doc/MusicBrainz_API)).
- **Auth:** None for reads. "Data submission, as well as requests that involve user information, require authentication" ([API](https://musicbrainz.org/doc/MusicBrainz_API)).
- **Rate limit:** "never make more than ONE call per second" ([API](https://musicbrainz.org/doc/MusicBrainz_API)). Over-limit requests from an IP get 503 errors ([Rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)).
- **User-Agent:** Required, e.g. `MyApp/1.0 ( me@example.com )`. Default library user-agents such as `Python-urllib` are throttled ([Rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)).
- **License:** Core data is CC0. Supplementary data is CC BY-NC-SA 3.0 ([Data license](https://musicbrainz.org/doc/About/Data_License)). "Non-commercial use of this web service is free" ([API](https://musicbrainz.org/doc/MusicBrainz_API)).
- **Cover art:** `https://coverartarchive.org/release-group/{mbid}/front-250|500|1200` returns a 307 redirect to the image, and the page states "no rate limiting rules" ([CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API)).
- **Gotchas:**
  - With `requests`, set the `User-Agent` header explicitly.
  - Throttle searches (debounce, cache results).
  - Use release-group MBIDs for "albums" so editions collapse into one entry.

#### Last.fm
- **Data:** `album.search`, `artist.search`, and `track.search`. Example: `ws.audioscrobbler.com/2.0/?method=album.search&album=…&api_key=…&format=json`. Search needs only an API key ([album.search](https://www.last.fm/api/show/album.search)).
- **Limits:** No number is published. "several calls per second" can lead to suspension. An identifiable `User-Agent` is requested ([Intro](https://www.last.fm/api/intro)).
- **Terms:**
  - Non-commercial use only ([ToS](https://www.last.fm/api/tos)).
  - Stored data is capped at 100 MB ([ToS](https://www.last.fm/api/tos)).
  - You must credit Last.fm and link to its pages ([ToS](https://www.last.fm/api/tos)).
  - Images and artwork are "expressly excluded" from the agreement ([ToS](https://www.last.fm/api/tos)).
- **Verdict:** Without the right to use images, it is a poor fit for a visual saved-items list.

#### Spotify Web API
- **Dev Mode (applies to all new apps):**
  - The app owner "must have a Spotify Premium account" ([Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)).
  - Only "Up to 5 authenticated Spotify users" ([Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)).
  - Extended quota is for organizations only (since 2025-05-15) and expects about 250k monthly active users ([Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)).
- **February 2026 changes:**
  - Search `limit` maximum dropped to 10 (default 5) ([Feb 2026 migration](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)).
  - Batch `GET /albums` and `GET /tracks` were removed; single-item GETs remain ([Feb 2026 migration](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)).
- **November 2024 restrictions for new apps:** Recommendations, Related Artists, Audio Features and Analysis, featured and category playlists, and preview URLs ([Nov 2024 blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)).
- **Auth:** The client-credentials token lasts 3,600 s and only reaches endpoints without user data ([Client credentials](https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow)).
- **Policy:**
  - Content must be attributed to Spotify, with a link back to the album or track ([Developer policy](https://developer.spotify.com/policy)).
  - Metadata and cover art may only be used "in connection with the underlying content" ([Developer policy](https://developer.spotify.com/policy)).
  - "commercial uses are not permitted" for streaming apps ([Developer policy](https://developer.spotify.com/policy)).
- **Verdict:** Ruled out for a student project. It requires a paid Premium owner account and has heavy restrictions.

#### Discogs
- **Could not fetch.** discogs.com/developers and its support ToS page returned HTTP 403. Search-engine extracts of the official docs mention:
  - 60 requests per minute authenticated and 25 per minute unauthenticated, per IP.
  - "Image requests require authentication."
  - ([Discogs developers](https://www.discogs.com/developers))
- Treat these as unverified. Discogs is strongest for physical releases and vinyl, which isn't needed here.

#### Deezer
- **Could not verify.** The docs at developers.deezer.com show "You have to login to accept the terms and conditions of the simple API" ([Deezer API](https://developers.deezer.com/api)). Endpoint, quota, and app-registration details were not visible without logging in.
- The guidelines page bans offline storage of audio. It does not address storing metadata ([Guidelines](https://developers.deezer.com/guidelines)).

### Bonus: anime and books

#### Jikan (unofficial MyAnimeList API)
- **Data:** Read-only GET endpoints for anime and manga, using MAL IDs ([Jikan README](https://github.com/jikan-me/jikan-rest)).
- **Rate limits:** 3 per second, 60 per minute, unlimited daily. MAL itself may still rate-limit ([Jikan OpenAPI description](https://github.com/jikan-me/jikan-rest/blob/master/storage/api-docs/api-docs.json)).
- **Caching:** Jikan caches responses for 24 hours ([Jikan OpenAPI description](https://github.com/jikan-me/jikan-rest/blob/master/storage/api-docs/api-docs.json)).
- **Status:** "not affiliated with MyAnimeList.net"; it "scrapes the website", and you must respect MAL's terms ([README](https://github.com/jikan-me/jikan-rest)).
- **Verdict:** The best anime option for this app type.

#### AniList
- **Rate limit:** 90 requests per minute, currently degraded to 30 per minute ([Rate limiting](https://github.com/AniList/docs/blob/master/docs/guide/rate-limiting.md)).
- **Terms:**
  - Using it "within competing, non-complementary services… including… anime and manga list or tracker services" is prohibited ([Terms](https://github.com/AniList/docs/blob/master/docs/guide/terms-of-use.md)).
  - Hoarding data is also prohibited, though AniList is "lenient" for school assignments ([Terms](https://github.com/AniList/docs/blob/master/docs/guide/terms-of-use.md)).
- **Verdict:** **Ruled out.** This app is a list tracker. (docs.anilist.co returned 403, so I read the official AniList/docs repo instead.)

#### Open Library
- **Data:** Search; works and editions as `/works/OL…W.json`; covers at `covers.openlibrary.org/b/{olid|isbn}/{value}-S|M|L.jpg` ([API](https://openlibrary.org/developers/api), [Covers](https://openlibrary.org/dev/docs/api/covers)).
- **Rate limits:** 1 request per second unidentified, 3 per second with a `User-Agent` plus email. No bulk downloading; use the data dumps instead ([API](https://openlibrary.org/developers/api)).
- **Covers:** Lookups by ISBN, OCLC, or LCCN are limited to 100 per 5 minutes; lookups by OLID or cover ID are unlimited ([Covers](https://openlibrary.org/dev/docs/api/covers)).

#### Google Books
- **Data:** `GET https://www.googleapis.com/books/v1/volumes?q=…&key=…`, with a maximum of 40 results. Stable volume `id`, and `imageLinks` thumbnails. OAuth is needed only for "My Library" ([Using the API](https://developers.google.com/books/docs/v1/using)).
- **Not covered:** The quota and terms of service were not checked.

## 4. Ruled out and caveats

- **Spotify:** Requires a Premium owner account, allows 5 users in Dev Mode, extended access is for organizations only, and commercial use is barred.
- **AniList:** Its terms forbid use in list or tracker apps.
- **Last.fm:** Images are excluded from the license, with a 100 MB storage cap and placement approval needed for attribution.
- **Trakt:** Usable but heavy (GitHub verification, production review, image caching duty). It is best only if you want to sync to users' Trakt accounts.
- **RAWG, Giant Bomb, Discogs, Deezer:** I could not verify these from live official pages on 2026-11-11 (522, 403, 403, and a login wall). Re-check them before choosing any.
- **Non-commercial everywhere:** TMDB, OMDb, MusicBrainz (free tier), Last.fm, and IGDB (free tier) are non-commercial or need a partnership for commercial use. A class project is fine; don't add ads or paid tiers.
- **Storage pattern that fits all of the recommended picks:** Your `SavedItem` model holds `provider`, `external_id`, cached `title`, `image_url` or `image_path`, `cached_at`, and the user's `status`, `rating`, `notes`, and `progress`. Refresh cached fields periodically; TMDB needs this at least every 6 months. Keep keys in environment variables, call APIs only server-side, and cache search responses briefly to respect rate limits.

## 5. Sources (all accessed 2026-11-11)

- TMDB: [Rate limiting](https://developer.themoviedb.org/docs/rate-limiting) · [Getting started](https://developer.themoviedb.org/docs/getting-started) · [Application auth](https://developer.themoviedb.org/docs/authentication-application) · [Image basics](https://developer.themoviedb.org/docs/image-basics) · [FAQ](https://developer.themoviedb.org/docs/faq) · [API Terms of Use](https://www.themoviedb.org/api-terms-of-use)
- TVmaze: [API docs](https://www.tvmaze.com/api)
- OMDb: [Home/docs](https://www.omdbapi.com/) · [API key](https://www.omdbapi.com/apikey.aspx) · [Legal](https://www.omdbapi.com/legal.htm)
- Trakt (official repo `trakt/trakt-api`, `projects/developer/src/lib/guides/`): [rate-limiting](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/rate-limiting.md) · [required-headers](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/required-headers.md) · [images](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/images.md) · [search](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/search.md) · [create-an-app](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/create-an-app.md) · [api-use-policy](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/api-use-policy.md) · [premium](https://github.com/trakt/trakt-api/blob/master/projects/developer/src/lib/guides/premium.md) · portal [developer.trakt.tv](https://developer.trakt.tv/) (did not render for my fetch tool)
- IGDB: [API docs incl. FAQ](https://api-docs.igdb.com/)
- RAWG: [apidocs](https://rawg.io/apidocs) · [API ToS](https://rawg.io/tos_api) (both returned HTTP 522)
- Giant Bomb: [API](https://www.giantbomb.com/api/) (returned HTTP 403)
- MusicBrainz: [API](https://musicbrainz.org/doc/MusicBrainz_API) · [Rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting) · [Data license](https://musicbrainz.org/doc/About/Data_License) · [Cover Art Archive API](https://musicbrainz.org/doc/Cover_Art_Archive/API)
- Last.fm: [Intro](https://www.last.fm/api/intro) · [API ToS](https://www.last.fm/api/tos) · [album.search](https://www.last.fm/api/show/album.search)
- Spotify: [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) · [Feb 2026 migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) · [Nov 2024 changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) · [Client credentials](https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow) · [Developer policy](https://developer.spotify.com/policy)
- Discogs: [Developers](https://www.discogs.com/developers) (returned HTTP 403)
- Deezer: [API](https://developers.deezer.com/api) · [Guidelines](https://developers.deezer.com/guidelines)
- Jikan: [jikan-rest README](https://github.com/jikan-me/jikan-rest) · [OpenAPI description](https://github.com/jikan-me/jikan-rest/blob/master/storage/api-docs/api-docs.json)
- AniList: [rate-limiting.md](https://github.com/AniList/docs/blob/master/docs/guide/rate-limiting.md) · [terms-of-use.md](https://github.com/AniList/docs/blob/master/docs/guide/terms-of-use.md)
- Open Library: [Developers API](https://openlibrary.org/developers/api) · [Covers API](https://openlibrary.org/dev/docs/api/covers)
- Google Books: [Using the API](https://developers.google.com/books/docs/v1/using)
