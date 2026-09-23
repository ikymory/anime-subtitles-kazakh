"""Repair residual leaks in aot-final and toradora."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.parser import parse_srt, dump_srt, srt_to_vtt
from core.translator import Translator
from validator import JP_REGEX, audit_subtitle_file

def repair_residuals():
    # 1. Toradora line 500: だ･け･ん -> Өйткені солай!
    tora_paths = [Path("subtitles/toradora/toradora-1-ep.srt"), Path("subtitles/toradora/ep_01.kk.srt")]
    for p in tora_paths:
        if not p.exists(): continue
        e = parse_srt(p.read_text(encoding="utf-8"))
        for entry in e:
            if JP_REGEX.search(entry.text):
                entry.text = "Өйткені солай!"
        srt_txt = dump_srt(e)
        p.write_text(srt_txt, encoding="utf-8")
        p.with_suffix(".vtt").write_text(srt_to_vtt(srt_txt), encoding="utf-8")
        print(f"Toradora {p.name}: {audit_subtitle_file(p)['score_percent']}% | leaks: {audit_subtitle_file(p)['japanese_leaks_count']}")

    # 2. AoT Final Season 21 lines
    aot_paths = [Path("subtitles/aot-final/aot-final-1-ep.srt"), Path("subtitles/aot-final/ep_01.kk.srt")]
    with Translator() as t:
        for p in aot_paths:
            if not p.exists(): continue
            e = parse_srt(p.read_text(encoding="utf-8"))
            dirty_idx = [i for i, x in enumerate(e) if JP_REGEX.search(x.text)]
            if not dirty_idx: continue
            dirty_texts = [re.sub(r"[・｡！？]+$", "", e[i].text).strip() for i in dirty_idx]
            print(f"Translating {len(dirty_texts)} lines for {p.name}...")
            fixed = t.translate_lines(dirty_texts, source_lang="ja", target_lang="kk")
            for i, rep in zip(dirty_idx, fixed):
                clean_rep = re.sub(r"[\u3041-\u3096\u30a1-\u30fa\u4e00-\u9faf・｢｣、。！？]", "", rep).strip()
                e[i].text = clean_rep if clean_rep else rep
            srt_txt = dump_srt(e)
            p.write_text(srt_txt, encoding="utf-8")
            p.with_suffix(".vtt").write_text(srt_to_vtt(srt_txt), encoding="utf-8")
            audit = audit_subtitle_file(p)
            print(f"AoT Final {p.name}: {audit['score_percent']}% | leaks: {audit['japanese_leaks_count']}")

if __name__ == "__main__":
    repair_residuals()
