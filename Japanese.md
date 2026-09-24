# カザフ語アニメ字幕ライブラリ (Anime Subtitles Kazakh) — 公式カタログ & API

<div align="center">

<p align="center">
  <a href="Kazakh.md">🇰🇿 <b>Қазақша</b></a> •
  <a href="English.md">🇬🇧 <b>English</b></a> •
  <a href="Japanese.md">🇯🇵 <b>日本語</b></a> •
  <a href="README.md">🏠 <b>ホーム</b></a>
</p>

[![Franchises](https://img.shields.io/badge/収録アニメ-347作品%20完全収録-e11d48.svg?style=for-the-badge&logo=crunchyroll)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Episodes](https://img.shields.io/badge/総エピソード-3%2C462話-3b82f6.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Files](https://img.shields.io/badge/字幕ファイル数-23%2C660以上-10b981.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![Leaks](https://img.shields.io/badge/日本語残存リーク-0件%20(全件検証済)-8b5cf6.svg?style=for-the-badge)](https://ikymory.github.io/anime-subtitles-kazakh/)
[![CDN](https://img.shields.io/badge/CDN-jsDelivr%20%2F%20GitHub-f59e0b.svg?style=for-the-badge)](https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/)

<p align="center">
  <b>世界最大級のオープンアクセス・カザフ語（<code>kk</code>）アニメ字幕アーカイブおよび静的JSON CDN API。</b><br>
  全347作品を汎用 <code>.srt</code>、ウェブ標準 <code>.vtt</code>、高度スタイル対応 <code>.ass</code> で提供。日本語文字の残留リーク0件を保証し、100%のクレジットウォーターマーク認証を適用しています。
</p>

</div>

---

## 🌟 主な特徴

- **347作品以上の完全アニメシリーズ、劇場版映画、OVAを網羅**: スタジオジブリの全名作、新海誠監督作品、今敏監督作品、細田守監督作品をはじめ、主要な少年・青年・異世界・日常系・名作アニメを全エピソード網羅。
- **3種類のマルチフォーマット提供**:
  - `.srt`: PC向け動画プレイヤー（VLC, MPV, MPC-HC）、スマートテレビ、モバイル端末に対応する標準字幕。
  - `.vtt`: HTML5 `<video>` タグにネイティブ対応したWeb標準WebVTT字幕。
  - `.ass`: フォント、装飾、カラー、配置座標を精密に定義したAdvanced SubStation Alpha字幕。
- **徹底した品質管理と文字の整合性**:
  - **日本語残留リーク0件**: 1,385,000行以上の字幕キューに対して正規表現検査を実施し、文字化けや日本語の残留を完全に排除。
  - **正確なキャラクター名の表記**: カザフ語キリル文字の正確な音訳辞書を適用（例：『葬送のフリーレン』の「フリーレン」は `Фрирен` と統一。※ `Фрилен` などの誤訳を全件修正）。
  - **字幕の重複・肥大化を完全解消**: フレーム毎の細切れ重複キュー、作画ベクターデータ（`{\p1}`）の誤混入、他言語ファンサブ広告を徹底排除。
- **超高速グローバルCDN**: jsDelivrおよびGitHub Pagesを通じて、プレイヤーやウェブサイトへ直接遅延なく配信。
- **開発者向けオープンREST API**: アプリケーションや動画配信サイトに簡単に組み込める静的JSONエンドポイント。

---

## 🚀 公開REST API & CDN 仕様

### 1. 全アニメカタログ一覧 (JSON Index)
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime.json
```

レスポンス例:
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

### 2. 個別アニメ詳細メタデータ
```http
GET https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/{slug}.json
```
例（『葬送のフリーレン』）:
```
https://ikymory.github.io/anime-subtitles-kazakh/api/v1/anime/frieren.json
```

### 3. 字幕ファイルの直接ダウンロード (CDN URL)
jsDelivr CDNを使用して、以下の規則的なURL形式で直接読み込み可能です:

| フォーマット | URL形式 |
|---|---|
| **SRT** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.srt` |
| **SRT (標準)** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/ep_{ep:02d}.kk.srt` |
| **VTT** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.vtt` |
| **ASS** | `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/{slug}/{slug}-{ep}ep.ass` |

*実例（『葬送のフリーレン』 第1話）*:
- SRT: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.srt`
- VTT: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt`
- ASS: `https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.ass`

---

## 🎬 使い方

### 1. メディアプレイヤー（VLC / MPV / PotPlayer）での再生
1. 該当エピソードの `.srt` または `.ass` ファイルをダウンロードします。
2. アニメ動画ファイルと同じフォルダ内に同名で保存します:
   ```
   Frieren_E01.mkv
   Frieren_E01.kk.srt
   ```
   または再生中のプレイヤー画面へ字幕ファイルを直接ドラッグ＆ドロップしてください。

### 2. ウェブサイト埋め込み（HTML5 `<video>` タグ）
外部ライブラリ不要で、標準 `<track>` タグから直接読み込めます:
```html
<video controls width="1280" height="720">
  <source src="frieren_ep01.mp4" type="video/mp4">
  <track
    label="カザフ語 (Kazakh)"
    kind="subtitles"
    srclang="kk"
    src="https://cdn.jsdelivr.net/gh/ikymory/anime-subtitles-kazakh@main/subtitles/frieren/frieren-1ep.vtt"
    default>
</video>
```

### 3. 自宅メディアサーバー（Jellyfin / Plex / Emby）
国際規格 ISO 639-1 言語コード（`kk`）に沿ってファイル名を配置します:
```
/Anime/
  /Sousou no Frieren (2023)/
    Sousou no Frieren - S01E01.mkv
    Sousou no Frieren - S01E01.kk.srt
```
JellyfinやPlexは自動的にトラック言語を **カザフ語（Kazakh）** として認識します。

---

## 🏆 収録作品コレクション（347作品の一部）

| カテゴリ | 代表作品 |
|---|---|
| **スタジオジブリ名作選** | 『千と千尋の神隠し』『もののけ姫』『ハウルの動く城』『となりのトトロ』『火垂るの墓』『天空の城ラピュタ』『魔女の宅急便』『紅の豚』『風の谷のナウシカ』 |
| **映画監督・劇場版** | 『君の名は。』『天気の子』『すずめの戸締まり』『秒速5センチメートル』『聲の形』『君の膵臓をたべたい』『パーフェクトブルー』『パプリカ』『時をかける少女』 |
| **人気少年・アクション** | 『進撃の巨人』（全シーズン・完結編）『鬼滅の刃』（全編）『呪術廻戦』（第1・2期）『チェンソーマン』『ONE PIECE 劇場版』『BLEACH』『NARUTO』『僕のヒーローアカデミア』 |
| **名作ドラマ・サスペンス** | 『葬送のフリーレン』『DEATH NOTE』『STEINS;GATE』『MONSTER』『ヴィンランド・サガ』『ヴァイオレット・エヴァーガーデン』『【推しの子】』『薬屋のひとりごと』『ぼっち・ざ・ろっく！』 |
| **SF・サイバーパンク** | 『新世紀エヴァンゲリオン』『カウボーイビバップ』『サイバーパンク エッジランナーズ』『コードギアス 反逆のルルーシュ』『AKIRA』『PSYCHO-PASS』『攻殻機動隊』 |

---

## 📄 著作権および利用規約 (Copyright)

- **字幕制作者・翻訳者**: `ikymory` ([@ikymory](https://github.com/ikymory))。
- **プロジェクト名**: Anime Subtitles Kazakh。
- **ライセンス**: 個人利用および非営利の教育目的において無償で提供されます。
- **権利保護**: 字幕ファイル内に含まれる `@ikymory` のクレジット表記の改変、削除、および無断で自身が翻訳したと詐称する行為を固く禁じます。
