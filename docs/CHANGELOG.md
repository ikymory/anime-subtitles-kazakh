# Changelog

## 2026-10-17 — Catalog/API reliability

- Added deterministic tracked-file inventory, strict subtitle parsers, safe serialization recovery, derived formats and machine-readable quality findings.
- Replaced ambiguous numeric-ID overwrites with explicit disambiguation; preserved slug endpoints and archived source assets.
- Added a tested read-only HTTP API, OpenAPI 3.1, query validation, CORS, caching, correct MIME types and safe file serving.
- Added canonical Pages staging, size enforcement, whole-export checksum validation and deployment gates.
- Pinned current official GitHub Actions revisions using Node 24, fixed the CI image to Ubuntu 24.04, and canceled superseded PR checks to avoid duplicate builds.
- Corrected coverage claims, developer examples, portal download generation, metadata fallbacks, injection risks and mobile navigation.
- Preserved unpublished local batches and existing author attribution.
