# Anime Subtitles Kazakh (Қазақша Аниме Субтитрлері)

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Portal-sky.svg)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Language](https://img.shields.io/badge/Language-Kazakh%20(kk)-emerald.svg)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Author](https://img.shields.io/badge/Author-ikymory-purple.svg)](https://github.com/ikymory)

Ең танымал анимелерге арналған толық қазақша субтитрлер каталогы, REST API және GitHub CDN қызметі. Барлық субтитрлер кез келген заманауи видео ойнатқышқа (VLC, MPV, MPC-HC, Smart TV, Web) дайын.

---

## 🌟 Жинақ ерекшеліктері (Features)

- **247+ толық аниме франшизасы, фильмдері мен OVA-лары**: Studio Ghibli алтын қоры, Макото Синкай, Сатоси Кон, Мамору Хосода шедеврлері, ең танымал Shonen, Seinen, Isekai, Romance және культтік классикалар толық қамтылған.
- **Үш түрлі формат**:
  - `.srt` — стандартты және әмбебап субтитрлер.
  - `.vtt` — браузерлер мен веб-плеерлерге арналған WebVTT форматы.
  - `.ass` — стильдері мен түстері бапталған кеңейтілген субтитрлер.
- **Авторлық белгі (Watermark)**: Барлық субтитрлерде кіріспе және қорытынды авторлық белгі сақталған (`@ikymory`).
- **Тегін CDN & API**: Кез келген веб-сайттан немесе мобильді қосымшадан jsDelivr / GitHub Pages арқылы тікелей қосу мүмкіндігі.

---

## 🚀 CDN & Тікелей жүктеу (Direct Access / CDN)

Субтитрлерді тікелей мына URL мекенжайлары арқылы ойнатқышыңызға қосуға немесе жүктеп алуға болады:

### 1. Каталог API (JSON)
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json
```

### 2. Жеке аниме мәліметтері
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/{slug}.json
```
*Мысалы (Death Note):* `https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/dn.json`

### 3. Тікелей субтитр жүктеу (Subtitles Direct Download)
- **SRT үлгісі**: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{episode}ep.srt`
- **VTT үлгісі**: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{episode}ep.vtt`
- **ASS үлгісі**: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{episode}ep.ass`

---

## 📺 Қолдану жолы (How to Use)

1. **Компьютерде (VLC / MPV / PotPlayer)**:
   - Аниме видеосын және оған сәйкес келетін қазақша `.srt` немесе `.ass` субтитрін жүктеп алыңыз.
   - Видео мен субтитр файлын бір қапшыққа (папкаға) салып, ойнатқышқа сүйреп тастаңыз (Drag & Drop).

2. **Веб-сайттар мен онлайн ойнатқыштарда**:
   - `<track>` тегі арқылы jsDelivr CDN сілтемесіндегі `.vtt` файлын тікелей қосыңыз:
   ```html
   <video controls>
     <source src="anime_ep1.mp4" type="video/mp4">
     <track label="Қазақша" kind="subtitles" srclang="kk" src="https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/dn/dn-1-ep.vtt" default>
   </video>
   ```

---

## 📁 Каталог құрылымы (Structure)

```
anime-subtitles-kazakh/
├── dist/                     # GitHub Pages веб-порталы мен статикалық JSON API
├── subtitles/
│   ├── dn/                   # Death Note (Барлық бөлімдер)
│   ├── aot/                  # Attack on Titan (Барлық маусымдар)
│   ├── jojo/                 # JoJo's Bizarre Adventure (Барлық бөлімдер)
│   └── ...                   # 247+ толық аниме мен фильмдер (.srt, .vtt, .ass)
└── README.md
```

---

## 📄 Авторлық құқық және лицензия (Copyright)

- Барлық қазақша субтитрлердің авторы: **ikymory** (`@ikymory`).
- Субтитрлер жеке және коммерциялық емес мақсатта тегін пайдалануға берілген.
- Субтитрлердегі авторлық белгілерді жоюға, өзгертуге немесе басқа адамның атынан жариялауға тыйым салынады.
