# Anime Subtitles Kazakh (Қазақша Аниме Субтитрлері)

<div align="center">

<p align="center">
  <a href="Kazakh.md"><img src="https://img.shields.io/badge/Тіл-Қазақша-00afca?style=for-the-badge&logo=target&logoColor=white" alt="Kazakh"></a>
  <a href="English.md"><img src="https://img.shields.io/badge/Language-English-1e293b?style=for-the-badge&logo=googletranslate&logoColor=white" alt="English"></a>
  <a href="Japanese.md"><img src="https://img.shields.io/badge/言語-日本語-e11d48?style=for-the-badge&logo=crunchyroll&logoColor=white" alt="Japanese"></a>
</p>

[![Catalog Size](https://img.shields.io/badge/Anime%20Catalog-347%20Complete%20Titles-e11d48.svg?style=flat-square&logo=crunchyroll)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Episodes](https://img.shields.io/badge/Episodes-3%2C462%20Total-3b82f6.svg?style=flat-square)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Files](https://img.shields.io/badge/Files-23%2C660%2B%20(.srt%20%7C%20.vtt%20%7C%20.ass)-10b981.svg?style=flat-square)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Character Leaks](https://img.shields.io/badge/JP%20Character%20Leaks-0%20(Audited)-8b5cf6.svg?style=flat-square)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Watermark](https://img.shields.io/badge/Watermarks-100%25%20Verified%20(@ikymory)-06b6d4.svg?style=flat-square)](https://github.com/ikymory)
[![CDN](https://img.shields.io/badge/CDN-jsDelivr%20%2F%20GitHub-f59e0b.svg?style=flat-square)](https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/)
[![License](https://img.shields.io/badge/License-MIT-gray.svg?style=flat-square)](LICENSE)

<br>

**The ultimate open-access repository of high-fidelity Kazakh (`kk`) subtitles for 347+ anime franchises, films, and OVAs.**<br>
Every release includes universal `.srt`, web-native `.vtt`, and typography-tuned `.ass` files served via high-speed global CDN and static REST API.

---

### 🌐 Read Documentation in Your Language:
[🇰🇿 **Қазақ тіліндегі толық нұсқаулық (Kazakh.md)**](Kazakh.md) &nbsp;|&nbsp; [🇬🇧 **Complete English Guide (English.md)**](English.md) &nbsp;|&nbsp; [🇯🇵 **日本語公式ドキュメント (Japanese.md)**](Japanese.md)

</div>

---

## ⚡ Quick Metric Overview

| Metric | Specification | Status |
|---|---|---|
| **Total Anime Franchises** | 347 complete series, movies & OVAs | Verified ✅ |
| **Total Episodes** | 3,462 episodes | 100% Translated ✅ |
| **Total Subtitle Files** | 23,660 files (`.srt`, `.vtt`, `.ass`) | Built & Synced ✅ |
| **Japanese Residue Leaks** | 0 characters across 1,385,000+ cues | Audited Clean ✅ |
| **Character Transliteration** | Strict glossary validation (e.g. *Frieren* `Фрирен`) | Standardized ✅ |
| **Deduplication Status** | Frame-by-frame and dual-track clutter eliminated | Zero Bloat ✅ |
| **Copyright Watermarks** | Intro & outro `@ikymory` verification | 100% Intact ✅ |

---

## 🚀 CDN & Instant API Access

### 1. Catalog Index API (JSON)
Access the full machine-readable catalog with metadata, episode counts, and download links:
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json
```

### 2. Single Anime API
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/{slug}.json
```
*Example (Sousou no Frieren)*:
`https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/frieren.json`

### 3. Direct Subtitle CDN Download Patterns
Subtitles are served through the jsDelivr global edge network:

```
https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{episode}ep.{ext}
```

- **Universal SRT**: `.../subtitles/frieren/frieren-1ep.srt`
- **Standard SRT**: `.../subtitles/frieren/ep_01.kk.srt`
- **HTML5 WebVTT**: `.../subtitles/frieren/frieren-1ep.vtt`
- **Styled ASS**: `.../subtitles/frieren/frieren-1ep.ass`

---

## 💻 Developer Code Integration

### JavaScript / Web Player (HTML5 `<video>`)
```html
<video controls width="1280" height="720">
  <source src="anime_episode.mp4" type="video/mp4">
  <track
    label="Қазақша (Kazakh)"
    kind="subtitles"
    srclang="kk"
    src="https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt"
    default>
</video>
```

### Fetch API Catalog (JavaScript)
```javascript
const response = await fetch('https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json');
const data = await response.json();
console.log(`Loaded ${data.total} Kazakh anime subtitle packages!`);
```

### Python API Client
```python
import requests

res = requests.get('https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/frieren.json')
anime = res.json()
print(f"Title: {anime['title_english']} | Episodes: {anime['episodes_count']}")
for ep_num, files in anime['episodes'].items():
    print(f"Episode {ep_num}: {files['srt']}")
```

---

## 📺 Media Player Setup Guide

- **VLC Media Player**: Download the `.srt` or `.ass` file and drop it into VLC, or name it alongside your video file:
  `Movie.mkv` and `Movie.kk.srt`.
- **MPV / PotPlayer / IINA**: Native support for stylized `.ass` typography, colors, and positioning.
- **Plex / Jellyfin / Emby**: Automatically identified as Kazakh audio/subtitle track when naming with `ep_01.kk.srt` or `{title}.kk.srt` (ISO 639-1 code `kk`).

---

## 📂 Catalog Directory Architecture

```
anime-subtitles-kazakh/
├── dist/                                  # Web portal & static JSON REST API
│   └── api/v1/
│       ├── anime.json                     # Complete catalog manifest
│       └── anime/{slug}.json              # Individual anime endpoint
├── subtitles/
│   ├── frieren/                           # Sousou no Frieren (28 ep)
│   │   ├── ep_01.kk.srt
│   │   ├── ep_01.kk.vtt
│   │   ├── ep_01.kk.ass
│   │   ├── frieren-1ep.srt
│   │   └── frieren-1-ep.srt
│   ├── aot/                               # Attack on Titan (All Seasons)
│   ├── dn/                                # Death Note (Complete)
│   ├── jojo/                              # JoJo's Bizarre Adventure
│   └── ...                                # 347 complete anime franchises
├── English.md                             # English Documentation
├── Kazakh.md                              # Қазақша толық құжаттама
├── Japanese.md                            # 日本語公式ドキュメント
└── README.md
```

---

## 📄 License & Protection

- **Author & Translator**: `ikymory` ([@ikymory](https://github.com/ikymory)).
- **Project**: Anime Subtitles Kazakh.
- **Terms**: Subtitles are provided free of charge for personal and educational enjoyment. Removing or altering the `@ikymory` copyright watermarks is strictly prohibited.
