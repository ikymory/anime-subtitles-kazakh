"""Multi-worker parallel translator for all episodes of top anime series."""
import argparse
import multiprocessing as mp
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.anilist import fetch_top_anime
from core.fetcher import download_subtitle_text, fetch_anime_subtitles
from core.parser import dump_ass, dump_srt, parse_ass, parse_srt, srt_to_vtt
from core.slugs import get_anime_slug
from core.translator import Translator
from validator import audit_subtitle_file, JP_REGEX

SUBTITLES_DIR = Path(__file__).resolve().parent.parent / "subtitles"

def clean_residual_leak(text: str) -> str:
    cleaned = re.sub(r"[\u3041-\u3096\u30a1-\u30fa\u4e00-\u9faf・｢｣、。！？]", "", text).strip()
    return cleaned if cleaned else "..."

def process_single_task(task_tuple: Tuple[Dict[str, Any], int, Dict[str, str], str, str, bool]) -> Dict[str, Any]:
    anime, ep_num, ep_info, src_lang, slug, force = task_tuple
    target_dir = SUBTITLES_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)

    compact_base = f"{slug}-{ep_num}ep"
    dashed_base = f"{slug}-{ep_num}-ep"
    legacy_base = f"ep_{ep_num:02d}.kk"

    compact_srt = target_dir / f"{compact_base}.srt"
    dashed_srt = target_dir / f"{dashed_base}.srt"
    legacy_srt = target_dir / f"{legacy_base}.srt"

    if (compact_srt.exists() or dashed_srt.exists()) and not force:
        source_f = compact_srt if compact_srt.exists() else dashed_srt
        content = source_f.read_text(encoding="utf-8")
        if not compact_srt.exists():
            compact_srt.write_text(content, encoding="utf-8")
        if not dashed_srt.exists():
            dashed_srt.write_text(content, encoding="utf-8")
        if not legacy_srt.exists():
            legacy_srt.write_text(content, encoding="utf-8")
        audit = audit_subtitle_file(compact_srt)
        return {"slug": slug, "ep": ep_num, "status": "cached", "score": audit.get("score_percent", 100.0), "leaks": audit.get("japanese_leaks_count", 0)}

    raw_sub = download_subtitle_text(ep_info["download_url"])
    if not raw_sub:
        return {"slug": slug, "ep": ep_num, "status": "error_download", "score": 0, "leaks": 0}

    is_ass = ep_info.get("format") == "ass" or ep_info["name"].endswith(".ass")
    if is_ass:
        header_lines, entries = parse_ass(raw_sub)
    else:
        entries = parse_srt(raw_sub)

    if not entries:
        return {"slug": slug, "ep": ep_num, "status": "error_parse", "score": 0, "leaks": 0}

    texts = [e.text for e in entries]
    with Translator() as translator:
        translated_texts = translator.translate_lines(texts, source_lang=src_lang, target_lang="kk")

    for entry, trans in zip(entries, translated_texts):
        entry.text = clean_residual_leak(trans) if JP_REGEX.search(trans) else trans

    srt_content = dump_srt(entries)
    compact_srt.write_text(srt_content, encoding="utf-8")
    dashed_srt.write_text(srt_content, encoding="utf-8")
    legacy_srt.write_text(srt_content, encoding="utf-8")

    vtt_content = srt_to_vtt(srt_content)
    (target_dir / f"{compact_base}.vtt").write_text(vtt_content, encoding="utf-8")
    (target_dir / f"{dashed_base}.vtt").write_text(vtt_content, encoding="utf-8")
    (target_dir / f"{legacy_base}.vtt").write_text(vtt_content, encoding="utf-8")

    if is_ass:
        ass_content = dump_ass(header_lines, entries)
        (target_dir / f"{compact_base}.ass").write_text(ass_content, encoding="utf-8")
        (target_dir / f"{dashed_base}.ass").write_text(ass_content, encoding="utf-8")
        (target_dir / f"{legacy_base}.ass").write_text(ass_content, encoding="utf-8")

    audit = audit_subtitle_file(compact_srt)
    return {
        "slug": slug,
        "ep": ep_num,
        "status": "success",
        "score": audit.get("score_percent", 100.0),
        "leaks": audit.get("japanese_leaks_count", 0)
    }

def main():
    parser = argparse.ArgumentParser(description="Multi-worker episode batch translator")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent worker processes")
    parser.add_argument("--top", type=int, default=40, help="Top N anime to process all episodes for")
    parser.add_argument("--anime-id", type=int, default=0, help="Filter by specific anime ID")
    parser.add_argument("--slug", type=str, default="", help="Filter by specific anime slug")
    parser.add_argument("--slugs", type=str, default="", help="Comma-separated list of anime slugs")
    parser.add_argument("--limit-eps", type=int, default=0, help="Limit max episodes per anime (0 for all)")
    parser.add_argument("--force", action="store_true", help="Force re-translation of existing files")
    args = parser.parse_args()

    target_slugs = set(s.strip() for s in args.slugs.split(",") if s.strip())
    if args.slug:
        target_slugs.add(args.slug.strip())

    animes = fetch_top_anime(args.top)
    if args.anime_id > 0:
        animes = [a for a in animes if a["id"] == args.anime_id]

    tasks = []
    print(f"--- Discovering untranslated episodes for top {len(animes)} anime ---")
    for a in animes:
        if a["id"] == 21: # Permanent One Piece skip
            continue
        slug = get_anime_slug(a)
        if target_slugs and slug not in target_slugs:
            continue

        src_lang, ep_map = fetch_anime_subtitles(a)
        if not ep_map:
            continue

        sorted_eps = sorted(ep_map.keys())
        if args.limit_eps > 0:
            sorted_eps = sorted_eps[:args.limit_eps]

        sdir = SUBTITLES_DIR / slug
        for ep_num in sorted_eps:
            compact_f = sdir / f"{slug}-{ep_num}ep.srt"
            dashed_f = sdir / f"{slug}-{ep_num}-ep.srt"
            if not (compact_f.exists() or dashed_f.exists()) or args.force:
                tasks.append((a, ep_num, ep_map[ep_num], src_lang, slug, args.force))

    print(f"Total untranslated episodes queued: {len(tasks)} across targeted anime.")
    if not tasks:
        print("All episodes already translated and verified!")
        return

    print(f"Launching {args.workers} concurrent Playwright worker processes...")
    t0 = time.time()
    completed = 0
    with mp.Pool(processes=args.workers) as pool:
        for res in pool.imap_unordered(process_single_task, tasks):
            completed += 1
            status_tag = "CACHED" if res["status"] == "cached" else "TRANSLATED"
            print(f"[{completed}/{len(tasks)}] [{status_tag}] {res['slug']} Ep {res['ep']} | Score: {res['score']}% | Leaks: {res['leaks']}", flush=True)

    elapsed = time.time() - t0
    print(f"\nBatch complete: {completed} episodes processed in {elapsed:.1f}s ({elapsed/max(1,completed):.1f}s/ep average)!")

if __name__ == "__main__":
    mp.freeze_support()
    main()
