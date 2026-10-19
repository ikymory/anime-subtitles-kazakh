# Dataset audit — 2026-10-17

VERIFIED FROM PROJECT: tracked source revision e8ea33be; 1,400 catalog releases, 9,819 archived episode tracks, 88,375 source subtitle files including three naming variants. Only tracked files were counted; 427 unpublished local release directories were preserved.

The normalized API exposes 9,788 usable tracks and 29,364 canonical format assets in the full build. 31 tracks are quarantined because none of their source formats supplies safely recoverable timing. There are 9,685 distinct usable episode-content fingerprints and 68 duplicate-content groups. Fingerprints are exact cue/time comparisons, not semantic anime deduplication.

1,327 distinct inherited numeric IDs occur across 1,400 entries. 70 IDs are ambiguous. These are unverified legacy identifiers; slugs are authoritative catalog keys.

The baseline SRT scan found 818,199 nonstandard/malformed cue blocks, including ASS-style timestamps in SRT, and 4,866 canonical source/deployment mismatches across formats. Build-time normalization repairs unambiguous serialization and derives 1,837 unusable/missing format assets from a usable counterpart. Raw source files and author attribution are preserved. A successful build does not imply that every source file is clean.

The current automated findings are:

```json
{
  "ambiguous_legacy_id": 70,
  "cjk_dialogue_requires_review": 2,
  "derived_format": 1837,
  "duplicate_episode_content": 68,
  "english_dialogue_requires_review": 592,
  "episode_numbering_requires_review": 47,
  "format_dialogue_drift": 275,
  "invalid_subtitle": 1930,
  "mirror_drift": 4866,
  "normalized_subtitle_serialization": 27527,
  "repeated_dialogue_requires_review": 39,
  "unrecognized_filename": 4,
  "unusable_episode": 31
}
```

English/CJK detection, repeated dialogue and episode-number flags are heuristics requiring review. They can include names, songs, signs or legitimate specials. Frieren's inherited track 264 is preserved and flagged, not automatically renamed. Metadata ratings, episode totals and external IDs remain unverified. Human linguistic review and comparison against licensed video are outstanding.

Canonical truth is [stats JSON](../dist/api/v1/stats.json) and [audit JSON](../dist/api/v1/audit.json); regenerate both after changes.
