# Optimization

Measured historical deployment subtitle mirror: 5,189,075,480 bytes across 88,375 files. Raw source subtitles: 4,201,117,793 bytes. Naming aliases duplicate almost all format payloads.

Pages staging publishes only canonical SRT/VTT, omits duplicate alias copies and full ASS, and enforces a 1,000,000,000-byte site budget before upload. Full exports remain available for self-hosting. Exact staged size is printed by `subtitle_api.stage`.

Search operates on an in-memory metadata snapshot with bounded pages, queries and query parameter counts. JSON uses ETags and five-minute caching in the reference HTTP server. UI renders one catalog page and fetches details on demand. Every advertised asset includes bytes/SHA-256 for integrity checks. No measured production throughput/SLA is claimed.
