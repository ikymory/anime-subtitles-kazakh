"""Build JSON from tracked assets; do not manufacture coverage or metadata."""

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

from .discovery import write_discovery
from .quality import (
    apply_quality_findings,
    dialogue_fingerprint,
    duplicate_title_groups,
    same_dialogue,
)
from .subtitles import (
    identify_file,
    normalize_subtitle,
    parse_subtitle,
    render_subtitle,
)

SITE = "https://ikymory.github.io/anime-subtitles-kazakh"
REPOSITORY = "https://github.com/ikymory/anime-subtitles-kazakh"
FORMATS = ("srt", "vtt", "ass")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if not path.exists() or path.read_bytes() != payload:
        path.write_bytes(payload)


def source_files(root: Path) -> list[str]:
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "subtitles"],
            capture_output=True,
            check=True,
        )
        return sorted(p for p in result.stdout.decode("utf-8").split("\0") if p)
    return sorted(
        p.relative_to(root).as_posix()
        for p in (root / "subtitles").rglob("*")
        if p.is_file()
    )


def build(
    source_root: Path,
    output_root: Path,
    metadata_path: Path,
    *,
    copy_subtitles: bool = True,
    base_url: str = SITE,
) -> dict:
    source_root, output_root = Path(source_root).resolve(), Path(output_root).resolve()
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    if not isinstance(metadata, list):
        raise TypeError("Metadata must be a list of releases")
    slugs = [a["slug"] for a in metadata]
    if len(set(slugs)) != len(slugs) or any(
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs
    ):
        raise ValueError("Duplicate or unsafe release slug")
    paths = source_files(source_root)
    quarantine_path = Path(metadata_path).parent / "quarantine.json"
    quarantines = {}
    if quarantine_path.exists():
        rules = json.loads(quarantine_path.read_bytes())
        if not isinstance(rules, dict) or not isinstance(rules.get("tracks"), list):
            raise ValueError("Invalid quarantine manifest")
        tracked_paths = set(paths)
        for rule in rules["tracks"]:
            if not isinstance(rule, dict) or rule.get("slug") not in slugs:
                raise ValueError("Invalid quarantine release")
            slug, episode = rule["slug"], rule.get("episode")
            relative, digest = rule.get("source_path"), rule.get("source_sha256")
            if (
                not isinstance(episode, int)
                or isinstance(episode, bool)
                or episode < 0
                or not isinstance(relative, str)
                or relative not in tracked_paths
                or Path(relative).parts[:2] != ("subtitles", slug)
                or not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or not isinstance(rule.get("reason"), str)
                or not rule["reason"].strip()
                or not isinstance(rule.get("evidence"), str)
                or not rule["evidence"].strip()
                or (slug, episode) in quarantines
            ):
                raise ValueError("Invalid quarantine track")
            identified = identify_file(slug, Path(relative).name)
            anchor = (source_root / relative).resolve()
            if (
                not identified
                or identified[0] != episode
                or not anchor.is_relative_to(source_root / "subtitles")
            ):
                raise ValueError("Invalid quarantine anchor")
            # Git stores LF while Windows checkouts may materialize CRLF.
            # Normalize line endings only; changed dialogue or added cues fail closed.
            anchor_bytes = anchor.read_bytes().replace(b"\r\n", b"\n")
            if hashlib.sha256(anchor_bytes).hexdigest() != digest:
                raise ValueError(
                    f"Quarantine source changed; review required: {relative}"
                )
            quarantines[(slug, episode)] = rule
    by_slug = defaultdict(list)
    for path in paths:
        parts = Path(path).parts
        if len(parts) == 3:
            by_slug[parts[1]].append(path)
    findings = []
    counts = Counter()
    fingerprints = defaultdict(list)
    dialogue_fingerprints = defaultdict(list)
    identifiers = defaultdict(list)
    details = []
    selected_formats = 0
    raw_bytes_total = 0
    all_cue_count = 0
    source_episode_count = 0

    def issue(code: str, **context: object) -> None:
        counts[code] += 1
        findings.append({"code": code, **context})

    for entry in sorted(metadata, key=lambda a: a["slug"]):
        slug = entry["slug"]
        choices = defaultdict(lambda: defaultdict(list))
        for path in by_slug[slug]:
            identified = identify_file(slug, Path(path).name)
            if identified:
                episode, ext, rank = identified
                choices[episode][ext].append((rank, path))
            else:
                issue("unrecognized_filename", path=path)
        if not choices:
            raise ValueError(f"{slug}: no subtitle files")
        source_episode_count += len(choices)
        rows = []
        release_findings = len(findings)
        for episode, formats in sorted(choices.items()):
            if (slug, episode) in quarantines:
                rule = quarantines[(slug, episode)]
                issue(
                    "reviewed_content_quarantine",
                    slug=slug,
                    episode=episode,
                    reason=rule["reason"],
                    evidence=rule["evidence"],
                    source_sha256=rule["source_sha256"],
                )
                continue
            track_findings = len(findings)
            links, assets, parsed = {}, {}, {}
            for ext in FORMATS:
                options = sorted(formats.get(ext, []))
                if not options:
                    links[ext] = None
                    issue("missing_format", slug=slug, episode=episode, format=ext)
                    continue
                _, selected = options[0]
                raw = (source_root / selected).read_bytes()
                raw_bytes_total += len(raw)
                source_digest = hashlib.sha256(raw).hexdigest()
                try:
                    normalized = normalize_subtitle(raw.decode("utf-8-sig"), ext)
                    parsed[ext] = parse_subtitle(normalized, ext)
                except (UnicodeError, ValueError) as error:
                    issue("invalid_subtitle", path=selected, message=str(error))
                    links[ext] = None
                    continue
                compiled = normalized.encode("utf-8")
                digest = hashlib.sha256(compiled).hexdigest()
                if compiled != raw:
                    issue("normalized_subtitle_serialization", path=selected)
                for _, alias in options[1:]:
                    if (
                        hashlib.sha256((source_root / alias).read_bytes()).hexdigest()
                        != source_digest
                    ):
                        issue("alias_drift", path=alias, canonical=selected)
                mirror = source_root / "dist" / selected
                if (
                    mirror.exists()
                    and hashlib.sha256(mirror.read_bytes()).hexdigest() != source_digest
                ):
                    issue("mirror_drift", path=selected)
                link = base_url.rstrip("/") + "/" + quote(selected, safe="/")
                links[ext] = link
                assets[ext] = {
                    "path": selected,
                    "sha256": digest,
                    "bytes": len(compiled),
                    "cues": len(parsed[ext]),
                    "origin": "source",
                }
                if copy_subtitles:
                    for _, relative in options:
                        dest = output_root / relative
                        if dest == source_root / relative:
                            raise ValueError(
                                "Output directory cannot overwrite source subtitles"
                            )
                        if not dest.exists() or dest.read_bytes() != compiled:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(compiled)
            if not parsed:
                issue("unusable_episode", slug=slug, episode=episode)
                continue
            primary = parsed.get("srt", next(iter(parsed.values())))
            for ext in FORMATS:
                if ext in parsed:
                    if same_dialogue(primary, parsed[ext]):
                        continue
                    issue(
                        "format_dialogue_drift", slug=slug, episode=episode, format=ext
                    )
                compiled = render_subtitle(primary, ext).encode("utf-8")
                try:
                    recovered = parse_subtitle(compiled.decode("utf-8"), ext)
                except ValueError:
                    issue(
                        "format_recovery_requires_review",
                        slug=slug,
                        episode=episode,
                        format=ext,
                    )
                    continue
                relative = f"subtitles/{slug}/ep_{episode:02d}.kk.{ext}"
                links[ext] = base_url.rstrip("/") + "/" + relative
                assets[ext] = {
                    "path": relative,
                    "sha256": hashlib.sha256(compiled).hexdigest(),
                    "bytes": len(compiled),
                    "cues": len(recovered),
                    "origin": "derived",
                }
                issue("derived_format", slug=slug, episode=episode, format=ext)
                if copy_subtitles:
                    targets = {relative, *[path for _, path in formats.get(ext, [])]}
                    for target in targets:
                        dest = output_root / target
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(compiled)
            selected_formats += len(assets)
            all_cue_count += len(primary)
            dialogue = [
                cue.text for cue in primary if "ikymory" not in cue.text.lower()
            ]
            content_hash = hashlib.sha256(
                json.dumps(
                    [(c.start, c.end, c.text) for c in primary], ensure_ascii=False
                ).encode()
            ).hexdigest()
            fingerprints[content_hash].append({"slug": slug, "episode": episode})
            dialogue_hash = dialogue_fingerprint(primary)
            if dialogue_hash:
                dialogue_fingerprints[dialogue_hash].append(
                    {"slug": slug, "episode": episode}
                )
            if any(
                re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text) for text in dialogue
            ):
                issue("cjk_dialogue_requires_review", slug=slug, episode=episode)
            if any(
                len(
                    re.findall(
                        r"\b(?:the|and|you|your|this|that|with|have|what|from|they|will)\b",
                        text,
                        re.IGNORECASE,
                    )
                )
                >= 3
                and not re.search(r"[\u0400-\u04ff]", text)
                for text in dialogue
            ):
                issue("english_dialogue_requires_review", slug=slug, episode=episode)
            repeated = Counter(text for text in dialogue if len(text) >= 30)
            if repeated:
                text, frequency = repeated.most_common(1)[0]
                if frequency >= 10 and frequency / max(len(dialogue), 1) >= 0.10:
                    issue(
                        "repeated_dialogue_requires_review",
                        slug=slug,
                        episode=episode,
                        occurrences=frequency,
                        sample=text[:200],
                    )
            if dialogue and not any(
                re.search(r"[ӘәҒғҚқҢңӨөҰұҮүҺһІі]", text) for text in dialogue
            ):
                issue("kazakh_language_requires_review", slug=slug, episode=episode)
            rows.append(
                {
                    "episode": episode,
                    "language": "kk",
                    "filename": Path(next(iter(assets.values()))["path"]).name,
                    "files": links,
                    "assets": assets,
                    "quality_flags": sorted(
                        {f["code"] for f in findings[track_findings:]}
                    ),
                }
            )
        episodes = [row["episode"] for row in rows]
        if episodes and max(episodes) > max(50, len(episodes) * 5):
            issue("episode_numbering_requires_review", slug=slug, episodes=episodes)
        detail = {
            k: v
            for k, v in entry.items()
            if k
            not in {
                "translated_episodes",
                "translated_episodes_count",
                "api_url",
                "subtitles",
            }
        }
        detail.update(
            catalog_id=slug,
            id_namespace="legacy_unverified",
            metadata_status="unverified",
            coverage_status="unverified",
            translation_status="not_human_verified",
            translation_provenance="legacy_untraced",
            translated_episodes=episodes,
            quarantined_episodes=sorted(set(choices) - set(episodes)),
            translated_episodes_count=len(rows),
            available_episodes_count=len(rows),
            subtitles=rows,
            quality_issues_count=len(findings) - release_findings,
            api_url=base_url.rstrip("/") + f"/api/v1/anime/{slug}.json",
        )
        details.append(detail)
        if entry.get("id") is not None:
            identifiers[str(entry["id"])].append(detail)

    duplicates = [tracks for tracks in fingerprints.values() if len(tracks) > 1]
    for tracks in duplicates:
        issue("duplicate_episode_content", tracks=tracks)
    dialogue_duplicates = [
        tracks for tracks in dialogue_fingerprints.values() if len(tracks) > 1
    ]
    for tracks in dialogue_duplicates:
        issue("duplicate_dialogue_content", tracks=tracks)
    title_duplicates = duplicate_title_groups(metadata)
    for group in title_duplicates:
        issue("duplicate_title_identity", slugs=group)
    for identifier, entries in identifiers.items():
        if len(entries) > 1:
            issue(
                "ambiguous_legacy_id", id=identifier, slugs=[a["slug"] for a in entries]
            )
    for slug in sorted(set(by_slug) - set(slugs)):
        issue("unlisted_tracked_release", slug=slug)
    # Cross-release findings are discovered only after scanning the whole archive.
    # Propagate them before serializing details so API clients see the same warnings.
    apply_quality_findings(details, findings)
    summary = [{k: v for k, v in item.items() if k != "subtitles"} for item in details]
    catalog = {
        "schema_version": "1.1",
        "total": len(summary),
        "total_episodes": sum(a["available_episodes_count"] for a in summary),
        "total_files": sum(len(by_slug[slug]) for slug in slugs),
        "language": "kk",
        "repository": REPOSITORY,
        "base_url": base_url.rstrip("/"),
        "data": summary,
    }
    stats = {k: v for k, v in catalog.items() if k != "data"}
    stats.update(
        counting_unit="release_entries_and_episode_tracks",
        source_episode_tracks=source_episode_count,
        quarantined_episode_tracks=source_episode_count - catalog["total_episodes"],
        reviewed_quarantined_episode_tracks=len(quarantines),
        unique_legacy_ids=len(identifiers),
        ambiguous_legacy_ids=sum(len(v) > 1 for v in identifiers.values()),
        canonical_format_files=selected_formats,
        unique_episode_contents=len(fingerprints),
        duplicate_content_groups=len(duplicates),
        duplicate_dialogue_groups=len(dialogue_duplicates),
        duplicate_title_groups=len(title_duplicates),
        translation_provenance="legacy_untraced",
        cue_count=all_cue_count,
        canonical_bytes=raw_bytes_total,
        human_verified_translations=0,
        complete_series_verified=0,
        translation_accuracy="not_verified",
        metadata_accuracy="not_verified",
        issue_counts=dict(sorted(counts.items())),
    )
    api = output_root / "api/v1"
    for detail in details:
        write_json(api / "anime" / f"{detail['slug']}.json", detail)
    for identifier, entries in sorted(identifiers.items()):
        if not re.fullmatch(r"\d+", identifier):
            continue
        alias = (
            entries[0]
            if len(entries) == 1
            else {
                "error": {
                    "code": "ambiguous_legacy_id",
                    "message": "Use a release slug; this legacy ID matches multiple entries.",
                },
                "matches": [
                    {"slug": a["slug"], "api_url": a["api_url"]} for a in entries
                ],
            }
        )
        write_json(api / "anime" / f"{identifier}.json", alias)
    expected = {a["slug"] + ".json" for a in details} | {
        key + ".json" for key in identifiers if key.isdigit()
    }
    # Only stale generated JSON is removed, never subtitle files or authored pages.
    for old in (api / "anime").glob("*.json"):
        if old.name not in expected:
            old.unlink()
    write_json(api / "anime.json", catalog)
    write_json(api / "stats.json", stats)
    write_json(
        api / "audit.json",
        {
            "schema_version": "1.0",
            "scope": "tracked assets in the source checkout",
            "translation_accuracy": "not_verified",
            "issue_counts": dict(sorted(counts.items())),
            "findings": findings,
        },
    )
    write_discovery(output_root, catalog, stats, base_url)
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--metadata", type=Path, default=Path("data/catalog.json"))
    parser.add_argument("--base-url", default=SITE)
    parser.add_argument("--no-copy-subtitles", action="store_true")
    args = parser.parse_args()
    result = build(
        args.source_root,
        args.output,
        args.metadata,
        copy_subtitles=not args.no_copy_subtitles,
        base_url=args.base_url,
    )
    print(
        json.dumps(
            {key: result[key] for key in ("total", "total_episodes", "total_files")}
        )
    )


if __name__ == "__main__":
    main()
