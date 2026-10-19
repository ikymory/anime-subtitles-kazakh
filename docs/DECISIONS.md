# Decisions

2026-10-17: Retain static Pages and add optional standard-library Python HTTP API; this avoids credentials, paid infrastructure and runtime package dependencies.
Use slugs for identity; inherited IDs are unverified and collide. Ambiguous legacy endpoints expose choices rather than silently selecting a release.
Preserve uncertain numbering and dialogue. Normalize unambiguous serialization, remove empty cue blocks, derive formats from usable cues, and quarantine tracks where timing would require guessing.
Publish canonical SRT/VTT on Pages to respect its documented site limit. ASS and all archived aliases remain in Git/full self-hosted exports. Existing Pages alias URLs are a documented compatibility change.
Work in an isolated sparse clone, preserving the original checkout's unpublished batches. Deliver a reviewable branch/PR; do not merge main without authorization.
