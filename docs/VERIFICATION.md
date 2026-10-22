# Verification — 2026-10-19

Source inventory: 1,400 releases / 9,819 archived tracks / 88,375 source subtitle files. 1,389 entries contain structurally usable tracks. Usable coverage: 9,788 tracks; 31 quarantined. Source tree e8ea33be and remote main 425b53f6 have identical subtitle content; remote changes only adjust README whitespace. Original local tracked files remain unchanged.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -v` | 30 passed; filesystem, parsing, generation, publishing and real HTTP regressions |
| `node --test tests/portal.test.cjs` | 5 passed; metadata safety, missing values and manifest downloads |
| `python -m ruff check subtitle_api tests tools` | passed |
| `python -m ruff format --check subtitle_api tests tools` | 10 files formatted |
| `python -m compileall -q subtitle_api tests tools` | passed |
| `python -m subtitle_api.validate --directory .build/pages` | 1,400 entries / 9,788 tracks / 19,576 URL, SHA-256, byte-count, cue-count and structural validations |
| OpenAPI component schema validation (JSON Schema 2020-12) | catalog, stats and all 2,727 detail/ambiguity documents passed |
| `python tools/browser_smoke.py --directory .build/pages` | no page exceptions; all three languages; 320/390 px layouts; no mobile header overlap; keyboard details/focus restoration; real local downloads; browser parsed all 266 sample VTT cues; API explorer 200 OK |
| Canonical Pages staging budget | 905,235,062 bytes, below 1,000,000,000-byte limit |

The real browser checks use optional Playwright 1.58.0. The runtime and unittest suite require only Python's standard library. The export was validated as staged; raw historical `dist/subtitles` files are not the publishing artifact.

See the PR's checks for external GitHub CI status. The changes are prepared for review; deployment and human linguistic acceptance are separate. Known content and metadata limitations remain in ISSUES.md and the machine-readable audit. No production load/SLA or complete-series claim is made.
