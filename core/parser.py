"""SRT and ASS subtitle parser, serializer, and converter."""
import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SubtitleEntry:
    index: int
    start: str
    end: str
    text: str
    raw_style: str = ""  # For ASS lines to preserve style/format fields

def parse_srt(content: str) -> List[SubtitleEntry]:
    """Parse SRT content into structured SubtitleEntry items."""
    entries: List[SubtitleEntry] = []
    # Strip BOM if present
    content = content.lstrip("\ufeff").strip()
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue

        # Look for timestamp line (00:00:00,000 --> 00:00:00,000)
        time_idx = -1
        for i, line in enumerate(lines):
            if "-->" in line:
                time_idx = i
                break

        if time_idx == -1:
            continue

        times = [t.strip() for t in lines[time_idx].split("-->")]
        if len(times) != 2:
            continue

        start, end = times[0], times[1]
        try:
            idx = int(lines[0]) if time_idx > 0 and lines[0].isdigit() else len(entries) + 1
        except ValueError:
            idx = len(entries) + 1

        text = "\n".join(lines[time_idx + 1:])
        entries.append(SubtitleEntry(index=idx, start=start, end=end, text=text))

    return entries

def dump_srt(entries: List[SubtitleEntry]) -> str:
    """Serialize SubtitleEntry items into valid SRT format."""
    blocks = []
    for i, entry in enumerate(entries, 1):
        blocks.append(f"{i}\n{entry.start} --> {entry.end}\n{entry.text.strip()}\n")
    return "\n".join(blocks)

def parse_ass(content: str) -> Tuple[List[str], List[SubtitleEntry]]:
    """Parse ASS/SSA content. Returns (header_lines, dialogue_entries)."""
    header_lines: List[str] = []
    entries: List[SubtitleEntry] = []
    content = content.lstrip("\ufeff")
    lines = content.replace("\r\n", "\n").split("\n")

    in_events = False
    format_cols = 10
    idx = 1

    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "[events]":
            in_events = True
            header_lines.append(line)
            continue

        if not in_events:
            header_lines.append(line)
            continue

        if stripped.lower().startswith("format:"):
            header_lines.append(line)
            parts = [p.strip() for p in stripped.split(":", 1)[1].split(",")]
            format_cols = len(parts)
            continue

        if stripped.lower().startswith("dialogue:"):
            # Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            prefix, rest = line.split(":", 1)
            parts = rest.split(",", format_cols - 1)
            if len(parts) == format_cols:
                raw_prefix = prefix + ":" + ",".join(parts[:-1]) + ","
                text = parts[-1]
                start = parts[1].strip()
                end = parts[2].strip()
                entries.append(SubtitleEntry(index=idx, start=start, end=end, text=text, raw_style=raw_prefix))
                idx += 1
            else:
                header_lines.append(line)
        else:
            header_lines.append(line)

    return header_lines, entries

def dump_ass(header_lines: List[str], entries: List[SubtitleEntry]) -> str:
    """Serialize header and translated entries back to valid ASS format."""
    out = []
    for h in header_lines:
        out.append(h)
    for e in entries:
        out.append(f"{e.raw_style}{e.text}")
    return "\n".join(out)

def srt_to_vtt(content: str) -> str:
    """Convert SRT string to WebVTT string."""
    vtt = "WEBVTT\n\n"
    # replace 00:00:00,000 with 00:00:00.000
    cleaned = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", content)
    return vtt + cleaned

if __name__ == "__main__":
    # ponytail: assert self-checks, upgrade to pytest if complex tag parsing needed
    sample_srt = "1\n00:00:01,000 --> 00:00:03,000\nHello World\n\n2\n00:00:04,000 --> 00:00:06,000\nSecond line"
    parsed = parse_srt(sample_srt)
    assert len(parsed) == 2
    assert parsed[0].text == "Hello World"
    dumped = dump_srt(parsed)
    assert "00:00:01,000 --> 00:00:03,000" in dumped
    print("parser.py self-check passed.")
