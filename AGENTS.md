# Repository instructions

Read docs/SESSION_HANDOFF.md, docs/DATASET.md and docs/API.md before changes.
Preserve raw subtitles, author attribution, license, unrelated work and unpublished local batches.
Use data/catalog.json as metadata input. It contains legacy unverified metadata; slugs are stable IDs.
Never claim complete anime or human-reviewed translations based on file presence or automated parsing.
Build with python -m subtitle_api.build; test with python -m unittest discover -s tests -v and node --test tests/portal.test.cjs.
Stage canonical SRT/VTT for Pages with subtitle_api.stage and validate every advertised download with subtitle_api.validate.
Keep Pages below 1,000,000,000 bytes. ASS remains available in raw archives and full self-hosted builds.
Update affected docs, audit findings and SESSION_HANDOFF.md after meaningful work. Never store credentials in source or documentation.
