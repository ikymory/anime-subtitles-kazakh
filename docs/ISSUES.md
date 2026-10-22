# Known issues

- 31 archived tracks have no safely recoverable format and remain quarantined. See `unusable_episode` findings in audit.json; the API does not advertise them.
- 47 numbering anomalies, 39 strongly repeated-dialogue tracks, 592 English-residue flags, 2 CJK flags, 275 cross-format dialogue differences, and 68 duplicate-content groups need human review. These counts are heuristic observations, not confirmed linguistic defects.
- Metadata, ratings, identities and intended series episode totals are unverified. No claim of 1,400 complete or uniquely identified anime is made.
- Raw source archives retain malformed legacy timestamp serializations and aliases. Served exports are normalized/derived and checksum-verified.
- Pages publishes SRT/VTT and drops historical Pages alias paths to respect site size limits. Raw source aliases and ASS remain in Git; self-host full builds for all three formats.
- Portal artwork, fonts and Tailwind styling depend on external services; the API and subtitle exports work offline. Third-party image failures fall back gracefully.
- No real production deployment or human translation acceptance is established by local tests. Merge/publish and subsequent live endpoint checks remain separate.
