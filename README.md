# Anime Subtitles Kazakh (Қазақша Аниме Субтитрлері)

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Portal-sky.svg)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Language](https://img.shields.io/badge/Language-Kazakh%20(kk)-emerald.svg)](https://ikymory.github.io/anime-subtitles-kazakh/)

Ең танымал **300 анимеге** арналған қазақ тіліндегі ресми субтитрлер каталогы, REST API және GitHub CDN қызметі. Түпнұсқа жапонша субтитрлерден (қолжетімсіз болған жағдайда ағылшын тілінен) DeepL арқылы аударылған.

---

## 🌟 Жоба ерекшеліктері (Features)

- **300 ең танымал аниме**: AniList бойынша үздік рейтингті анимелер каталогы.
- **Жапон тілінен тікелей аударма**: Жапонша түпнұсқа таймингі мен мағынасы сақталған (Kitsunekko / Jimaku базасы).
- **Үш түрлі формат**: `.srt`, `.ass` (стильдерімен), `.vtt` (веб-плеерлерге арналған).
- **Тегін CDN API**: Кез келген веб-сайттан немесе мобильді қосымшадан jsDelivr / GitHub Pages арқылы тікелей қосу мүмкіндігі.
- **FastAPI жергілікті сервері**: Толық мәтінді іздеу және сүзу мүмкіндігі бар REST API.

---

## 🚀 CDN API Қолдану (Serverless / Direct Access)

Кез келген серверсіз субтитрлерді тікелей мына URL арқылы алуға болады:

### 1. Толық аниме тізімі (Catalog JSON)
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json
```

### 2. Жеке аниме мәліметтері (Anime Detail)
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/{anime_id}.json
```
*Мысалы (Death Note ID: 1535):* `https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/1535.json`

### 3. Тікелей субтитр жүктеу (Subtitles Direct Download)
- **SRT**: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{anime_id}/ep_{episode_number}.kk.srt`
- **VTT**: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{anime_id}/ep_{episode_number}.kk.vtt`
- **ASS**: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{anime_id}/ep_{episode_number}.kk.ass`

---

## 💻 Жергілікті REST API Сервері (Local FastAPI)

### Орнату (Installation)
```bash
git clone https://github.com/ikymory/anime-subtitles-kazakh.git
cd anime-subtitles-kazakh
pip install -r requirements.txt
```

### Серверді іске қосу (Run Server)
```bash
python api/server.py
```
Сервер `http://localhost:8000` мекенжайында қосылады.
- Swagger интерактивті құжаттама: `http://localhost:8000/docs`
- Каталог іздеу: `http://localhost:8000/api/v1/anime?q=Death+Note`

---

## ⚙️ Аударма конвейері (Pipeline CLI)

Конвейер жапонша субтитрлерді автоматты түрде тауып, қазақ тіліне аударады және сақтайды:

```bash
# DeepL API кілтін орнату (міндетті емес, кілтсіз тегін аударма режимі қосылады):
set DEEPL_API_KEY=your-api-key-here

# 300 анименің 1-бөлімін аудару:
python pipeline.py --top 300 --episodes 1

# Белгілі бір анимені толық аудару (мысалы Death Note ID 1535):
python pipeline.py --anime-id 1535 --episodes 0

# Статикалық API мен веб-порталды құрастыру:
python api/static_builder.py
```

---

## 📁 Жоба құрылымы (Repository Structure)

```
anime-subtitles-kazakh/
├── api/
│   ├── server.py             # FastAPI REST API қосымшасы
│   └── static_builder.py     # GitHub Pages үшін статикалық JSON құрастырушы
├── core/
│   ├── anilist.py            # AniList GraphQL арқылы 300 аниме метадерегін жинау
│   ├── fetcher.py            # Kitsunekko / Jimaku жапонша субтитр табушы
│   ├── parser.py             # SRT/ASS/VTT талдаушы және түрлендіруші
│   └── translator.py         # DeepL & Fallback аударма қозғалтқышы
├── data/
│   ├── anime_top300.json     # 300 анименің кэштелген метадеректері
│   └── translations_cache.sqlite # Қайталанбас аударма кэші
├── subtitles/
│   └── {anime_id}/           # Қазақша субтитр файлдары (.kk.srt, .kk.vtt, .kk.ass)
├── dist/                     # GitHub Pages-ке арналған статикалық сайт пен JSON API
├── pipeline.py               # Конвейерді іске қосу CLI скрипті
└── requirements.txt
```

---

## 📄 Лицензия (License)
MIT License.
Субтитрлер мен медиа деректері білім беру және коммерциялық емес мақсатта ұсынылған.
