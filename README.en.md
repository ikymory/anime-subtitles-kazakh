# Anime Subtitles Kazakh — Complete Catalog & API

<div align="center">

<p align="center">
  <a href="Kazakh.md">🇰🇿 <b>Қазақша</b></a> •
  <a href="English.md">🇬🇧 <b>English</b></a> •
  <a href="Japanese.md">🇯🇵 <b>日本語</b></a> •
  <a href="README.md">🏠 <b>Home</b></a>
</p>

[![Franchises](https://img.shields.io/badge/Anime%20Catalog-347%20Complete%20Titles-e11d48.svg?style=for-the-badge&logo=crunchyroll)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Episodes](https://img.shields.io/badge/Episodes-3%2C462%20Eps-3b82f6.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Files](https://img.shields.io/badge/Subtitle%20Files-23%2C660%2B-10b981.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Leaks](https://img.shields.io/badge/JP%20Character%20Leaks-0%20(Audited)-8b5cf6.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![CDN](https://img.shields.io/badge/CDN-jsDelivr%20%2F%20GitHub-f59e0b.svg?style=for-the-badge)](https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/)

<p align="center">
  <b>The largest open-access Kazakh (<code>kk</code>) anime subtitle archive and static JSON CDN API.</b><br>
  Every title is provided in universal <code>.srt</code>, browser-native <code>.vtt</code>, and styled <code>.ass</code> formats, verified for zero Japanese character leaks and 100% watermark compliance.
</p>

</div>

---

## 💎 Key Highlights

- **347 Complete Anime Franchises, Films & OVAs**: Full series coverage from Studio Ghibli masterpieces and Makoto Shinkai films to top-tier Shonen, Seinen, Isekai, and Slice-of-Life titles.
- **Triple Format Multi-Track**:
  - `.srt`: Universal compatibility with desktop players, TVs, and mobile hardware.
  - `.vtt`: Standards-compliant WebVTT with cues for HTML5 `<video>` embedding.
  - `.ass`: Advanced SubStation Alpha styling with crisp typography and layout positions.
- **Flawless Quality & Linguistic Precision**:
  - **Zero Japanese residue leaks**: Regex-verified clean Kazakh Cyrillic across 1,385,000+ dialogue cues.
  - **Correct character names**: Audited transliterations (e.g. *Frieren* `Фрирен`, *Eren* `Эрен`, *Luffy* `Луффи`, *All Might* `Оллмайт`).
  - **Deduplicated cues**: Frame-by-frame subtitle clutter, duplicate layers, and foreign fansub watermarks completely eliminated.
- **Global High-Speed CDN**: Instant streaming via jsDelivr and GitHub Pages.
- **Developer-Friendly REST API**: Static JSON endpoints for integrating subtitles into third-party streaming web portals and apps.

---

## 🌐 Public REST API & CDN Endpoints

### 1. Full Anime Catalog (Index)
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json
```
Response sample:
```json
{
  "total": 347,
  "updated_at": "2026-09-24T15:13:09Z",
  "catalog": [
    {
      "id": 154587,
      "slug": "frieren",
      "title_romaji": "Sousou no Frieren",
      "title_english": "Frieren: Beyond Journey's End",
      "format": "TV",
      "episodes_count": 28,
      "api_url": "https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/frieren.json"
    }
  ]
}
```

### 2. Single Anime Metadata & File Manifest
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/{slug}.json
```
Example (*Sousou no Frieren*):
```
https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/frieren.json
```

### 3. Direct Subtitle CDN Download URLs
Subtitles are served directly via global CDN using standard 3-filename patterns:

| Format | URL Pattern |
|---|---|
| **SRT** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.srt` |
| **SRT (Alt)** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/ep_{ep:02d}.kk.srt` |
| **VTT** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.vtt` |
| **ASS** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.ass` |

*Live Example (Frieren Episode 1)*:
- SRT: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.srt`
- VTT: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt`
- ASS: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.ass`

---

## 🎬 How to Use

### 1. In Media Players (VLC / MPV / PotPlayer)
1. Download the raw `.srt` or `.ass` file for your episode.
2. Place the video file and the subtitle file in the same directory with matching names:
   ```
   Frieren_E01.mkv
   Frieren_E01.kk.srt
   ```
   Or drag-and-drop the subtitle file directly into the running player window.

### 2. In Web Browsers (HTML5 `<video>`)
Embed subtitles with zero external dependencies:
```html
<video controls width="1280" height="720">
  <source src="frieren_ep01.mp4" type="video/mp4">
  <track
    label="Қазақша (Kazakh)"
    kind="subtitles"
    srclang="kk"
    src="https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt"
    default>
</video>
```

### 3. In Self-Hosted Media Servers (Plex / Jellyfin / Emby)
Name files following the standard ISO 639-1 language tag:
```
/Anime/
  /Sousou no Frieren (2023)/
    Sousou no Frieren - S01E01.mkv
    Sousou no Frieren - S01E01.kk.srt
```
Jellyfin and Plex will automatically identify and index the track as **Kazakh**.

---

## 🏆 Featured Collections (Sample of 347 Titles)

| Category | Featured Titles |
|---|---|
| **Studio Ghibli** | *Spirited Away*, *Princess Mononoke*, *Howl's Moving Castle*, *My Neighbor Totoro*, *Grave of the Fireflies*, *Castle in the Sky*, *Kiki's Delivery Service*, *Porco Rosso*, *Nausicaä* |
| **Auteur Films** | *Your Name*, *Weathering with You*, *Suzume*, *5 Centimeters per Second*, *A Silent Voice*, *I Want to Eat Your Pancreas*, *Perfect Blue*, *Paprika*, *The Girl Who Leapt Through Time* |
| **Top Shonen & Action** | *Attack on Titan* (S1-S4 Final), *Demon Slayer* (All Arcs), *Jujutsu Kaisen* (S1-S2), *Chainsaw Man*, *One Piece* (Stampede, Red), *Bleach*, *Naruto*, *My Hero Academia* (S1-S6) |
| **Acclaimed Drama & Mystery** | *Sousou no Frieren*, *Death Note*, *Steins;Gate*, *Monster*, *Vinland Saga* (S1-S2), *Violet Evergarden*, *Oshi no Ko*, *Odd Taxi*, *The Apothecary Diaries*, *Bocchi the Rock!* |
| **Sci-Fi & Cyberpunk** | *Neon Genesis Evangelion*, *Cowboy Bebop*, *Cyberpunk: Edgerunners*, *Code Geass* (R1-R2), *Akira*, *Psycho-Pass*, *Ghost in the Shell*, *Trigun* |

---

## 🔒 Copyright & Terms

- **Author & Translator**: `ikymory` ([@ikymory](https://github.com/ikymory)).
- **Project**: Anime Subtitles Kazakh.
- **License**: Provided freely for personal and non-commercial educational use.
- **Protection**: Modifying, removing, or stripping the `@ikymory` author watermarks, or claiming unauthorized translation authorship, is strictly prohibited.
