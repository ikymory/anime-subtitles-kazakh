"""Static JSON API and GitHub Pages website builder."""
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SUBTITLES_DIR = BASE_DIR / "subtitles"
DIST_DIR = BASE_DIR / "dist"
ANIME_FILE = DATA_DIR / "anime_top300.json"
STATUS_FILE = DATA_DIR / "pipeline_status.json"

GITHUB_USER = "ikymory"
REPO_NAME = "anime-subtitles-kazakh"
CDN_BASE_URL = f"https://cdn.jsdelivr.net/gh/{GITHUB_USER}/{REPO_NAME}@main/subtitles"

def build_static_api():
    """Generates static JSON API files in dist/ for GitHub Pages and CDN."""
    print("Building static API and UI...")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    api_v1 = DIST_DIR / "api" / "v1"
    api_v1.mkdir(parents=True, exist_ok=True)
    anime_api_dir = api_v1 / "anime"
    anime_api_dir.mkdir(parents=True, exist_ok=True)

    catalog: List[Dict[str, Any]] = []
    if ANIME_FILE.exists():
        with open(ANIME_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)

    status: Dict[str, Any] = {}
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            status = json.load(f)

    # 1. Per-anime detail pages
    catalog_summary = []
    for a in catalog:
        a_id = str(a["id"])
        stat = status.get(a_id, {})
        anime_sub_dir = SUBTITLES_DIR / a_id

        episodes_data = []
        if anime_sub_dir.exists():
            for srt in sorted(anime_sub_dir.glob("*.kk.srt")):
                ep_num_str = srt.name.replace("ep_", "").replace(".kk.srt", "")
                try:
                    ep_num = int(ep_num_str)
                except ValueError:
                    ep_num = 1

                episodes_data.append({
                    "episode": ep_num,
                    "language": "kk",
                    "files": {
                        "srt": f"{CDN_BASE_URL}/{a_id}/ep_{ep_num:02d}.kk.srt",
                        "vtt": f"{CDN_BASE_URL}/{a_id}/ep_{ep_num:02d}.kk.vtt",
                        "ass": f"{CDN_BASE_URL}/{a_id}/ep_{ep_num:02d}.kk.ass" if (anime_sub_dir / f"ep_{ep_num:02d}.kk.ass").exists() else None
                    }
                })

        detail = {
            "id": a["id"],
            "title": a.get("title"),
            "format": a.get("format"),
            "episodes": a.get("episodes"),
            "seasonYear": a.get("seasonYear"),
            "genres": a.get("genres", []),
            "description": a.get("description"),
            "coverImage": a.get("coverImage", {}).get("large"),
            "bannerImage": a.get("bannerImage"),
            "translated_episodes": [e["episode"] for e in episodes_data],
            "subtitles": episodes_data
        }

        with open(anime_api_dir / f"{a_id}.json", "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)

        catalog_summary.append({
            "id": a["id"],
            "title": a.get("title"),
            "format": a.get("format"),
            "episodes": a.get("episodes"),
            "seasonYear": a.get("seasonYear"),
            "genres": a.get("genres", []),
            "coverImage": a.get("coverImage", {}).get("large"),
            "translated_episodes_count": len(episodes_data),
            "api_url": f"https://{GITHUB_USER}.github.io/{REPO_NAME}/api/v1/anime/{a_id}.json"
        })

    # 2. Main catalog JSON
    with open(api_v1 / "anime.json", "w", encoding="utf-8") as f:
        json.dump({
            "total": len(catalog_summary),
            "language": "kk",
            "repository": f"https://github.com/{GITHUB_USER}/{REPO_NAME}",
            "data": catalog_summary
        }, f, ensure_ascii=False, indent=2)

    # 3. Copy subtitles folder to dist
    dist_subs = DIST_DIR / "subtitles"
    if SUBTITLES_DIR.exists():
        if dist_subs.exists():
            shutil.rmtree(dist_subs)
        shutil.copytree(SUBTITLES_DIR, dist_subs)

    # 4. Generate Interactive Web Portal index.html
    html_content = f"""<!DOCTYPE html>
<html lang="kk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Anime Subtitles Kazakh | Қазақша Аниме Субтитрлері</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <header class="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
    <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="text-2xl">⚡</span>
        <div>
          <h1 class="font-bold text-lg leading-tight">Anime Subtitles Kazakh</h1>
          <p class="text-xs text-sky-400">Қазақша субтитрлер &middot; DeepL API</p>
        </div>
      </div>
      <div class="flex items-center space-x-4 text-sm">
        <a href="api/v1/anime.json" class="text-slate-400 hover:text-white transition">API JSON</a>
        <a href="https://github.com/{GITHUB_USER}/{REPO_NAME}" target="_blank" class="bg-sky-600 hover:bg-sky-500 text-white px-3 py-1.5 rounded-lg flex items-center space-x-2 transition font-medium">
          <i class="fab fa-github"></i>
          <span>GitHub</span>
        </a>
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto px-4 py-8">
    <section class="mb-8 text-center py-6 bg-gradient-to-b from-slate-900 to-slate-950 rounded-2xl border border-slate-800 shadow-xl">
      <h2 class="text-2xl md:text-3xl font-extrabold mb-2">Ең танымал 300 анимеге арналған қазақша субтитрлер</h2>
      <p class="text-slate-400 max-w-2xl mx-auto text-sm">Түпнұсқа жапонша субтитрлерден қазақ тіліне аударылған, кез келген видео ойнатқышқа (VLC, MPV, Web) дайын SRT/VTT/ASS файлдары.</p>
      <div class="mt-4 flex justify-center">
        <input id="searchInput" type="text" placeholder="Аниме атын іздеу (Death Note, Attack on Titan, etc.)..."
          class="w-full max-w-md px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-sm focus:outline-none focus:border-sky-500 transition">
      </div>
    </section>

    <div id="animeGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      <!-- Loaded dynamically via JS -->
    </div>
  </main>

  <footer class="border-t border-slate-800 py-6 text-center text-xs text-slate-500">
    <p>Ашық бастапқы жоба &middot; Деректер көзі: AniList & Kitsunekko &middot; Жинақтаушы: @{GITHUB_USER}</p>
  </footer>

  <script>
    let animeList = [];
    async function loadData() {{
      const res = await fetch('api/v1/anime.json');
      const data = await res.json();
      animeList = data.data;
      render(animeList);
    }}

    function render(list) {{
      const grid = document.getElementById('animeGrid');
      grid.innerHTML = '';
      list.forEach(a => {{
        const card = document.createElement('div');
        card.className = 'bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-sky-500 transition shadow-md flex flex-col';
        card.innerHTML = `
          <img src="${{a.coverImage || ''}}" alt="${{a.title.romaji}}" class="w-full h-48 object-cover bg-slate-800">
          <div class="p-3 flex-1 flex flex-col justify-between">
            <div>
              <h3 class="font-semibold text-xs text-white truncate" title="${{a.title.romaji}}">${{a.title.romaji}}</h3>
              <p class="text-[10px] text-slate-400 truncate">${{a.title.english || a.title.native || ''}}</p>
            </div>
            <div class="mt-3 flex items-center justify-between pt-2 border-t border-slate-800">
              <span class="text-[10px] text-sky-400 font-mono">${{a.translated_episodes_count > 0 ? a.translated_episodes_count + ' бөлім' : 'Кезекте'}}</span>
              <a href="api/v1/anime/${{a.id}}.json" target="_blank" class="text-[10px] text-slate-300 hover:text-white bg-slate-800 px-2 py-1 rounded">JSON</a>
            </div>
          </div>
        `;
        grid.appendChild(card);
      }});
    }}

    document.getElementById('searchInput').addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      const filtered = animeList.filter(a =>
        a.title.romaji.toLowerCase().includes(q) ||
        (a.title.english && a.title.english.toLowerCase().includes(q))
      );
      render(filtered);
    }});

    loadData();
  </script>
</body>
</html>
"""
    with open(DIST_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Static build complete. Files written to dist/")

if __name__ == "__main__":
    build_static_api()
