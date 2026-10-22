# Catalog and API Implementation Plan

> **For agentic workers:** Implement inline with superpowers:executing-plans; preserve unrelated work.

**Goal:** Make coverage reproducible and provide tested static and self-hosted APIs.
**Architecture:** A standard-library Python package validates tracked subtitle assets, generates deterministic catalog/statistics/audit JSON, and serves the generated public directory. Existing Pages and portal routes stay available.
**Tech Stack:** Python 3.11+, unittest, static HTML/JavaScript, GitHub Actions.
**Spec:** ../specs/2026-10-17-catalog-api-design.md

## Global constraints
- Preserve subtitle text, attribution and untracked local batches.
- Never equate structural checks with translation accuracy or completed anime.
- Keep existing static JSON and subtitle paths.
- No credentials or external services in build/test.

## Review focus
- Episode numbers embedded in titles must never become episode numbers.
- Empty, missing or invalid formats must not yield fabricated links.
- Colliding numeric identifiers must not silently return a different release.
- Encoded traversal, symlinks, malformed queries and HEAD/OPTIONS need safe HTTP behavior.
- Existing sparse/untracked local work must not affect published coverage.

### Task 1: Reproducible inventory and quality audit
Files: subtitle_api/subtitles.py, subtitle_api/build.py, data/catalog.json, tests/test_catalog.py.
- [x] Write regression tests for exact filename recognition, format parsers, deduplication, missing assets and ambiguous IDs; observe failures.
- [x] Implement deterministic build(source_root, output_root, metadata_path) with tracked-file inventory, preserved legacy metadata and measured quality findings.
- [x] Run unittest; build against the tracked source; compare counts, links, mirrors and bytes.

### Task 2: HTTP API
Files: subtitle_api/server.py, tests/test_server.py, dist/openapi.json, docs/API.md.
- [x] Write real ephemeral HTTP server tests for pagination, filters, errors, CORS, caching, HEAD and traversal; observe failures.
- [x] Implement create_server(directory, host, port) and CLI with bounded inputs and safe static file handling.
- [x] Run complete unittest suite and real endpoint smoke checks.

### Task 3: Portal, documentation and CI
Files: dist/index.html, dist/api.html, README*.md, language guide aliases, .github/workflows/*.yml, docs/*.md.
- [x] Add browser/JavaScript regressions for missing metadata and authoritative download URLs.
- [x] Fix verified portal/data claims and examples; add validated CI build and deploy dependency; document actual coverage and unresolved content review.
- [x] Run full tests, full repository audit, generated-output validation, browser smoke and git diff checks; package a reviewable branch/PR and report limitations.

## Execution evidence and decisions

- Task 1: complete. Tracked inventory and structural build at e8ea33be: 1,400 entries / 9,819 archived tracks / 9,788 usable tracks. Raw sources and unpublished batches preserved.
- Task 2: complete locally. Real HTTP regression tests cover bounded queries, cache/HEAD/OPTIONS, errors and both symlink escape paths.
- Task 3: local implementation/verification complete; PR publication and external CI status are recorded in docs/VERIFICATION.md.
- Ruling: Pages publishes canonical SRT/VTT to remain below its 1 GB site limit. Existing raw Git aliases/ASS are preserved; historical Pages aliases are no longer published. Compatibility cost is documented in API.md and the PR.
- Ruling: Preserve uncertain numbering and quarantine 31 tracks rather than invent timing/dialogue. This limits usable coverage until source material is reviewed.
- Final review: independent review performed; all reported findings were reproduced and fixed, with regression evidence in docs/REVIEW.md.
