"""Strict structural parsers. Successful parsing does not verify a translation."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    start: int
    end: int
    text: str


def normalize_subtitle(text: str, ext: str) -> str:
    """Repair timestamp serialization only; retain dialogue, styling and timing."""
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")

    def normalize_time(value: str) -> str:
        match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})", value.strip())
        if not match:
            return value
        h, m, s, fraction = match.groups()
        total = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(
            fraction.ljust(3, "0")
        )
        hours, rest = divmod(total, 3600000)
        minutes, rest = divmod(rest, 60000)
        seconds, milliseconds = divmod(rest, 1000)
        if ext == "ass":
            return f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds // 10:02d}"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}{',' if ext == 'srt' else '.'}{milliseconds:03d}"

    if ext in ("srt", "vtt"):
        normalized = re.sub(
            r"^(\S+)(\s+-->\s+)(\S+)",
            lambda m: normalize_time(m[1]) + m[2] + normalize_time(m[3]),
            text,
            flags=re.MULTILINE,
        )
        blocks = re.split(r"\n[ \t]*\n", normalized.strip())
        kept = []
        for block in blocks:
            lines = block.splitlines()
            index = next((i for i, line in enumerate(lines) if "-->" in line), None)
            if index is not None and not any(
                line.strip() for line in lines[index + 1 :]
            ):
                continue
            kept.append(block)
        return "\n\n".join(kept) + "\n"
    columns = []
    events = False
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith("["):
            events = line.strip().lower() == "[events]"
        elif events and line.startswith("Format:"):
            columns = [s.strip().lower() for s in line.split(":", 1)[1].split(",")]
        elif (
            events
            and line.startswith("Dialogue:")
            and {"start", "end"}.issubset(columns)
        ):
            values = line.split(":", 1)[1].lstrip().split(",", len(columns) - 1)
            if len(values) == len(columns):
                for key in ("start", "end"):
                    i = columns.index(key)
                    values[i] = normalize_time(values[i])
                line = "Dialogue: " + ",".join(values)
        lines.append(line)
    return "".join(lines)


def identify_file(slug: str, filename: str) -> tuple[int, str, int] | None:
    match = re.fullmatch(r"ep_(\d+)\.kk\.(srt|vtt|ass)", filename)
    rank = 0
    if not match:
        match = re.fullmatch(re.escape(slug) + r"-(\d+)(-?)ep\.(srt|vtt|ass)", filename)
        if not match:
            return None
        episode, dash, ext = match.groups()
        return int(episode), ext, 2 if dash else 1
    episode, ext = match.groups()
    return int(episode), ext, rank


def render_subtitle(cues: list[Cue], ext: str) -> str:
    """Derive a missing/broken format from usable cues, preserving attribution."""

    def time(ms: int) -> str:
        h, rest = divmod(ms, 3600000)
        m, rest = divmod(rest, 60000)
        s, fraction = divmod(rest, 1000)
        return (
            f"{h}:{m:02d}:{s:02d}.{fraction // 10:02d}"
            if ext == "ass"
            else f"{h:02d}:{m:02d}:{s:02d}{',' if ext == 'srt' else '.'}{fraction:03d}"
        )

    usable = [cue for cue in cues if cue.text.strip()]
    if ext == "ass":
        header = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,30,30,30,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        return header + "".join(
            "Dialogue: 0,"
            + time(c.start)
            + ","
            + time(c.end)
            + ",Default,,0,0,0,,"
            + c.text.replace("\n", r"\N")
            + "\n"
            for c in usable
        )
    header = "WEBVTT\n\n" if ext == "vtt" else ""
    return (
        header
        + "\n\n".join(
            f"{i}\n{time(c.start)} --> {time(c.end)}\n{c.text}"
            for i, c in enumerate(usable, 1)
        )
        + "\n"
    )


def timestamp(value: str, ext: str) -> int:
    pattern = (
        r"(\d+):([0-5]\d):([0-5]\d)\.(\d{2})"
        if ext == "ass"
        else r"(\d{2,}):([0-5]\d):([0-5]\d)"
        + (r",(\d{3})" if ext == "srt" else r"\.(\d{3})")
    )
    match = re.fullmatch(pattern, value)
    if not match:
        raise ValueError(f"Invalid {ext} timestamp: {value}")
    hours, minutes, seconds, fraction = map(int, match.groups())
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + fraction * (
        10 if ext == "ass" else 1
    )


def make_cue(start: str, end: str, text: str, ext: str) -> Cue:
    cue = Cue(timestamp(start, ext), timestamp(end, ext), text.strip())
    if cue.end <= cue.start:
        raise ValueError("Cue end must be later than start")
    if not cue.text and ext != "ass":
        raise ValueError("Empty cue text")
    return cue


def parse_subtitle(text: str, ext: str) -> list[Cue]:
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if "\ufffd" in text or "\x00" in text:
        raise ValueError("Replacement character or NUL in subtitle")
    cues = []
    if ext in ("srt", "vtt"):
        if ext == "vtt":
            if not re.match(r"^WEBVTT(?:[ \t][^\n]*)?(?:\n|$)", text):
                raise ValueError("Missing WEBVTT header")
            text = text.split("\n\n", 1)[1] if "\n\n" in text else ""
        for block in re.split(r"\n[ \t]*\n", text.strip()):
            lines = block.splitlines()
            if (
                ext == "vtt"
                and lines
                and re.match(r"^(NOTE(?:\s|$)|STYLE$|REGION$)", lines[0])
            ):
                continue
            index = 1 if lines and "-->" not in lines[0] else 0
            if ext == "srt" and (index != 1 or not lines[0].isdigit()):
                raise ValueError("Missing SRT cue index")
            if len(lines) <= index + 1:
                raise ValueError("Incomplete cue")
            timing = re.fullmatch(r"(\S+)\s+-->\s+(\S+)(?:[ \t]+[^\n]*)?", lines[index])
            if not timing:
                raise ValueError("Invalid cue timing line")
            cues.append(make_cue(*timing.groups(), "\n".join(lines[index + 1 :]), ext))
    elif ext == "ass":
        in_events = False
        columns = []
        for line in text.splitlines():
            if line.startswith("["):
                in_events = line.strip().lower() == "[events]"
            elif in_events and line.startswith("Format:"):
                columns = [
                    part.strip().lower() for part in line.split(":", 1)[1].split(",")
                ]
                if (
                    not {"start", "end", "text"}.issubset(columns)
                    or columns[-1] != "text"
                ):
                    raise ValueError("Invalid ASS event format")
            elif in_events and line.startswith("Dialogue:"):
                if not columns:
                    raise ValueError("Missing ASS event format")
                values = line.split(":", 1)[1].lstrip().split(",", len(columns) - 1)
                if len(values) != len(columns):
                    raise ValueError("Incomplete ASS dialogue")
                event = dict(zip(columns, values))
                dialogue = (
                    re.sub(r"\{[^}]*\}", "", event["text"])
                    .replace(r"\N", "\n")
                    .replace(r"\n", "\n")
                    .replace(r"\h", " ")
                )
                cues.append(
                    make_cue(
                        event["start"].strip(), event["end"].strip(), dialogue, ext
                    )
                )
    else:
        raise ValueError(f"Unsupported subtitle format: {ext}")
    if not cues:
        raise ValueError("No subtitle cues")
    return cues
