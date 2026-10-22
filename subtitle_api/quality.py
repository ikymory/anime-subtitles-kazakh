"""Conservative content and identity checks; these do not verify translation accuracy."""

import hashlib
import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import PurePosixPath

from .subtitles import Cue


def apply_quality_findings(details: list[dict], findings: list[dict]) -> None:
    """Propagate local/path and cross-release findings before manifest emission."""
    per_release = defaultdict(list)
    per_track = defaultdict(set)
    for finding in findings:
        affected = set(finding.get("slugs", []))
        if finding.get("slug"):
            affected.add(finding["slug"])
        path = finding.get("path")
        if isinstance(path, str):
            parts = PurePosixPath(path).parts
            if len(parts) >= 3 and parts[0] == "subtitles":
                affected.add(parts[1])
        for track in finding.get("tracks", []):
            affected.add(track["slug"])
            per_track[(track["slug"], track["episode"])].add(finding["code"])
        for slug in affected:
            per_release[slug].append(finding["code"])
    for detail in details:
        flags = per_release[detail["slug"]]
        detail["quality_flags"] = sorted(set(flags))
        detail["quality_issues_count"] = len(flags)
        for row in detail["subtitles"]:
            row["quality_flags"] = sorted(
                set(row.get("quality_flags", []))
                | per_track[(detail["slug"], row["episode"])]
            )


def plain_dialogue(text: str) -> str:
    text = re.sub(r"\{[^}]*\}|<[^>]*>", "", text)
    return " ".join(unicodedata.normalize("NFKC", html.unescape(text)).split())


def same_dialogue(first: list[Cue], second: list[Cue]) -> bool:
    if first is second or [cue.text for cue in first] == [cue.text for cue in second]:
        return True
    return [plain_dialogue(c.text) for c in first if c.text.strip()] == [
        plain_dialogue(c.text) for c in second if c.text.strip()
    ]


def dialogue_fingerprint(cues: list[Cue]) -> str | None:
    lines = [
        plain_dialogue(cue.text).casefold()
        for cue in cues
        if cue.text.strip() and "ikymory" not in cue.text.casefold()
    ]
    if len(lines) < 5 or sum(map(len, lines)) < 100:
        return None
    return hashlib.sha256(
        json.dumps(lines, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def title_key(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKC", html.unescape(text)).casefold()
        if char.isalnum()
    )


def title_keys(entry: dict, *, include_synonyms: bool = False) -> set[str]:
    title = entry.get("title") or {}
    values = (
        [title.get(key) for key in ("english", "romaji", "native")]
        if isinstance(title, dict)
        else [title]
    )
    if include_synonyms:
        values.extend(entry.get("synonyms") or [])
    return {
        key
        for text in values
        if isinstance(text, str)
        and (key := title_key(text))
        and key not in {"unknown", "untitled", "anime", "special"}
    }


def duplicate_title_groups(entries: list[dict]) -> list[list[str]]:
    """Report exact multilingual title collisions without trusting legacy IDs."""
    owners = defaultdict(set)
    for entry in entries:
        for key in title_keys(entry):
            owners[key].add(entry["slug"])
    # Unite transitively connected aliases; never silently merge archive entries.
    parent = {entry["slug"]: entry["slug"] for entry in entries}

    def find(slug: str) -> str:
        while parent[slug] != slug:
            parent[slug] = parent[parent[slug]]
            slug = parent[slug]
        return slug

    for slugs in owners.values():
        ordered = sorted(slugs)
        for slug in ordered[1:]:
            parent[find(slug)] = find(ordered[0])
    groups = defaultdict(list)
    for slug in sorted(parent):
        groups[find(slug)].append(slug)
    return sorted(group for group in groups.values() if len(group) > 1)
