"""Subtitle search, matching, and download engine."""
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
INDEX_FILE = CACHE_DIR / "kitsunekko_index.json"

KITSUNEKKO_REPO = "Ajatt-Tools/kitsunekko-mirror"
KITSUNEKKO_RAW_BASE = f"https://raw.githubusercontent.com/{KITSUNEKKO_REPO}/main"
KITSUNEKKO_API_BASE = f"https://api.github.com/repos/{KITSUNEKKO_REPO}"

def _clean_str(s: Optional[str]) -> str:
    """Normalize string for fuzzy alphanumeric comparison."""
    if not s:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

def get_kitsunekko_index(refresh: bool = False) -> Dict[str, List[Dict[str, str]]]:
    """Fetch or load cached tree of all available anime folders in kitsunekko mirror."""
    if not refresh and INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    categories = ["anime_tv", "anime_movie"]
    index: Dict[str, List[Dict[str, str]]] = {"anime_tv": [], "anime_movie": []}

    for cat in categories:
        # ponytail: GitHub Trees API call, cached to disk to avoid rate limits
        url = f"{KITSUNEKKO_API_BASE}/git/trees/main:subtitles/{cat}"
        req = urllib.request.Request(url, headers={"User-Agent": "AnimeSubtitlesKZ/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("tree", []):
                    if item.get("type") == "tree":
                        index[cat].append({
                            "name": item["path"],
                            "path": f"subtitles/{cat}/{item['path']}",
                            "category": cat
                        })
        except Exception as e:
            print(f"Error fetching kitsunekko {cat} index: {e}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return index

def find_japanese_folder(anime: Dict[str, Any], index: Dict[str, List[Dict[str, str]]]) -> Optional[Dict[str, str]]:
    """Match AniList anime titles to kitsunekko folder."""
    all_folders: List[Dict[str, str]] = index.get("anime_tv", []) + index.get("anime_movie", [])
    cleaned_folders = {_clean_str(f["name"]): f for f in all_folders}

    # Candidate titles in priority order
    candidates = [
        anime.get("title", {}).get("romaji"),
        anime.get("title", {}).get("english"),
    ] + anime.get("synonyms", [])

    for title in candidates:
        if not title:
            continue
        cleaned = _clean_str(title)
        if not cleaned:
            continue

        # 1. Exact match
        if cleaned in cleaned_folders:
            return cleaned_folders[cleaned]

        # 2. Prefix / containment match
        if len(cleaned) >= 5:
            for k, folder in cleaned_folders.items():
                if k == cleaned or k.startswith(cleaned) or (len(k) >= 5 and cleaned.startswith(k)):
                    return folder

    return None

def fetch_folder_episodes(folder_info: Dict[str, str]) -> Dict[int, Dict[str, str]]:
    """List and group subtitle files by episode number for a folder."""
    folder_path = folder_info["path"]
    encoded_path = urllib.parse.quote(folder_path, safe="/")
    url = f"{KITSUNEKKO_API_BASE}/contents/{encoded_path}"
    req = urllib.request.Request(url, headers={"User-Agent": "AnimeSubtitlesKZ/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            files = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch files for {folder_path}: {e}")
        return {}

    episodes: Dict[int, Dict[str, str]] = {}
    encoded_folder = urllib.parse.quote(folder_path, safe="/")
    for f in files:
        name = f.get("name", "")
        if not (name.endswith(".srt") or name.endswith(".ass")):
            continue

        # Extract episode number
        # matches: - 01, Ep 01, Episode 01, _01_, etc.
        m = re.search(r"(?:^|[-_#\s]|ep|episode)[^\d]*?(\d{1,3})(?:[.\s\]_-]|$)", name, re.IGNORECASE)
        ep_num = int(m.group(1)) if m else 1

        # Prefer .srt over .ass for simpler rendering unless .ass is already present
        if ep_num not in episodes or (name.endswith(".srt") and not episodes[ep_num]["name"].endswith(".srt")):
            episodes[ep_num] = {
                "name": name,
                "download_url": f"{KITSUNEKKO_RAW_BASE}/{encoded_folder}/{urllib.parse.quote(name)}",
                "format": "srt" if name.endswith(".srt") else "ass"
            }

    # If no episode regex matched but file exists (e.g. movies)
    if not episodes and files:
        for f in files:
            name = f.get("name", "")
            if name.endswith(".srt") or name.endswith(".ass"):
                episodes[1] = {
                    "name": name,
                    "download_url": f"{KITSUNEKKO_RAW_BASE}/{encoded_folder}/{urllib.parse.quote(name)}",
                    "format": "srt" if name.endswith(".srt") else "ass"
                }
                break

    return episodes

def download_subtitle_text(download_url: str) -> Optional[str]:
    """Download raw subtitle text from URL, handling UTF-8 and BOM."""
    req = urllib.request.Request(download_url, headers={"User-Agent": "AnimeSubtitlesKZ/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            # Try utf-8-sig first to strip BOM, fallback to utf-8, shift-jis, cp1252
            for enc in ["utf-8-sig", "utf-8", "shift_jis", "cp932", "latin1"]:
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
    except Exception as e:
        print(f"Error downloading subtitle from {download_url}: {e}")
        return None
    return None

def fetch_anime_subtitles(anime: Dict[str, Any], index: Optional[Dict[str, List[Dict[str, str]]]] = None) -> Tuple[str, Dict[int, Dict[str, str]]]:
    """
    Locates subtitles for an anime: Japanese first, fallback to English.
    Returns (source_language: 'ja'|'en', {episode_number: episode_info}).
    """
    if index is None:
        index = get_kitsunekko_index()

    folder = find_japanese_folder(anime, index)
    if folder:
        eps = fetch_folder_episodes(folder)
        if eps:
            return "ja", eps

    # Fallback to English subtitles (tagged empty if unavailable)
    # ponytail: English fallback stub, expand with AnimeTosho/OpenSubtitles client when needed
    return "en", {}

if __name__ == "__main__":
    idx = get_kitsunekko_index()
    sample_anime = {"title": {"romaji": "Death Note", "english": "Death Note"}, "synonyms": []}
    lang, episodes = fetch_anime_subtitles(sample_anime, idx)
    print(f"Language: {lang}, Available episodes: {len(episodes)}")
    assert len(episodes) > 0
    print("fetcher.py self-check passed.")
