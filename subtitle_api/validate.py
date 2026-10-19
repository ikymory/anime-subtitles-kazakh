"""Validate generated manifests and every advertised file's exact SHA-256."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from .subtitles import parse_subtitle


def validate(directory: Path) -> dict:
    root = Path(directory).resolve()
    api = root / "api/v1"
    catalog = json.loads((api / "anime.json").read_bytes())
    data = catalog["data"]
    if catalog["total"] != len(data) or len({a["slug"] for a in data}) != len(data):
        raise ValueError("Catalog totals or slugs are inconsistent")
    episodes = 0
    assets = 0
    for entry in data:
        detail = json.loads((api / "anime" / f"{entry['slug']}.json").read_bytes())
        rows = detail["subtitles"]
        actual = [row["episode"] for row in rows]
        if (
            actual != sorted(set(actual))
            or actual != entry["translated_episodes"]
            or actual != detail["translated_episodes"]
            or len(rows) != entry["available_episodes_count"]
        ):
            raise ValueError(f"Episode manifest mismatch: {entry['slug']}")
        episodes += len(rows)
        for row in rows:
            if not any(row["files"].values()):
                raise ValueError("Advertised episode has no download")
            for ext, url in row["files"].items():
                if not url:
                    continue
                asset = row["assets"][ext]
                base = detail["api_url"].rsplit("/api/v1/anime/", 1)[0]
                if url != base + "/" + quote(asset["path"], safe="/"):
                    raise ValueError(
                        f"Asset URL does not match its manifest path: {url}"
                    )
                path = (root / asset["path"]).resolve()
                if not path.is_relative_to(root / "subtitles"):
                    raise ValueError("Unsafe subtitle path")
                payload = path.read_bytes()
                if (
                    hashlib.sha256(payload).hexdigest() != asset["sha256"]
                    or len(payload) != asset["bytes"]
                ):
                    raise ValueError(f"Asset checksum mismatch: {path}")
                try:
                    cues = parse_subtitle(payload.decode("utf-8-sig"), ext)
                    if len(cues) != asset["cues"]:
                        raise ValueError("Cue count mismatch")
                except (UnicodeError, ValueError) as error:
                    raise ValueError(
                        f"Invalid exported subtitle: {path}: {error}"
                    ) from error
                assets += 1
    if episodes != catalog["total_episodes"]:
        raise ValueError("Episode total is inconsistent")
    stats = json.loads((api / "stats.json").read_bytes())
    if stats["total"] != len(data) or stats["total_episodes"] != episodes:
        raise ValueError("Statistics do not match catalog")
    return {
        "releases": len(data),
        "episode_tracks": episodes,
        "validated_downloads": assets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    args = parser.parse_args()
    print(json.dumps(validate(args.directory)))


if __name__ == "__main__":
    main()
