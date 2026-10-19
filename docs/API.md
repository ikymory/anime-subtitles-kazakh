# API contract

Static Pages base: `https://ikymory.github.io/anime-subtitles-kazakh`. OpenAPI 3.1: [`/openapi.json`](../dist/openapi.json).

| Static path | Result |
| --- | --- |
| `/api/v1/anime.json` | `{total, total_episodes, total_files, language, data}` |
| `/api/v1/anime/{slug}.json` | Release metadata, actual track numbers and download manifest |
| `/api/v1/stats.json` | Measured counts, publishing profile and quality summary |
| `/api/v1/audit.json` | Full source audit and review findings |

`total` counts release entries, including entries with zero usable tracks. `total_episodes` counts usable tracks. `source_episode_tracks` in stats counts all archived tracks. `total_files` counts source files including naming aliases; use `published_format_files` for the staged site's actual download count. `episodes`, `id`, artwork and ratings are inherited unverified metadata. `catalog_id`/`slug` are stable identifiers. `translated_episodes` is the actual list, including episode zero and noncontiguous values. Do not construct ranges from counts.

`subtitles` is an array of `{episode, language, filename, files, assets}`. Each format's `files` value is an absolute URL or null. `assets` includes the relative path, bytes, SHA-256, cue count and origin (`source` or `derived`). Derived ASS uses a simple default style. Pages publishes canonical SRT/VTT to fit its 1 GB budget; full self-hosted builds support ASS too. Legacy source aliases remain in the Git archive; Pages alias URLs are no longer published. Use the manifest for current URLs.

Static Pages is read-only, with no server-side query execution. Fetch the catalog once and filter locally. Numeric alias documents can contain `{error, matches}` with HTTP 200 because Pages is static. Slug endpoints avoid collisions. Missing static files can be HTML 404 responses, so always check `response.ok` before decoding JSON. Pages controls its own CORS/cache headers and quotas.

The optional Python server adds `GET /api/v1/anime`, `GET /api/v1/anime/{slug}`, `GET /api/v1/stats`, and `GET /health`. Filters: `q` (up to 200 characters; searches multilingual titles and slug), `genre` (case-insensitive), `format`, `year` (1900–2200), `limit` (1–100; default 24), and `offset` (0–1,000,000). Unknown/duplicate/malformed query parameters return 400. Search returns `{total, limit, offset, has_more, data}`; order is deterministic by slug.

The Python server supports GET/HEAD/OPTIONS, `Access-Control-Allow-Origin: *`, JSON error bodies, ETag/If-None-Match (304), UTF-8 and subtitle MIME types. Ambiguous numeric IDs return 409; unknown releases return 404; unsupported write methods return 405. Health is not cached. Static files additionally support Last-Modified/If-Modified-Since. Directory listing, hidden paths, traversal and escaping symlinks are denied. No upload, translation, authentication, accounts, billing or video API is provided.

For offline/self-hosted URL manifests build with `--base-url http://localhost:8000` (or your public HTTPS base URL). The portal uses validated relative asset paths and works against the staged local site. The server reads catalog/stats at startup; restart it after rebuilding. Deploy behind a production reverse proxy for TLS, concurrency/bandwidth policy and access logs.

Python example:

```python
import json
from urllib.request import urlopen

base = 'https://ikymory.github.io/anime-subtitles-kazakh'
with urlopen(base + '/api/v1/anime/frieren.json', timeout=20) as response:
    anime = json.load(response)
print(anime['title']['english'], anime['available_episodes_count'])
for track in anime['subtitles']:
    if track['files']['vtt']:
        print(track['episode'], track['files']['vtt'])
```

For HTML5 players set `<video crossorigin="anonymous">`, add a `<track kind="subtitles" srclang="kk">` with the returned VTT URL, and ensure your media origin permits cross-origin playback. Check timing against the exact video release.
