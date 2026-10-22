"""Curate additional distinct works from a dated AniList metadata snapshot.

This offline planner never labels metadata, queued works, or individual tracks as
translated anime. Franchise exclusions are deliberately conservative.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from .build import write_json
from .quality import title_keys

FRANCHISE_RELATIONS = {
    "PREQUEL",
    "SEQUEL",
    "PARENT",
    "SIDE_STORY",
    "ALTERNATIVE",
    "COMPILATION",
    "CONTAINS",
    "CHARACTER",
}


def plan_expansion(
    existing: list[dict],
    candidates: list[dict],
    *,
    chinese: int = 300,
    other: int = 200,
) -> dict:
    if chinese < 0 or other < 0:
        raise ValueError("Requested title counts must be nonnegative")
    existing_keys = (
        set().union(*(title_keys(entry, include_synonyms=True) for entry in existing))
        if existing
        else set()
    )
    rows = {}
    for entry in candidates:
        identifier = entry.get("id")
        if (
            not isinstance(identifier, int)
            or isinstance(identifier, bool)
            or identifier < 1
        ):
            raise ValueError("Candidates require positive AniList IDs")
        if identifier in rows and rows[identifier] != entry:
            # Paginated rankings may shift during collection. Prefer the first
            # fetched record, which carries the original ranking snapshot.
            continue
        rows[identifier] = entry
    parent = {identifier: identifier for identifier in rows}

    def find(identifier):
        parent.setdefault(identifier, identifier)
        while parent[identifier] != identifier:
            parent[identifier] = parent[parent[identifier]]
            identifier = parent[identifier]
        return identifier

    for identifier, entry in rows.items():
        for edge in entry.get("relations", {}).get("edges", []):
            node = edge.get("node") or {}
            other_id = node.get("id")
            if (
                edge.get("relationType") in FRANCHISE_RELATIONS
                and node.get("type") == "ANIME"
                and isinstance(other_id, int)
            ):
                first, second = find(identifier), find(other_id)
                parent[max(first, second)] = min(first, second)
    blocked_franchises = set()
    for identifier, entry in rows.items():
        related = [
            edge.get("node") or {}
            for edge in entry.get("relations", {}).get("edges", [])
            if edge.get("relationType") in FRANCHISE_RELATIONS
        ]
        if title_keys(entry, include_synonyms=True) & existing_keys or any(
            title_keys(node) & existing_keys for node in related
        ):
            blocked_franchises.add(find(identifier))

    selected = []
    reasons = Counter()
    countries = Counter()
    selected_keys = set()
    selected_franchises = set()
    ranked = sorted(
        rows.values(),
        key=lambda row: (
            -(row.get("averageScore") or 0),
            -(row.get("popularity") or 0),
            row["id"],
        ),
    )
    for entry in ranked:
        identifier = entry["id"]
        group = find(identifier)
        bucket = "CN" if entry.get("countryOfOrigin") == "CN" else "other"
        target = chinese if bucket == "CN" else other
        keys = title_keys(entry, include_synonyms=True)
        if group in blocked_franchises:
            reasons["existing_title_or_franchise"] += 1
            continue
        if keys & selected_keys or group in selected_franchises:
            reasons["duplicate_title_or_franchise"] += 1
            continue
        if entry.get("status") != "FINISHED":
            reasons["not_finished"] += 1
            continue
        if (
            not keys
            or entry.get("format") not in {"TV", "ONA", "MOVIE"}
            or (entry.get("duration") or 0) < 10
            or (entry.get("averageScore") or 0) <= 0
        ):
            reasons["insufficient_metadata_or_short_form"] += 1
            continue
        if countries[bucket] >= target:
            continue
        related_other_ids = {
            node["id"]
            for edge in entry.get("relations", {}).get("edges", [])
            if edge.get("relationType") == "OTHER"
            and (node := edge.get("node") or {}).get("type") == "ANIME"
            and isinstance(node.get("id"), int)
            and not isinstance(node["id"], bool)
            and node["id"] > 0
        }
        selected.append(
            {
                "anime_id": f"anilist:{identifier}",
                "anilist_id": identifier,
                "myanimelist_id": entry.get("idMal"),
                "title": entry["title"],
                "synonyms": entry.get("synonyms") or [],
                "country": entry.get("countryOfOrigin"),
                "format": entry.get("format"),
                "episodes_expected_unverified": entry.get("episodes"),
                "ranking": {
                    "provider": "AniList",
                    "score": entry.get("averageScore"),
                    "popularity": entry.get("popularity"),
                    "source_url": f"https://anilist.co/anime/{identifier}",
                },
                "status": "source_required",
                "translation_provider": None,
                "source_tracks": [],
                "translated_tracks": 0,
                "human_reviewed": False,
                "relation_review_links": [
                    {
                        "relation": "OTHER",
                        "anilist_id": related_id,
                        "source_url": f"https://anilist.co/anime/{related_id}",
                        "status": "unresolved_franchise_identity",
                    }
                    for related_id in sorted(related_other_ids)
                ],
            }
        )
        selected_keys.update(keys)
        selected_franchises.add(group)
        countries[bucket] += 1
    return {
        "schema_version": "1.0",
        "counting_unit": "distinct_anilist_works_with_conservative_franchise_screening",
        "requested": {"CN": chinese, "other": other},
        "selected": {"CN": countries["CN"], "other": countries["other"]},
        "shortfall": {
            "CN": max(0, chinese - countries["CN"]),
            "other": max(0, other - countries["other"]),
        },
        "selected_distinct_anime": len(selected),
        "translated_distinct_anime": 0,
        "ready_to_translate": False,
        "franchise_identity_verified": False,
        "source": "https://graphql.anilist.co",
        "ranking_method": "score descending, popularity descending, AniList ID ascending; finished TV/ONA/movie releases >=10 minutes; one work per conservative anime relation group; existing title and related title aliases excluded",
        "quality_caveat": "Scores are dated provider metadata, not an S-tier guarantee. Counts identify distinct AniList works, not verified distinct franchises. OTHER anime relations remain unresolved review links and may connect selected works; missing relations may also hide franchise overlap. Source identities and episode completeness require verification before translation.",
        "excluded": dict(sorted(reasons.items())),
        "targets": selected,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.json"))
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--chinese", type=int, default=300)
    parser.add_argument("--other", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("data/expansion-plan.json"))
    args = parser.parse_args()
    result = plan_expansion(
        json.loads(args.catalog.read_bytes()),
        json.loads(args.candidates.read_bytes()),
        chinese=args.chinese,
        other=args.other,
    )
    write_json(args.output, result)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "selected",
                    "shortfall",
                    "translated_distinct_anime",
                    "ready_to_translate",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
