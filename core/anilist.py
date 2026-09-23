"""AniList GraphQL metadata fetcher for top popular anime."""
import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ANILIST_API_URL = "https://graphql.anilist.co"
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "anime_top300.json"

QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      hasNextPage
    }
    media(sort: POPULARITY_DESC, type: ANIME) {
      id
      idMal
      title {
        romaji
        english
        native
      }
      synonyms
      format
      episodes
      seasonYear
      genres
      coverImage {
        large
      }
      bannerImage
      description
    }
  }
}
"""

def fetch_top_anime(limit: int = 300, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Fetch top popular anime from AniList GraphQL API, caching locally."""
    if use_cache and CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if len(data) >= limit:
                return data[:limit]

    results: List[Dict[str, Any]] = []
    page = 1
    per_page = 50

    while len(results) < limit:
        # ponytail: simple pagination loop, upgrade to backoff if AniList starts 429-ing
        req_data = json.dumps({
            "query": QUERY,
            "variables": {"page": page, "perPage": per_page}
        }).encode("utf-8")

        req = urllib.request.Request(
            ANILIST_API_URL,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AnimeSubtitlesKZ/1.0"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            media = body.get("data", {}).get("Page", {}).get("media", [])
            if not media:
                break
            results.extend(media)
            if not body.get("data", {}).get("Page", {}).get("pageInfo", {}).get("hasNextPage"):
                break

        page += 1

    results = results[:limit]

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

if __name__ == "__main__":
    anime = fetch_top_anime(10)
    print(f"Fetched {len(anime)} anime. Sample: {anime[0]['title']['romaji']}")
