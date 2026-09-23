"""Anime title slug, abbreviation, and season resolver.

Produces clear, understandable slugs and filenames:
- Jujutsu Kaisen -> jjk (jjk-1ep.srt, jjk-2ep.srt)
- Jujutsu Kaisen 2nd Season -> jjk-s2 (jjk-s2-1ep.srt)
- Attack on Titan / Shingeki no Kyojin -> aot (aot-1ep.srt)
- Shingeki no Kyojin Season 2 -> aot-s2 (aot-s2-1ep.srt)
- Shingeki no Kyojin Season 3 -> aot-s3 (aot-s3-1ep.srt)
- Shingeki no Kyojin Season 3 Part 2 -> aot-s3-p2 (aot-s3-p2-1ep.srt)
- Shingeki no Kyojin: The Final Season -> aot-final (aot-final-1ep.srt)
- Death Note -> dn (dn-1ep.srt)
- Kimetsu no Yaiba -> kny (kny-1ep.srt)
- Kimetsu no Yaiba: Yuukaku-hen -> kny-s2 (kny-s2-1ep.srt)
- One Punch Man -> opm (opm-1ep.srt)
- One Punch Man 2 -> opm-s2 (opm-s2-1ep.srt)
- Boku no Hero Academia -> my-hero-academia (my-hero-academia-1ep.srt)
- Boku no Hero Academia 2 -> my-hero-academia-s2 (my-hero-academia-s2-1ep.srt)
- Hunter x Hunter -> hxh (hxh-1ep.srt)
- Tokyo Ghoul -> tokyo-ghoul (tokyo-ghoul-1ep.srt)
- Tokyo Ghoul √A -> tokyo-ghoul-s2 (tokyo-ghoul-s2-1ep.srt)
"""
import re
from typing import Any, Dict, List, Optional, Tuple, Union

# Curated base abbreviations
KNOWN_BASE_SLUGS = {
    # High-popularity short acronyms
    "jujutsu kaisen": "jjk",
    "shingeki no kyojin": "aot",
    "attack on titan": "aot",
    "death note": "dn",
    "kimetsu no yaiba": "kny",
    "demon slayer": "kny",
    "one punch man": "opm",
    "hunter x hunter": "hxh",
    "fullmetal alchemist: brotherhood": "fmab",
    "fullmetal alchemist": "fma",
    "sword art online": "sao",
    "neon genesis evangelion": "eva",
    "chainsaw man": "csm",
    "spy x family": "sxf",
    "no game no life": "ngnl",
    "tengen toppa gurren lagann": "ttgl",
    "fate/stay night": "fsn",
    "fate/zero": "fate-zero",
    "great teacher onizuka": "gto",
    "jojo's bizarre adventure": "jojo",
    "jojo no kimyou na bouken": "jojo",
    "jojo": "jojo",

    # Full understandable slugs
    "boku no hero academia": "my-hero-academia",
    "my hero academia": "my-hero-academia",
    "tokyo ghoul": "tokyo-ghoul",
    "vinland saga": "vinland-saga",
    "haikyuu!!": "haikyuu",
    "haikyuu": "haikyuu",
    "black clover": "black-clover",
    "code geass": "code-geass",
    "mob psycho 100": "mob-psycho-100",
    "steins;gate": "steins-gate",
    "re:zero": "rezero",
    "naruto": "naruto",
    "bleach": "bleach",
    "gintama": "gintama",
    "cowboy bebop": "cowboy-bebop",
    "cyberpunk: edgerunners": "edgerunners",
    "dr. stone": "dr-stone",
    "kaguya-sama wa kokurasetai": "kaguya",
    "made in abyss": "made-in-abyss",
    "mushoku tensei": "mushoku-tensei",
    "overlord": "overlord",
    "psycho-pass": "psycho-pass",
    "solo leveling": "solo-leveling",
    "violet evergarden": "violet-evergarden",
    "sousou no frieren": "frieren",
    "frieren": "frieren",
    "oshi no ko": "oshi-no-ko",
    "bocchi the rock!": "bocchi",
    "blue lock": "blue-lock",
    "dororo": "dororo",
    "tokyo revengers": "tokyo-revengers",
    "hell's paradise": "hells-paradise",
    "jigokuraku": "jigokuraku",
    "parasyte": "parasyte",
    "death parade": "death-parade",
    "noragami": "noragami",
    "assassination classroom": "ansatsu-kyoushitsu",
    "erased": "erased",
    "your lie in april": "shigatsu",
    "clannad": "clannad",
    "toradora": "toradora",
    "samurai champloo": "samurai-champloo",
    "k-on!": "k-on",
    "k-on": "k-on"
}

