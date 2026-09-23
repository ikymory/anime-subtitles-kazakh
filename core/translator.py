"""DeepL and resilient free fast neural translation client targeting Kazakh (kk)."""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CACHE_DB = Path(__file__).resolve().parent.parent / "data" / "translations_cache.sqlite"

class Translator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPL_API_KEY", "").strip()
        self.is_deepl_free = self.api_key.endswith(":fx")
        self._ddg_vqd: Optional[str] = None
        self._init_db()

    def _init_db(self):
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(CACHE_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    source_lang TEXT,
                    target_lang TEXT,
                    source_text TEXT PRIMARY KEY,
                    translated_text TEXT
                )
            """)

    def _get_cached(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        with sqlite3.connect(CACHE_DB) as conn:
            cur = conn.execute(
                "SELECT translated_text FROM cache WHERE source_lang=? AND target_lang=? AND source_text=?",
                (source_lang.lower(), target_lang.lower(), text)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def _set_cached(self, text: str, translated: str, source_lang: str, target_lang: str):
        if not translated or translated.strip() == text.strip():
            return
        with sqlite3.connect(CACHE_DB) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
                (source_lang.lower(), target_lang.lower(), text, translated)
            )

    def _translate_deepl(self, texts: List[str], source_lang: str, target_lang: str = "kk") -> List[str]:
        """Translate batch using official DeepL API (if key provided)."""
        base_url = "https://api-free.deepl.com/v2/translate" if self.is_deepl_free else "https://api.deepl.com/v2/translate"
        payload = {
            "text": texts,
            "target_lang": target_lang.upper(),
            "source_lang": source_lang.upper() if source_lang else None
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        req_data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            base_url,
            data=req_data,
            headers={
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AnimeSubtitlesKZ/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [t.get("text", "") for t in data.get("translations", [])]

    def _get_ddg_vqd(self) -> Optional[str]:
        """Fetch DuckDuckGo translation session token."""
        try:
            req = urllib.request.Request(
                "https://duckduckgo.com/?q=translate",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode("utf-8")
                m = re.search(r'vqd="([^"]+)"', html) or re.search(r"vqd='([^']+)'", html)
                return m.group(1) if m else None
        except Exception:
            return None

    def _translate_ddg_single(self, text: str, source_lang: str = "ja", target_lang: str = "kk") -> str:
        """Fast free neural translation via DuckDuckGo."""
        if not text.strip():
            return text

        if not self._ddg_vqd:
            self._ddg_vqd = self._get_ddg_vqd()

        if not self._ddg_vqd:
            return self._translate_google_single(text, source_lang, target_lang)

        url = f"https://duckduckgo.com/translation.js?query=translate&vqd={self._ddg_vqd}&to={target_lang}"
        req = urllib.request.Request(
            url,
            data=text.encode("utf-8"),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                trans = res.get("translated", "")
                if trans:
                    return trans
        except Exception:
            # Refresh token on error
            self._ddg_vqd = self._get_ddg_vqd()

        return self._translate_google_single(text, source_lang, target_lang)

    def _translate_google_single(self, text: str, source_lang: str, target_lang: str = "kk") -> str:
        """Google Translate fallback."""
        if not text.strip():
            return text
        post_data = urllib.parse.urlencode({"q": text}).encode("utf-8")
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t"
        req = urllib.request.Request(
            url,
            data=post_data,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Content-Type": "application/x-www-form-urlencoded"}
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return "".join(part[0] for part in data[0] if part and part[0])
        except Exception:
            return text

    def translate_lines(self, lines: List[str], source_lang: str = "ja", target_lang: str = "kk") -> List[str]:
        """Translates a list of subtitle lines, checking cache first, using free fast neural engines."""
        results: List[Optional[str]] = [None] * len(lines)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        # 1. Check cache
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                results[i] = line
                continue

            cached = self._get_cached(stripped, source_lang, target_lang)
            if cached is not None and cached != stripped:
                results[i] = cached
            else:
                missing_indices.append(i)
                missing_texts.append(stripped)

        if not missing_texts:
            return [r if r is not None else "" for r in results]

        # 2. Official DeepL API if key provided
        if self.api_key:
            chunk_size = 30
            for c in range(0, len(missing_texts), chunk_size):
                chunk = missing_texts[c:c + chunk_size]
                try:
                    res = self._translate_deepl(chunk, source_lang, target_lang)
                    for idx, orig, trans in zip(missing_indices[c:c + chunk_size], chunk, res):
                        if trans and trans.strip() != orig.strip():
                            self._set_cached(orig, trans, source_lang, target_lang)
                        results[idx] = trans
                    continue
                except Exception as e:
                    print(f"DeepL API key error ({e}), switching to free fast neural engine...")
                    break

        # 3. Free neural translation for remaining missing lines
        for idx, text in zip(missing_indices, missing_texts):
            if results[idx] is not None:
                continue
            trans = self._translate_ddg_single(text, source_lang=source_lang, target_lang=target_lang)
            if trans and trans.strip() != text.strip():
                self._set_cached(text, trans, source_lang, target_lang)
                results[idx] = trans
            else:
                results[idx] = text
            time.sleep(0.04)

        return [r if r is not None else "" for r in results]

if __name__ == "__main__":
    t = Translator()
    out = t.translate_lines(["なに？", "その日 人類は思い出した"], source_lang="ja", target_lang="kk")
    print(f"Translated: {out}")
    assert len(out) == 2
    assert out[0] != "なに？"
    print("translator.py self-check passed.")
