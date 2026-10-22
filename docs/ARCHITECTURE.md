# Architecture

`data/catalog.json`: preserved release metadata input; unverified legacy external IDs/ratings.
`subtitles/`: archived raw translations and naming aliases. No automatic semantic edits.
`subtitle_api/subtitles.py`: strict SRT/VTT/ASS parsing, conservative timestamp normalization, format rendering.
`subtitle_api/build.py`: tracked-file inventory, quality findings, deterministic manifests, explicit ambiguous-ID documents, optional normalized full export.
`subtitle_api/stage.py`: canonical export profiles, checksum comparison against build, Pages size budget.
`subtitle_api/validate.py`: catalog consistency and SHA-256/byte verification for every advertised download.
`subtitle_api/server.py`: dependency-free read-only HTTP reference server.
`dist/`: portal sources, OpenAPI, generated JSON snapshots and historical subtitle mirrors. Deploy `.build/pages`, not the historical dist mirror.
`tests/`: real filesystem and HTTP regression tests; Node built-in portal helper tests.

Builds are deterministic and contain no wall-clock timestamps, random IDs or translation API calls. Source and deployed files are explicitly distinguished. CI is the deployment gate. Generated JSON is a snapshot; source metadata plus tracked subtitles are the build inputs.
