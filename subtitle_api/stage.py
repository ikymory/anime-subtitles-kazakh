"""Stage canonical SRT/VTT for Pages within its 1 GB published-site limit."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from .build import FORMATS, write_json
from .subtitles import normalize_subtitle, parse_subtitle, render_subtitle


def stage(
    catalog_root: Path,
    source_root: Path,
    web_root: Path,
    output: Path,
    formats=("srt", "vtt"),
    max_bytes=1_000_000_000,
) -> dict:
    catalog_root, source_root, web_root, output = [
        Path(p).resolve() for p in (catalog_root, source_root, web_root, output)
    ]
    if not formats or not set(formats).issubset(FORMATS):
        raise ValueError("Unsupported publishing formats")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Staging directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "api.html", "catalog-runtime.js", "openapi.json"):
        src = web_root / name
        if src.exists():
            shutil.copyfile(src, output / name)
    (output / "api").mkdir(exist_ok=True)
    if (web_root / "api/index.html").exists():
        shutil.copyfile(web_root / "api/index.html", output / "api/index.html")
    api = catalog_root / "api/v1"
    catalog = json.loads((api / "anime.json").read_bytes())
    lookup = {}
    total_asset_bytes = 0
    total_assets = 0
    for summary in catalog["data"]:
        detail = json.loads((api / "anime" / f"{summary['slug']}.json").read_bytes())
        for row in detail["subtitles"]:
            original_assets = dict(row["assets"])
            source_cues = None
            for ext in FORMATS:
                if ext not in formats:
                    row["files"][ext] = None
                    row["assets"].pop(ext, None)
                    continue
                asset = original_assets.get(ext)
                if not asset:
                    continue
                relative = Path(asset["path"])
                source = (source_root / relative).resolve()
                destination = (output / relative).resolve()
                if not source.is_relative_to(
                    source_root / "subtitles"
                ) or not destination.is_relative_to(output / "subtitles"):
                    raise ValueError("Unsafe asset path")
                if asset["origin"] == "source":
                    payload = normalize_subtitle(
                        source.read_text(encoding="utf-8-sig"), ext
                    ).encode("utf-8")
                else:
                    if source_cues is None:
                        primary_ext = next(
                            e
                            for e in FORMATS
                            if original_assets.get(e, {}).get("origin") == "source"
                        )
                        primary_path = (
                            source_root / original_assets[primary_ext]["path"]
                        ).resolve()
                        if not primary_path.is_relative_to(source_root / "subtitles"):
                            raise ValueError("Unsafe primary asset path")
                        source_cues = parse_subtitle(
                            normalize_subtitle(
                                primary_path.read_text(encoding="utf-8-sig"),
                                primary_ext,
                            ),
                            primary_ext,
                        )
                    payload = render_subtitle(source_cues, ext).encode("utf-8")
                if hashlib.sha256(payload).hexdigest() != asset["sha256"]:
                    raise ValueError(f"Asset changed since build: {relative}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(payload)
                total_asset_bytes += len(payload)
                total_assets += 1
            row["available_formats"] = [ext for ext in formats if row["files"].get(ext)]
        detail["publishing_formats"] = list(formats)
        summary["publishing_formats"] = list(formats)
        write_json(output / "api/v1/anime" / f"{summary['slug']}.json", detail)
        lookup[summary["slug"]] = detail
    for alias in (api / "anime").glob("*.json"):
        if alias.stem.isdigit():
            item = json.loads(alias.read_bytes())
            write_json(
                output / "api/v1/anime" / alias.name,
                lookup[item["slug"]] if "slug" in item else item,
            )
    write_json(output / "api/v1/anime.json", catalog)
    shutil.copyfile(api / "audit.json", output / "api/v1/audit.json")
    stats = json.loads((api / "stats.json").read_bytes())
    stats.update(
        publishing_formats=list(formats),
        published_format_files=total_assets,
        published_subtitle_bytes=total_asset_bytes,
        alias_files_published=False,
    )
    write_json(output / "api/v1/stats.json", stats)
    size = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    if size > max_bytes:
        raise ValueError(
            f"Published site is {size} bytes, exceeding budget {max_bytes}"
        )
    return {
        "site_bytes": size,
        "published_format_files": total_assets,
        "formats": list(formats),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("dist"))
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--web-root", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, default=Path(".build/pages"))
    parser.add_argument("--formats", default="srt,vtt")
    args = parser.parse_args()
    print(
        json.dumps(
            stage(
                args.catalog,
                args.source_root,
                args.web_root,
                args.output,
                tuple(args.formats.split(",")),
            )
        )
    )


if __name__ == "__main__":
    main()
