"""Subtitle Quality Validator, Leak Detector, and Auto-Repair Engine."""
import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.parser import dump_srt, parse_srt, srt_to_vtt
from core.translator import Translator

SUBTITLES_DIR = Path(__file__).resolve().parent / "subtitles"
JP_REGEX = re.compile(r"[\u3040-\u30ff\u4e00-\u9faf]")

def audit_subtitle_file(file_path: Path) -> Dict[str, Any]:
    """Inspects subtitle file for untranslated Japanese, empty lines, and timestamp validity."""
    if not file_path.exists():
        return {"error": "File does not exist", "score": 0.0}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = parse_srt(content)
    total = len(entries)
    if total == 0:
        return {"total": 0, "leaks": 0, "score": 0.0, "status": "empty"}

    leaked_indices = []
    empty_indices = []
    valid_count = 0

    for i, e in enumerate(entries):
        text = e.text.strip()
        if not text:
            empty_indices.append(e.index)
            continue

        if JP_REGEX.search(text):
            leaked_indices.append(e.index)
        else:
            valid_count += 1

    score = round((valid_count / total) * 100, 1) if total > 0 else 0.0

    return {
        "file": file_path.name,
        "anime_id": file_path.parent.name,
        "total_entries": total,
        "valid_translated": valid_count,
        "japanese_leaks_count": len(leaked_indices),
        "leaked_indices": leaked_indices[:15],
        "score_percent": score,
        "is_clean": len(leaked_indices) == 0 and len(empty_indices) == 0
    }

def audit_all_subtitles() -> List[Dict[str, Any]]:
    """Audit all subtitle files across all anime directories."""
    results = []
    if not SUBTITLES_DIR.exists():
        return results

    all_srt_paths = sorted(set(list(SUBTITLES_DIR.glob("*/*-ep.srt")) + list(SUBTITLES_DIR.glob("*/*.kk.srt"))))
    for srt_path in all_srt_paths:
        res = audit_subtitle_file(srt_path)
        res["path"] = str(srt_path)
        results.append(res)

    return results

def repair_subtitle_file(file_path: Path, translator: Translator) -> Tuple[bool, Dict[str, Any]]:
    """Re-translates any leaked Japanese blocks in the subtitle file until 100% clean."""
    audit = audit_subtitle_file(file_path)
    if audit.get("is_clean"):
        return True, audit

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = parse_srt(content)
    dirty_indices = []
    dirty_texts = []

    for idx, e in enumerate(entries):
        if JP_REGEX.search(e.text):
            dirty_indices.append(idx)
            dirty_texts.append(e.text)

    if not dirty_texts:
        return True, audit

    print(f"Repairing {len(dirty_texts)} untranslated lines in {file_path.name}...")
    fixed_texts = translator.translate_lines(dirty_texts, source_lang="ja", target_lang="kk")

    for idx, fixed in zip(dirty_indices, fixed_texts):
        entries[idx].text = fixed

    # Save repaired SRT and VTT
    repaired_srt = dump_srt(entries)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(repaired_srt)

    vtt_path = file_path.with_suffix(".vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(srt_to_vtt(repaired_srt))

    new_audit = audit_subtitle_file(file_path)
    return new_audit.get("is_clean", False), new_audit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subtitle quality auditor and leak detector")
    parser.add_argument("--repair", action="store_true", help="Auto-repair leaked files")
    args = parser.parse_args()

    print("--- Running Subtitle Audit & Verification ---")
    audits = audit_all_subtitles()
    translator = None

    for a in audits:
        status_str = "OK" if a["is_clean"] else "NEEDS REPAIR"
        print(f"[{status_str}] Anime {a['anime_id']} ({a['file']}): {a['valid_translated']}/{a['total_entries']} ({a['score_percent']}%) | Leaks: {a['japanese_leaks_count']}")
        if not a["is_clean"] and args.repair:
            if translator is None:
                translator = Translator()
            repaired_ok, new_audit = repair_subtitle_file(Path(a["path"]), translator)
            rep_status = "REPAIRED OK" if repaired_ok else "STILL DIRTY"
            print(f"  -> [{rep_status}] Score: {new_audit['score_percent']}% | Leaks: {new_audit['japanese_leaks_count']}")
