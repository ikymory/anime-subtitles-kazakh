# Қазақша Аниме Субтитрлері (Anime Subtitles Kazakh) — Ресми Каталог & API

<div align="center">

<p align="center">
  <a href="Kazakh.md">🇰🇿 <b>Қазақша</b></a> •
  <a href="English.md">🇬🇧 <b>English</b></a> •
  <a href="Japanese.md">🇯🇵 <b>日本語</b></a> •
  <a href="README.md">🏠 <b>Басты бет</b></a>
</p>

[![Franchises](https://img.shields.io/badge/Аниме%20Каталогы-347%20Толық%20Атау-e11d48.svg?style=for-the-badge&logo=crunchyroll)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Episodes](https://img.shields.io/badge/Бөлімдер-3%2C462%20Эпизод-3b82f6.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Files](https://img.shields.io/badge/Субтитрлер-23%2C660%2B%20Файл-10b981.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Leaks](https://img.shields.io/badge/Жапон%20Таңбалары-0%20(Тексерілген)-8b5cf6.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![CDN](https://img.shields.io/badge/CDN-jsDelivr%20%2F%20GitHub-f59e0b.svg?style=for-the-badge)](https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/)

<p align="center">
  <b>Қазақ тіліндегі (<code>kk</code>) ең ірі ашық аниме субтитрлер каталогы, тегін REST API және GitHub CDN жүйесі.</b><br>
  Барлық анимелер әмбебап <code>.srt</code>, вебке арналған <code>.vtt</code> және сәнделген <code>.ass</code> форматтарында ұсынылған. Жапон таңбаларының қалып қоюы толық жойылған және 100% авторлық белгімен қорғалған.
</p>

</div>

---

## 🌟 Жинақтың негізгі артықшылықтары

- **347+ толық аниме франшизасы, фильмдері мен OVA-лары**: Studio Ghibli алтын қоры, Макото Синкай туындылары, Сатоси Кон шедеврлері, ең танымал Shonen, Seinen, Isekai, Romance, Slice of Life және культтік классикалар толық аударылған.
- **Үш түрлі стандартты формат**:
  - `.srt`: Компьютерлерге, ойнатқыштарға (VLC, MPV, PotPlayer), Smart TV және телефондарға арналған әмбебап формат.
  - `.vtt`: Браузерлерге, сайттарға және HTML5 `<video>` тегіне арналған WebVTT форматы.
  - `.ass`: Арнайы стильдері, түстері, орналасуы және өлшемдері бапталған Advanced SubStation Alpha форматы.
- **Мінсіз сапа және тіл тазалығы**:
  - **0 жапон таңбасының қалдығы**: Репозиторийдегі 1,385,000+ диалог жолы тексеріліп, жапон иероглифтері мен катакана қалдықтары толықтай тазартылған.
  - **Кейіпкерлер есімдерінің дұрыс транслитерациясы**: Қазақ тілінің үндестігіне сай бейімделген (мысалы: *Frieren* — `Фрирен`, *Eren* — `Эрен`, *Luffy* — `Луффи`, *All Might* — `Оллмайт`, *Tanjiro* — `Танджиро`).
  - **Қайталанатын субтитрлер толық жойылған**: Кадрлық қайталанулар мен қате аудармалар реттелген.
- **Халықаралық жоғары жылдамдықты CDN**: jsDelivr және GitHub Pages арқылы субтитрлерді кез келген ойнатқышқа жылдам қосу.
- **Бағдарламашыларға арналған тегін REST API**: Сайттар мен қосымшаларға субтитрлерді автоматты түрде қосуға арналған статикалық JSON жүйесі.

---

## 🚀 Ашық REST API & CDN Сілтемелері

### 1. Каталогтың толық тізімі (JSON Index)
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json
```

Жауап үлгісі:
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

### 2. Жеке анименің толық сипаттамасы мен файлдары
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/{slug}.json
```
Мысалы (*Sousou no Frieren*):
```
https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/frieren.json
```

### 3. Субтитрлерді тікелей жүктеу (CDN URLs)
Субтитрлерді jsDelivr CDN арқылы мына шаблон бойынша тікелей жүктеуге болады:

| Формат | URL Шаблоны |
|---|---|
| **SRT** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.srt` |
| **SRT (Қосымша)** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/ep_{ep:02d}.kk.srt` |
| **VTT** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.vtt` |
| **ASS** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.ass` |

*Нақты мысал (Фрирен, 1-бөлім)*:
- SRT: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.srt`
- VTT: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt`
- ASS: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.ass`

---

## 📺 Қолдану тәсілдері

### 1. Компьютердегі ойнатқыштар (VLC / MPV / PotPlayer)
1. Қажетті бөлімнің қазақша `.srt` немесе `.ass` субтитрін жүктеп алыңыз.
2. Видео файл мен субтитр файлын бір қапшыққа (папкаға) бірдей атпен орналастырыңыз:
   ```
   Frieren_E01.mkv
   Frieren_E01.kk.srt
   ```
   Немесе субтитр файлын ойнап жатқан бейне ойнатқыштың терезесіне сүйреп тастаңыз (Drag & Drop).

### 2. Веб-сайттар мен онлайн ойнатқыштарда (HTML5 `<video>`)
Сайттарға қосымша кітапханасыз тікелей қосу:
```html
<video controls width="1280" height="720">
  <source src="frieren_ep01.mp4" type="video/mp4">
  <track
    label="Қазақша"
    kind="subtitles"
    srclang="kk"
    src="https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt"
    default>
</video>
```

### 3. Медиа-серверлерде (Jellyfin / Plex / Emby)
Файлдарды ISO 639-1 халықаралық стандартты тіл белгісімен сақтаңыз:
```
/Anime/
  /Sousou no Frieren (2023)/
    Sousou no Frieren - S01E01.mkv
    Sousou no Frieren - S01E01.kk.srt
```
Jellyfin мен Plex оны бірден **Қазақша (Kazakh)** тілі деп таниды.

---

## 🏆 Танымал топтамалар (347 анименің ішінен)

| Бағыт | Танымал туындылар |
|---|---|
| **Studio Ghibli** | *Сен мен Чихироның саяхаты (Spirited Away)*, *Мононоке ханшайымы*, *Хаулдың қозғалмалы сарайы*, *Менің көршім Тоторо*, *Жарық қоңыздар қабірі*, *Аспандағы Лапута сарайы*, *Кикидің жеткізу қызметі*, *Порко Россо*, *Навсикая* |
| **Авторлық Фильмдер** | *Сенің есімің (Your Name)*, *Ауа райы баласы*, *Судзуме*, *Секундына 5 сантиметр*, *Дауыс пішіні (A Silent Voice)*, *Ұйқы безіңді жегім келеді*, *Көк түсті кемелдік*, *Паприка*, *Уақытпен секірген қыз* |
| **Ең үздік Сёнэн & Экшн** | *Титанға шабуыл (AOT)* (Барлық 4 маусым), *Жын қаруы (Demon Slayer)* (Барлық аркалар), *Сиқырлы шайқас (Jujutsu Kaisen)* (1-2 маусым), *Бензоара адамы*, *One Piece* (Фильмдері), *Bleach*, *Наруто*, *Менің қаһармандық академиям* (1-6 маусым) |
| **Танымал Драма & Детектив** | *Фрирен (Sousou no Frieren)*, *Өлім дәптері (Death Note)*, *Штайнс қақпасы (Steins;Gate)*, *Монстр*, *Винланд сагасы* (1-2 маусым), *Вайолет Эвергарден*, *Жұлдыз бала (Oshi no Ko)*, *Дәріханашы қыз күнделігі*, *Боччи-рок!* |
| **Ғылыми фантастика & Киберпанк** | *Евангелион (Evangelion)*, *Ковбой Бибоп*, *Киберпанк: Эджраннерс*, *Код Гиас* (R1-R2), *Акира*, *Психопаспарт*, *Сауыттағы елес*, *Триган* |

---

## 📄 Авторлық құқық және лицензия (Copyright)

- **Субтитрлер авторы**: `ikymory` ([@ikymory](https://github.com/ikymory)).
- **Жоба атауы**: Anime Subtitles Kazakh.
- **Лицензия**: Жеке және коммерциялық емес мақсатта пайдалану үшін тегін таратылады.
- **Қорғау**: Субтитрлердегі `@ikymory` авторлық белгілерін өзгертуге, өшіруге немесе аударманы өз атынан жариялауға қатаң тыйым салынады.