def _extract_season_suffix(title: str) -> Tuple[str, str]:
    """Extract season or part suffix from title, returning (cleaned_base_title, season_suffix)."""
    t = title.strip()

    # Final Season Part 2 / 3
    if re.search(r"the final season part\s*(\d+)", t, re.I):
        m = re.search(r"the final season part\s*(\d+)", t, re.I)
        cleaned = re.sub(r"the final season part\s*\d+", "", t, flags=re.I).strip(" :-")
        return cleaned, f"-final-p{m.group(1)}"

    # Final Season
    if re.search(r"(the final season|final season)", t, re.I):
        cleaned = re.sub(r"(the final season|final season)", "", t, flags=re.I).strip(" :-")
        return cleaned, "-final"

    # Season X Part Y
    m_sp = re.search(r"season\s*(\d+)\s*part\s*(\d+)", t, re.I)
    if m_sp:
        cleaned = re.sub(r"season\s*\d+\s*part\s*\d+", "", t, flags=re.I).strip(" :-")
        return cleaned, f"-s{m_sp.group(1)}-p{m_sp.group(2)}"

    # Season X or Xnd/Xth/Xrd Season
    m_s = re.search(r"(?:season\s*(\d+)|(\d+)(?:st|nd|rd|th)\s*season)", t, re.I)
    if m_s:
        s_num = m_s.group(1) or m_s.group(2)
        cleaned = re.sub(r"(?:season\s*\d+|\d+(?:st|nd|rd|th)\s*season)", "", t, flags=re.I).strip(" :-")
        return cleaned, f"-s{s_num}"

    # Roman numerals II, III, IV at end of title
    m_rom = re.search(r"\b(II|III|IV)\b\s*$", t)
    if m_rom:
        rom_map = {"II": "-s2", "III": "-s3", "IV": "-s4"}
        cleaned = re.sub(r"\b(II|III|IV)\b\s*$", "", t).strip(" :-")
        return cleaned, rom_map[m_rom.group(1)]

    # Standalone number at end of title like "Boku no Hero Academia 2" or "One Punch Man 2"
    m_num = re.search(r"\s+(\d+)\s*$", t)
    if m_num and int(m_num.group(1)) in range(2, 10):
        cleaned = re.sub(r"\s+\d+\s*$", "", t).strip(" :-")
        return cleaned, f"-s{m_num.group(1)}"

    # Specific arc seasons
    if re.search(r"mugen\s*ressha", t, re.I):
        cleaned = re.sub(r":?\s*mugen\s*ressha-?hen", "", t, flags=re.I).strip(" :-")
        return cleaned, "-mugen-train"
    if re.search(r"yuukaku", t, re.I):
        cleaned = re.sub(r":?\s*yuukaku-?hen", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s2"
    if re.search(r"katanakaji", t, re.I):
        cleaned = re.sub(r":?\s*katanakaji\s*no\s*sato-?hen", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s3"
    if re.search(r"hashira\s*geiko", t, re.I):
        cleaned = re.sub(r":?\s*hashira\s*geiko-?hen", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s4"
    if re.search(r"(?:√A|root\s*a)\b", t, re.I):
        cleaned = re.sub(r":?\s*(?:√A|root\s*a)\b", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s2"
    if re.search(r":re\b", t, re.I):
        cleaned = re.sub(r":re\b", "", t, flags=re.I).strip(" :-")
        return cleaned, "-re"

    # JoJo Bizarre Adventure seasons & parts
    if re.search(r"stardust\s*crusaders.*egypt", t, re.I):
        cleaned = re.sub(r":?\s*stardust\s*crusaders.*egypt-?hen.*", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s3"
    if re.search(r"stardust\s*crusaders", t, re.I):
        cleaned = re.sub(r":?\s*stardust\s*crusaders.*", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s2"
    if re.search(r"diamond\s*wa\s*kudakenai|diamond\s*is\s*unbreakable", t, re.I):
        cleaned = re.sub(r":?\s*(diamond\s*wa\s*kudakenai|diamond\s*is\s*unbreakable).*", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s4"
    if re.search(r"ougon\s*no\s*kaze|golden\s*wind|vento\s*aureo", t, re.I):
        cleaned = re.sub(r":?\s*(ougon\s*no\s*kaze|golden\s*wind|vento\s*aureo).*", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s5"
    if re.search(r"stone\s*ocean", t, re.I):
        cleaned = re.sub(r":?\s*stone\s*ocean.*", "", t, flags=re.I).strip(" :-")
        return cleaned, "-s6"

    return t, ""

def get_anime_slug(anime_data_or_title: Union[Dict[str, Any], str]) -> str:
    """Generate clean slug with proper season tag (e.g. jjk, aot, my-hero-academia-s2)."""
    raw_titles = []
    if isinstance(anime_data_or_title, dict):
        t_dict = anime_data_or_title.get("title", {})
        if isinstance(t_dict, dict):
            if t_dict.get("english"):
                raw_titles.append(t_dict["english"])
            if t_dict.get("romaji"):
                raw_titles.append(t_dict["romaji"])
        elif isinstance(t_dict, str):
            raw_titles.append(t_dict)
    elif isinstance(anime_data_or_title, str):
        raw_titles.append(anime_data_or_title)

    if not raw_titles:
        return "anime"

    # Find season suffix from any title candidate
    season_suffix = ""
    cleaned_candidates = []
    for raw in raw_titles:
        c_title, s_suffix = _extract_season_suffix(raw)
        cleaned_candidates.append(c_title)
        if s_suffix and not season_suffix:
            season_suffix = s_suffix

    # Resolve base slug
    base_slug = None
    for cand in cleaned_candidates + raw_titles:
        norm = re.sub(r"[^\w\s]", "", cand.lower()).strip()
        # Direct match in known base slugs
        for known, slug in KNOWN_BASE_SLUGS.items():
            known_norm = re.sub(r"[^\w\s]", "", known.lower()).strip()
            if known_norm == norm or norm == known_norm or norm.startswith(known_norm):
                base_slug = slug
                break
        if base_slug:
            break

    if not base_slug:
        # Fallback kebab slug
        words = re.findall(r"[a-zA-Z0-9]+", cleaned_candidates[0].lower())
        stopwords = {"no", "wa", "to", "ni", "de", "ga", "the", "a", "an", "of", "and", "in", "on"}
        sig_words = [w for w in words if w not in stopwords]
        base_slug = "-".join(sig_words[:3]) if sig_words else "anime"

    return f"{base_slug}{season_suffix}"

def get_subtitle_filename(slug: str, ep: int, ext: str = "srt") -> str:
    """Returns primary user filename (e.g. my-hero-academia-1ep.srt)."""
    return f"{slug}-{ep}ep.{ext}"

def get_subtitle_filenames(slug: str, ep: int, ext: str = "srt") -> List[str]:
    """Returns primary user filename (e.g. my-hero-academia-1ep.srt) and aliases."""
    return [
        f"{slug}-{ep}ep.{ext}",
        f"{slug}-{ep}-ep.{ext}"
    ]

if __name__ == "__main__":
    tests = [
        {"title": {"romaji": "Jujutsu Kaisen", "english": "JUJUTSU KAISEN"}},
        {"title": {"romaji": "Jujutsu Kaisen 2nd Season", "english": "JUJUTSU KAISEN Season 2"}},
        {"title": {"romaji": "Shingeki no Kyojin", "english": "Attack on Titan"}},
        {"title": {"romaji": "Shingeki no Kyojin Season 2", "english": "Attack on Titan Season 2"}},
        {"title": {"romaji": "Shingeki no Kyojin Season 3", "english": "Attack on Titan Season 3"}},
        {"title": {"romaji": "Shingeki no Kyojin Season 3 Part 2", "english": "Attack on Titan Season 3 Part 2"}},
        {"title": {"romaji": "Shingeki no Kyojin: The Final Season", "english": "Attack on Titan Final Season"}},
        {"title": {"romaji": "Shingeki no Kyojin: The Final Season Part 2", "english": "Attack on Titan Final Season Part 2"}},
        {"title": {"romaji": "DEATH NOTE", "english": "Death Note"}},
        {"title": {"romaji": "Kimetsu no Yaiba", "english": "Demon Slayer: Kimetsu no Yaiba"}},
        {"title": {"romaji": "Kimetsu no Yaiba: Yuukaku-hen", "english": "Demon Slayer: Kimetsu no Yaiba Entertainment District Arc"}},
        {"title": {"romaji": "One Punch Man", "english": "One-Punch Man"}},
        {"title": {"romaji": "One Punch Man 2", "english": "One-Punch Man Season 2"}},
        {"title": {"romaji": "Boku no Hero Academia", "english": "My Hero Academia"}},
        {"title": {"romaji": "Boku no Hero Academia 2", "english": "My Hero Academia Season 2"}},
        {"title": {"romaji": "Boku no Hero Academia 3", "english": "My Hero Academia Season 3"}},
        {"title": {"romaji": "Hunter x Hunter (2011)", "english": "Hunter x Hunter"}},
        {"title": {"romaji": "Tokyo Ghoul", "english": "Tokyo Ghoul"}},
        {"title": {"romaji": "Tokyo Ghoul √A", "english": "Tokyo Ghoul Root A"}},
    ]
    for t in tests:
        s = get_anime_slug(t)
        fnames = get_subtitle_filenames(s, 1, "srt")
        eng = t["title"].get("english") or t["title"]["romaji"]
        print(f"{eng} -> '{s}' -> Primary: {fnames[0]}")

    assert get_anime_slug({"title": {"romaji": "Boku no Hero Academia"}}) == "my-hero-academia"
    assert get_anime_slug({"title": {"romaji": "Boku no Hero Academia 2"}}) == "my-hero-academia-s2"
    assert get_anime_slug({"title": {"romaji": "Shingeki no Kyojin Season 2"}}) == "aot-s2"
    assert get_anime_slug({"title": {"romaji": "Jujutsu Kaisen 2nd Season"}}) == "jjk-s2"
    assert get_anime_slug({"title": {"romaji": "One Punch Man 2"}}) == "opm-s2"
    print("\ncore/slugs.py season verification PASSED.")
