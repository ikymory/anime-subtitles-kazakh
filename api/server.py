"""FastAPI REST API server for Anime Subtitles Kazakh."""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from core.slugs import get_anime_slug
DATA_DIR = BASE_DIR / "data"
SUBTITLES_DIR = BASE_DIR / "subtitles"
ANIME_FILE = DATA_DIR / "anime_top300.json"
STATUS_FILE = DATA_DIR / "pipeline_status.json"

app = FastAPI(
    title="Anime Subtitles Kazakh API",
    description="REST API for Kazakh (Қазақша) subtitles of top popular anime.",
    version="1.0.0"
)

# Enable CORS for media players and web scrapers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _load_anime_catalog() -> List[Dict[str, Any]]:
    if ANIME_FILE.exists():
        with open(ANIME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _load_status() -> Dict[str, Any]:
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.get("/")
def get_root():
    catalog = _load_anime_catalog()
    status = _load_status()
    translated_count = sum(1 for v in status.values() if v.get("translated_episodes"))
    return {
        "name": "Anime Subtitles Kazakh API",
        "description": "Қазақ тіліндегі аниме субтитрлер каталогы мен API",
        "language": "kk",
        "total_catalog": len(catalog),
        "total_translated_anime": translated_count,
        "github_repository": "https://github.com/ikymory/anime-subtitles-kazakh",
        "docs_url": "/docs"
    }

@app.get("/api/v1/anime")
def list_anime(
    q: Optional[str] = Query(None, description="Search query in titles"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    catalog = _load_anime_catalog()
    status = _load_status()

    # Filter
    results = catalog
    if q:
        query_norm = q.lower()
        results = [
            a for a in results
            if query_norm in a.get("title", {}).get("romaji", "").lower()
            or query_norm in (a.get("title", {}).get("english") or "").lower()
            or query_norm in (a.get("title", {}).get("native") or "").lower()
            or any(query_norm in syn.lower() for syn in a.get("synonyms", []))
        ]

    if genre:
        genre_norm = genre.lower()
        results = [
            a for a in results
            if any(genre_norm == g.lower() for g in a.get("genres", []))
        ]

    total = len(results)
    start = (page - 1) * limit
    paginated = results[start:start + limit]

    items = []
    for a in paginated:
        a_id = str(a["id"])
        stat = status.get(a_id, {})
        items.append({
            "id": a["id"],
            "title": a.get("title"),
            "format": a.get("format"),
            "episodes": a.get("episodes"),
            "seasonYear": a.get("seasonYear"),
            "genres": a.get("genres", []),
            "coverImage": a.get("coverImage", {}).get("large"),
            "translated_episodes": stat.get("translated_episodes", [])
        })

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
        "data": items
    }

def _find_anime(id_or_slug: str) -> Optional[Dict[str, Any]]:
    catalog = _load_anime_catalog()
    for a in catalog:
        if str(a["id"]) == str(id_or_slug) or get_anime_slug(a) == str(id_or_slug).lower():
            return a
    return None

@app.get("/api/v1/anime/{id_or_slug}")
def get_anime_detail(id_or_slug: str):
    anime = _find_anime(id_or_slug)
    if not anime:
        raise HTTPException(status_code=404, detail="Anime not found")

    anime_id = str(anime["id"])
    slug = get_anime_slug(anime)
    status = _load_status().get(anime_id, {})

    anime_dir = SUBTITLES_DIR / slug if (SUBTITLES_DIR / slug).exists() else SUBTITLES_DIR / anime_id
    available_files = []
    if anime_dir.exists():
        for f in anime_dir.glob("*.srt"):
            available_files.append(f.name)

    return {
        "id": anime["id"],
        "slug": slug,
        "title": anime.get("title"),
        "format": anime.get("format"),
        "episodes": anime.get("episodes"),
        "seasonYear": anime.get("seasonYear"),
        "genres": anime.get("genres", []),
        "description": anime.get("description"),
        "coverImage": anime.get("coverImage", {}).get("large"),
        "bannerImage": anime.get("bannerImage"),
        "translation_status": status,
        "available_files": available_files
    }

@app.get("/api/v1/anime/{id_or_slug}/episodes/{ep}/subtitles")
def get_subtitles(
    id_or_slug: str,
    ep: int,
    format: str = Query("srt", pattern="^(srt|ass|vtt|json)$", description="Format: srt, ass, vtt, json")
):
    anime = _find_anime(id_or_slug)
    if not anime:
        raise HTTPException(status_code=404, detail=f"Anime '{id_or_slug}' not found")

    anime_id = str(anime["id"])
    slug = get_anime_slug(anime)

    anime_dir = SUBTITLES_DIR / slug if (SUBTITLES_DIR / slug).exists() else SUBTITLES_DIR / anime_id

    candidates = [
        anime_dir / f"{slug}-{ep}ep.{format}",
        anime_dir / f"{slug}-{ep}-ep.{format}",
        anime_dir / f"ep_{ep:02d}.kk.{format}",
        anime_dir / f"{slug}-{ep}ep.srt",
        anime_dir / f"{slug}-{ep}-ep.srt",
        anime_dir / f"ep_{ep:02d}.kk.srt"
    ]

    file_path = None
    for cand in candidates:
        if cand.exists():
            file_path = cand
            break

    if not file_path:
        raise HTTPException(status_code=404, detail=f"Kazakh subtitles for anime '{slug}' episode {ep} not found")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    media_types = {
        "srt": "text/plain; charset=utf-8",
        "ass": "text/plain; charset=utf-8",
        "vtt": "text/vtt; charset=utf-8",
        "json": "application/json; charset=utf-8"
    }

    return Response(content=content, media_type=media_types.get(format, "text/plain"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
