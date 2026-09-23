"""Pre-indexes episode inventory for top 300 anime from Kitsunekko mirror using multi-threading."""
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
EPISODES_CACHE = CACHE_DIR / "kitsunekko_episodes_cache.json"

from core.anilist import fetch_top_anime
from core.fetcher import _clean_str

def fetch_anime_episodes_worker(item):
    anime_id, matched_folder = item
    folder_sha = matched_folder["sha"]
    try:
        res = subprocess.run(
            ["gh", "api", f"repos/Ajatt-Tools/kitsunekko-mirror/git/trees/{folder_sha}?recursive=1"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )
        tree_json = json.loads(res.stdout)
        files = tree_json.get("tree", [])

        episodes = {}
        for f in files:
            name = f.get("path", "")
            if not (name.endswith(".srt") or name.endswith(".ass")):
                continue
            # Ignore OP/ED/credit songs
            if any(k in name.lower() for k in ["_ncop", "_nced", "ncop", "nced", "menu", "trailer", "preview"]):
                continue
            m = re.search(r"(?:^|[-_#\s]|ep|episode)[^\d]*?(\d{1,3})(?:[.\s\]_-]|$)", name, re.IGNORECASE)
            ep_num = int(m.group(1)) if m else 1

            dl_path = f"{matched_folder['path']}/{name}"
            encoded_path = urllib.parse.quote(dl_path, safe="/")
            dl_url = f"https://raw.githubusercontent.com/Ajatt-Tools/kitsunekko-mirror/main/{encoded_path}"

            if ep_num not in episodes or (name.endswith(".srt") and not episodes[ep_num]["name"].endswith(".srt")):
                episodes[ep_num] = {
                    "name": name,
                    "download_url": dl_url,
                    "format": "srt" if name.endswith(".srt") else "ass"
                }

        return anime_id, {
            "folder_name": matched_folder["name"],
            "folder_path": matched_folder["path"],
            "folder_sha": folder_sha,
            "episodes": {str(k): v for k, v in sorted(episodes.items())}
        }
    except Exception as e:
        print(f"Error fetching tree for {matched_folder['name']}: {e}", flush=True)
        return anime_id, None

def build_catalog_index():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    tv_data = json.load(open(CACHE_DIR / "kitsunekko_tv_tree.json", encoding="utf-8"))
    movie_data = json.load(open(CACHE_DIR / "kitsunekko_movie_tree.json", encoding="utf-8"))

    all_folders = []
    for item in tv_data.get("tree", []):
        all_folders.append({"name": item["path"], "path": f"subtitles/anime_tv/{item['path']}", "sha": item["sha"], "cat": "anime_tv"})
    for item in movie_data.get("tree", []):
        all_folders.append({"name": item["path"], "path": f"subtitles/anime_movie/{item['path']}", "sha": item["sha"], "cat": "anime_movie"})

    cleaned_map = {_clean_str(f["name"]): f for f in all_folders}

    cache = {}
    if EPISODES_CACHE.exists():
        try:
            with open(EPISODES_CACHE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    animes = fetch_top_anime(300)
    to_fetch = []

    for anime in animes:
        if anime["id"] == 21: # One Piece skip
            continue
        
        anime_id = str(anime["id"])
        cands = [anime.get("title", {}).get("romaji"), anime.get("title", {}).get("english")] + anime.get("synonyms", [])
        matched_folder = None
        for title in cands:
            if not title:
                continue
            c = _clean_str(title)
            if c in cleaned_map:
                matched_folder = cleaned_map[c]
                break
            if len(c) >= 5:
                for k, folder in cleaned_map.items():
                    if k == c or k.startswith(c) or (len(k) >= 5 and c.startswith(k)):
                        matched_folder = folder
                        break
            if matched_folder:
                break

        if not matched_folder:
            continue

        folder_sha = matched_folder["sha"]
        if anime_id in cache and cache[anime_id].get("folder_sha") == folder_sha and cache[anime_id].get("episodes"):
            continue

        to_fetch.append((anime_id, matched_folder))

    print(f"Total anime needing episode index: {len(to_fetch)} (already cached: {len(cache)})", flush=True)

    if to_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(fetch_anime_episodes_worker, item) for item in to_fetch]
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                a_id, res = fut.result()
                if res:
                    cache[a_id] = res
                done += 1
                if done % 20 == 0 or done == len(to_fetch):
                    print(f"[{done}/{len(to_fetch)}] Indexed...", flush=True)

        with open(EPISODES_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    total_with_eps = sum(1 for v in cache.values() if v.get("episodes"))
    print(f"Done! Total anime with episodes ready: {total_with_eps}/{len(cache)}", flush=True)

if __name__ == "__main__":
    build_catalog_index()
