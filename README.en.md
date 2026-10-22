# Anime Subtitles Kazakh

Kazakh (`kk`) anime subtitle archive, static JSON catalog, and optional self-hosted HTTP API.

[Catalog](https://ikymory.github.io/anime-subtitles-kazakh/) · [API documentation](https://ikymory.github.io/anime-subtitles-kazakh/api.html) · [Қазақша](README.kk.md) · [日本語](README.ja.md)

| Measured from the tracked archive | Count |
| --- | ---: |
| Catalog release entries | 1,400 |
| Entries with structurally usable tracks | 1,389 |
| Archived episode tracks | 9,819 |
| Structurally usable tracks after normalization/recovery | 9,788 |
| Quarantined tracks requiring timing/content repair | 31 |
| Archived SRT/VTT/ASS files, including naming aliases | 88,375 |
| Distinct legacy metadata IDs | 1,327 |
| Ambiguous legacy ID groups | 70 |

These are **release entries and subtitle tracks**, not a verified count of unique anime franchises or complete series. Alias files do not count as additional translations. Metadata, episode numbering, translation accuracy and synchronization with licensed video have not received human verification. [Measured stats](dist/api/v1/stats.json) and the [full audit](dist/api/v1/audit.json) expose the known issues.

## Use the static API

No API key is required. GitHub Pages serves static files; search and pagination are performed in your client. Hosting/CDN limits still apply.

```javascript
const base = 'https://ikymory.github.io/anime-subtitles-kazakh';
const response = await fetch(`${base}/api/v1/anime.json`);
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const catalog = await response.json();
const match = catalog.data.find(a => a.slug === 'frieren');
const detailResponse = await fetch(match.api_url);
if (!detailResponse.ok) throw new Error(`HTTP ${detailResponse.status}`);
const anime = await detailResponse.json();
for (const track of anime.subtitles) {
  console.log(track.episode, track.files.vtt); // use manifest URLs; formats can be null
}
```

Endpoints: `/api/v1/anime.json`, `/api/v1/anime/{slug}.json`, `/api/v1/stats.json`, `/api/v1/audit.json`, `/openapi.json`.

Use slugs as stable IDs. The inherited numeric IDs are unverified and sometimes collide. Ambiguous numeric JSON endpoints contain `error.code = "ambiguous_legacy_id"` and `matches`; static hosting returns that document with HTTP 200, while the self-hosted server returns HTTP 409.

Pages publishes **canonical SRT and WebVTT** within its 1 GB site budget. Full local/self-hosted builds also support ASS. Raw originals and naming aliases remain in `subtitles/`. Do not construct links from episode counts or assume every number between 1 and the maximum is present.

## Build and run locally

Requires Python 3.11+ and Git. No runtime packages, credentials or translation service are needed. Node.js 22+ runs the portal unit tests.

```sh
git clone https://github.com/ikymory/anime-subtitles-kazakh.git
cd anime-subtitles-kazakh
python -m subtitle_api.build --output .build/catalog --no-copy-subtitles
python -m subtitle_api.stage --catalog .build/catalog --output .build/pages
python -m subtitle_api.validate --directory .build/pages
python -m subtitle_api.server --directory .build/pages --port 8000
```

Open `http://localhost:8000`. The dynamic server additionally supports:

```http
GET /api/v1/anime?q=frieren&genre=Fantasy&limit=24&offset=0
GET /api/v1/anime/frieren
GET /api/v1/stats
GET /health
```

To publish all three formats on your own host, use a clean output directory:

```sh
python -m subtitle_api.build --output .build/full --base-url http://localhost:8000
python -m subtitle_api.validate --directory .build/full
python -m subtitle_api.server --directory .build/full
```

The full build exports the API and subtitles. Serve the portal from the Pages staging directory, or copy `dist/index.html`, `dist/api.html`, `dist/catalog-runtime.js` and `dist/openapi.json` into your full output directory. For production, replace the base URL with your public HTTPS origin and deploy behind a reverse proxy with your own capacity/rate limits. The bundled threaded HTTP server is a local/reference implementation.

## Contribute and verify

```sh
python -m unittest discover -s tests -v
node --test tests/portal.test.cjs
python -m compileall -q subtitle_api tests
```

`data/catalog.json` is the metadata input; `subtitles/` contains the archived assets. The build uses tracked assets when Git metadata is available and rejects missing releases. It repairs timestamp serialization, removes empty cue blocks, derives broken/missing formats from a usable counterpart, and quarantines tracks with no safe source. It never invents dialogue or uncertain timing. Rebuild after source changes; JSON in `dist/api/v1/` is generated. CI builds, stages, size-checks and checksum-validates every advertised download before Pages deployment.

Optional browser acceptance (requires separate development dependencies and internet access for the portal's external artwork/styles):

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tools/browser_smoke.py --directory .build/pages
```

This checks multilingual coverage, keyboard details, manifest downloads, native browser WebVTT parsing, 320/390 px layouts and the API explorer. It starts and stops its own local API process.

See [dataset audit](docs/DATASET.md), [API contract](docs/API.md), [architecture](docs/ARCHITECTURE.md), [known issues](docs/ISSUES.md), and [session handoff](docs/SESSION_HANDOFF.md).

## Attribution and rights

Preserve the original `ikymory` translation/author attribution. See [LICENSE](LICENSE) and [DMCA.md](DMCA.md) for the repository's existing terms and contact. The archive contains text subtitles and metadata. Use licensed media from the relevant rights holders.
