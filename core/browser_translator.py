"""Headless browser neural translation engine for anime subtitles.

Zero-cost, zero-ban, high-throughput translation with full context support.
Uses Playwright with DOM-based indexed batching ([1] line, [2] line) for 100% line alignment.
"""
import os
import re
import sqlite3
import sys
import time
import urllib.parse
from pathlib import Path
from typing import List, Optional, Tuple
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CACHE_DB = Path(__file__).resolve().parent.parent / "data" / "translations_cache.sqlite"
JP_CHAR_REGEX = re.compile(r"[\u3040-\u30ff\u4e00-\u9faf]")

def preprocess_text(line: str) -> str:
    """Clean furigana ruby tags, ASS overrides, speaker tags, and sound effects."""
    if not line:
        return ""
    # Strip ASS overrides like {\pos(1,2)} or {\an8}
    cleaned = re.sub(r"\{[^\}]*\}", "", line)
    # Replace ASS newlines with space
    cleaned = cleaned.replace("\\N", " ").replace("\\n", " ")
    # Strip ruby furigana attached to kanji like 奴(やつ) -> 奴 or 漢字（かんじ） -> 漢字
    cleaned = re.sub(r"([\u4e00-\u9faf])[\(（][ぁ-んァ-ン]+[\)）]", r"\1", cleaned)
    # Strip speaker tag only if dialogue follows: e.g. "（エレン）何してるの" -> "何してるの"
    spk_dialogue = re.match(r"^[（\(][^）\)]+[）\)]\s*(\S.*)$", cleaned)
    if spk_dialogue:
        cleaned = spk_dialogue.group(1)
    # Clean whitespace
    return " ".join(cleaned.split())

class BrowserTranslator:
    def __init__(self):
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
        if not text:
            return ""
        with sqlite3.connect(CACHE_DB) as conn:
            cur = conn.execute(
                "SELECT translated_text FROM cache WHERE source_lang=? AND target_lang=? AND source_text=?",
                (source_lang.lower(), target_lang.lower(), text)
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                cached_val = row[0].strip()
                if cached_val != text.strip() and not JP_CHAR_REGEX.search(cached_val):
                    return cached_val
            return None

    def _set_cached(self, text: str, translated: str, source_lang: str, target_lang: str):
        if not translated or translated.strip() == text.strip() or JP_CHAR_REGEX.search(translated):
            return
        with sqlite3.connect(CACHE_DB) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
                (source_lang.lower(), target_lang.lower(), text, translated)
            )

    def _translate_batch(self, page, texts: List[str], source_lang: str = "ja", target_lang: str = "kk") -> List[str]:
        if not texts:
            return []

        # Number each line: [1] line1\n[2] line2...
        numbered_lines = [f"[{i + 1}] {t}" for i, t in enumerate(texts)]
        joined_text = "\n".join(numbered_lines)
        encoded = urllib.parse.quote(joined_text)
        url = f"https://translate.google.com/?sl={source_lang}&tl={target_lang}&text={encoded}&op=translate"

        results_map = {}
        try:
            page.goto(url, timeout=20000)
            page.wait_for_selector("span[jsname=\"W297wb\"]", timeout=12000)
            time.sleep(1.0)
            res_elements = page.locator("span[jsname=\"W297wb\"]").all_inner_texts()
            full_out = "".join(res_elements)

            curr_idx = None
            for seg in full_out.split("\n"):
                seg = seg.strip()
                if not seg:
                    continue
                m = re.match(r"^\[(\d+)\]\s*(.*)$", seg)
                if m:
                    curr_idx = int(m.group(1))
                    results_map[curr_idx] = m.group(2).strip()
                elif curr_idx is not None:
                    results_map[curr_idx] += " " + seg
        except Exception as e:
            print(f"     [!] Batch DOM error: {e}", flush=True)

        final_batch = []
        for i, original in enumerate(texts, 1):
            trans = results_map.get(i)
            if trans and not JP_CHAR_REGEX.search(trans):
                final_batch.append(trans)
            else:
                # Single fallback if index missing or had leak
                try:
                    single_enc = urllib.parse.quote(original)
                    page.goto(f"https://translate.google.com/?sl={source_lang}&tl={target_lang}&text={single_enc}&op=translate", timeout=10000)
                    page.wait_for_selector("span[jsname=\"W297wb\"]", timeout=6000)
                    single_res = "".join(page.locator("span[jsname=\"W297wb\"]").all_inner_texts()).strip()
                    if single_res and not JP_CHAR_REGEX.search(single_res):
                        final_batch.append(single_res)
                    else:
                        final_batch.append(original)
                except Exception:
                    final_batch.append(original)

        return final_batch

    def translate_lines(self, lines: List[str], source_lang: str = "ja", target_lang: str = "kk") -> List[str]:
        results: List[Optional[str]] = [None] * len(lines)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        # 1. Pre-process and check cache
        for idx, line in enumerate(lines):
            cleaned = preprocess_text(line)
            if not cleaned:
                results[idx] = ""
                continue

            cached = self._get_cached(cleaned, source_lang, target_lang)
            if cached is not None:
                results[idx] = cached
            else:
                missing_indices.append(idx)
                missing_texts.append(cleaned)

        if not missing_texts:
            return [r if r is not None else "" for r in results]

        print(f"  -> Translating {len(missing_texts)} lines via headless natural browser engine...", flush=True)

        # 2. Run Playwright in indexed batches of 35 lines
        batch_size = 35
        translated_all: List[str] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for c in range(0, len(missing_texts), batch_size):
                chunk = missing_texts[c:c + batch_size]
                chunk_res = self._translate_batch(page, chunk, source_lang=source_lang, target_lang=target_lang)
                translated_all.extend(chunk_res)
                print(f"     [{min(c + batch_size, len(missing_texts))}/{len(missing_texts)}] lines translated...", flush=True)

            browser.close()

        # 3. Store clean lines into SQLite cache and assign to results
        for orig, trans, idx in zip(missing_texts, translated_all, missing_indices):
            clean_trans = trans.strip()
            if clean_trans and clean_trans != orig and not JP_CHAR_REGEX.search(clean_trans):
                self._set_cached(orig, clean_trans, source_lang, target_lang)
                results[idx] = clean_trans
            else:
                results[idx] = clean_trans if clean_trans else orig

        return [r if r is not None else "" for r in results]

if __name__ == "__main__":
    bt = BrowserTranslator()
    sample = [
        "（アルミン）その日 人類は思い出した",
        "奴(やつ)らに支配されていた恐怖を",
        "鳥籠の中に とらわれていた屈辱を",
        "総員 戦闘用意！",
        "目標は１体だ 必ず仕留めろ！",
        "あっ また飲んでる",
        "お前らも一緒にどうだ？",
        "酒臭っ"
    ]
    t0 = time.time()
    out = bt.translate_lines(sample, source_lang="ja", target_lang="kk")
    print(f"\nTranslated {len(sample)} lines in {time.time() - t0:.2f}s:")
    for o, res in zip(sample, out):
        print(f"  {o} -> {res}")
    assert len(out) == len(sample)
    assert not JP_CHAR_REGEX.search("".join(out))
    print("\nBrowserTranslator self-check PASSED (100% clean, 0% leaks).")
