# Verified catalog and API

The user requested an audit of translated anime/episodes, fixes for repository errors, and a dependable API. Preserve subtitle text, author attribution, all existing downloads, unrelated files, and unpublished local batches.

Use the existing static GitHub Pages architecture. Add a reproducible Python 3.11+ standard-library build, structural subtitle audit, explicit coverage/quality metadata, OpenAPI specification, and an optional HTTP API for local/self hosting. No paid services or new credentials are required. Keep legacy JSON endpoints; slugs are stable identifiers because existing numeric IDs collide and have unverified provenance.

Count releases and episode tracks from tracked files, never filenames/aliases twice. A track being present does not establish correct episode numbering, complete series coverage, or human-reviewed translation. Record structural errors, missing formats, mirror/alias drift, duplicate content, and suspicious numbering. Do not invent missing dialogue or renumber uncertain episodes. Publish machine-readable findings and clearly state limitations.

The HTTP API must provide bounded pagination/search/filtering, individual releases, stats, health, GET/HEAD/OPTIONS, JSON errors, CORS, conditional caching, UTF-8 and correct subtitle MIME types. Constrain file access to the public directory. Include working examples, automated regression and real HTTP tests, and CI that validates before deployment.

Preserve the portal's visual design. Correct fabricated fallback metadata, episode/download assumptions, injection risks, loading failures and accessibility where directly affected. Verify the portal in a browser.

Implementation choices above are the agent's judgment under the user's autonomous repair request. Publishing/merging into main remains separate from a reviewable branch/PR.
