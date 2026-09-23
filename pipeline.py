"""Pipeline CLI orchestrator: top anime ingestion, subtitle fetching, and Kazakh translation."""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.anilist import fetch_top_anime
from core.fetcher import download_subtitle_text, fetch_anime_subtitles, get_kitsunekko_index
from core.parser import dump_ass, dump_srt, parse_ass, parse_srt, srt_to_vtt
from core.translator import Translator

SUBTITLES_DIR = Path(__file__).resolve().parent / "subtitles"
STATUS_FILE = Path(__file__).resolve().parent / "data" / "pipeline_status.json"

def load_status() -> Dict[str, Any]:
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_status(status: Dict[str, Any]):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def process_anime_episode(
    anime: Dict[str, Any],
    ep_num: int,
    ep_info: Dict[str, str],
    source_lang: str,
    translator: Translator,
    force: bool = False
) -> bool:
    anime_id = str(anime["id"])
    target_dir = SUBTITLES_DIR / anime_id
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"ep_{ep_num:02d}.kk"
    srt_out = target_dir / f"{base_name}.srt"
    ass_out = target_dir / f"{base_name}.ass"
    vtt_out = target_dir / f"{base_name}.vtt"

    if srt_out.exists() and not force:
        return True

    # 1. Download original
    raw_sub = download_subtitle_text(ep_info["download_url"])
    if not raw_sub:
        return False

    is_ass = ep_info.get("format") == "ass" or ep_info["name"].endswith(".ass")

    # 2. Parse & extract dialogue
    if is_ass:
        header_lines, entries = parse_ass(raw_sub)
    else:
        entries = parse_srt(raw_sub)

    if not entries:
        return False

    # 3. Translate dialogue texts
    texts = [e.text for e in entries]
    translated_texts = translator.translate_lines(texts, source_lang=source_lang, target_lang="kk")

    for entry, trans in zip(entries, translated_texts):
        entry.text = trans

    # 4. Serialize to disk (SRT, ASS, VTT)
    if is_ass:
        ass_content = dump_ass(header_lines, entries)
        with open(ass_out, "w", encoding="utf-8") as f:
            f.write(ass_content)
        # Also generate clean SRT representation
        srt_content = dump_srt(entries)
        with open(srt_out, "w", encoding="utf-8") as f:
            f.write(srt_content)
    else:
        srt_content = dump_srt(entries)
        with open(srt_out, "w", encoding="utf-8") as f:
            f.write(srt_content)

    # Save VTT for web players
    with open(vtt_out, "w", encoding="utf-8") as f:
        f.write(srt_to_vtt(srt_content))

    return True

def run_pipeline(top_n: int = 300, max_episodes: int = 1, anime_id_filter: int = 0, force: bool = False):
    """Main pipeline execution."""
    print(f"--- Running Anime Subtitles Kazakh Pipeline (Top {top_n}, Max {max_episodes} eps) ---")
    translator = Translator()
    anime_list = fetch_top_anime(limit=top_n)
    index = get_kitsunekko_index()
    status = load_status()

    if anime_id_filter > 0:
        anime_list = [a for a in anime_list if a["id"] == anime_id_filter]

    success_count = 0
    total_episodes_processed = 0

    for idx, anime in enumerate(anime_list, 1):
        a_id = str(anime["id"])
        romaji_title = anime["title"]["romaji"]
        eng_title = anime["title"].get("english") or ""

        # Ignore ONE PIECE as requested (too long)
        if anime["id"] == 21 or "one piece" in romaji_title.lower() or "one piece" in eng_title.lower():
            print(f"[{idx}/{len(anime_list)}] ID {a_id}: {romaji_title} -> SKIPPED (ignored per user request: too long).")
            continue

        print(f"[{idx}/{len(anime_list)}] Resolving ID {a_id}: {romaji_title}...")

        src_lang, ep_map = fetch_anime_subtitles(anime, index)
        if not ep_map:
            print(f"  [!] No subtitles found for {romaji_title}")
            status[a_id] = {"status": "missing_subtitles", "episodes": []}
            continue

        sorted_eps = sorted(ep_map.keys())
        if max_episodes > 0:
            target_eps = sorted_eps[:max_episodes]
        else:
            target_eps = sorted_eps

        translated_eps = []
        for ep in target_eps:
            info = ep_map[ep]
            print(f"  -> Translating Ep {ep} ({info['format']}) from {src_lang.upper()} to KK...")
            ok = process_anime_episode(anime, ep, info, src_lang, translator, force=force)
            if ok:
                translated_eps.append(ep)
                total_episodes_processed += 1

        status[a_id] = {
            "title": romaji_title,
            "source_lang": src_lang,
            "total_available_episodes": len(ep_map),
            "translated_episodes": translated_eps,
            "updated_at": int(time.time())
        }
        save_status(status)
        if translated_eps:
            success_count += 1

    print(f"\nDone! Translated {total_episodes_processed} episodes across {success_count}/{len(anime_list)} anime.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anime Kazakh Subtitle Generator")
    parser.add_argument("--top", type=int, default=300, help="Top N popular anime (default 300)")
    parser.add_argument("--episodes", type=int, default=1, help="Max episodes per anime to translate (default 1)")
    parser.add_argument("--anime-id", type=int, default=0, help="Filter by specific AniList ID")
    parser.add_argument("--force", action="store_true", help="Force re-translation")
    args = parser.parse_args()

    run_pipeline(top_n=args.top, max_episodes=args.episodes, anime_id_filter=args.anime_id, force=args.force)
