"""Anime title slug and abbreviation resolver.

Produces clean, recognizable short slugs like:
- Jujutsu Kaisen -> jjk (jjk-1-ep.srt, jjk-2-ep.srt)
- Attack on Titan / Shingeki no Kyojin -> aot (aot-1-ep.srt)
- Death Note -> dn (dn-1-ep.srt)
- Kimetsu no Yaiba / Demon Slayer -> kny (kny-1-ep.srt)
- One Punch Man -> opm (opm-1-ep.srt)
- Boku no Hero Academia -> mha (mha-1-ep.srt)
"""
import re
from typing import Any, Dict, Optional, Union

# Curated high-popularity abbreviations
KNOWN_SLUGS = {
    # Shonen / Action hits
    "jujutsu kaisen": "jjk",
    "shingeki no kyojin": "aot",
    "attack on titan": "aot",
    "death note": "dn",
    "kimetsu no yaiba": "kny",
    "demon slayer": "kny",
    "demon slayer: kimetsu no yaiba": "kny",
    "one punch man": "opm",
    "boku no hero academia": "mha",
    "my hero academia": "mha",
    "hunter x hunter": "hxh",
    "hunter x hunter (2011)": "hxh",
    "fullmetal alchemist: brotherhood": "fmab",
    "fullmetal alchemist": "fma",
    "sword art online": "sao",
    "tokyo ghoul": "tokyo-ghoul",
    "chainsaw man": "csm",
    "spy x family": "sxf",
    "vinland saga": "vinland-saga",
    "haikyuu!!": "haikyuu",
    "black clover": "black-clover",
    "code geass": "code-geass",
    "code geass: hangyaku no lelouch": "code-geass",
    "neon genesis evangelion": "eva",
    "mob psycho 100": "mob-psycho-100",
    "steins;gate": "steins-gate",
    "re:zero kara hajimeru isekai seikatsu": "rezero",
    "re:zero": "rezero",
    "no game no life": "ngnl",
    "tengen toppa gurren lagann": "ttgl",
    "naruto": "naruto",
    "naruto: shippuuden": "naruto-shippuuden",
    "bleach": "bleach",
    "bleach: sennen kessen-hen": "bleach-tybw",
    "gintama": "gintama",
    "cowboy bebop": "cowboy-bebop",
    "cyberpunk: edgerunners": "edgerunners",
    "dr. stone": "dr-stone",
    "fate/stay night": "fsn",
    "fate/zero": "fate-zero",
    "kaguya-sama wa kokurasetai": "kaguya",
    "made in abyss": "made-in-abyss",
    "mushoku tensei": "mushoku-tensei",
    "overlord": "overlord",
    "psycho-pass": "psycho-pass",
    "solo leveling": "solo-leveling",
    "violet evergarden": "violet-evergarden",
    "sousou no frieren": "frieren",
    "frieren: beyond journey's end": "frieren",
    "frieren": "frieren",
    "oshi no ko": "oshi-no-ko",
    "bocchi the rock!": "bocchi",
    "blue lock": "blue-lock",
    "dororo": "dororo",
    "tokyo revengers": "tokyo-revengers",
    "hell's paradise": "hells-paradise",
    "jigokuraku": "jigokuraku",
    "parasyte": "parasyte",
    "kiseijuu: sei no kakuritsu": "parasyte",
    "death parade": "death-parade",
    "noragami": "noragami",
    "assassination classroom": "ansatsu-kyoushitsu",
    "ansatsu kyoushitsu": "ansatsu-kyoushitsu",
    "erased": "erased",
    "boku dake ga inai machi": "erased",
    "your lie in april": "shigatsu",
    "shigatsu wa kimi no uso": "shigatsu",
    "clannad": "clannad",
    "toradora!": "toradora",
    "toradora": "toradora",
    "great teacher onizuka": "gto",
    "gto": "gto",
    "samurai champloo": "samurai-champloo"
}

def get_anime_slug(anime_data_or_title: Union[Dict[str, Any], str]) -> str:
    """Generate a clean, recognizable short slug like 'jjk', 'aot', 'dn'."""
    titles = []
    if isinstance(anime_data_or_title, dict):
        t_dict = anime_data_or_title.get("title", {})
        if isinstance(t_dict, dict):
            if t_dict.get("romaji"):
                titles.append(t_dict["romaji"])
            if t_dict.get("english"):
                titles.append(t_dict["english"])
        elif isinstance(t_dict, str):
            titles.append(t_dict)
    elif isinstance(anime_data_or_title, str):
        titles.append(anime_data_or_title)

    for raw in titles:
        norm = re.sub(r"[^\w\s]", "", raw.lower()).strip()
        # Direct match in known slugs
        if norm in KNOWN_SLUGS:
            return KNOWN_SLUGS[norm]
        for known, slug in KNOWN_SLUGS.items():
            known_norm = re.sub(r"[^\w\s]", "", known.lower()).strip()
            if known_norm == norm or norm.startswith(known_norm):
                return slug

    # Algorithmic fallback
    primary = titles[0] if titles else "anime"
    words = re.findall(r"[a-zA-Z0-9]+", primary.lower())
    
    # Filter stopwords for initials
    stopwords = {"no", "wa", "to", "ni", "de", "ga", "the", "a", "an", "of", "and", "in", "on"}
    sig_words = [w for w in words if w not in stopwords]

    # If 3 or more significant words, form clean acronym e.g. Boku no Hero Academia -> bnha
    if len(sig_words) >= 3 and len(sig_words) <= 6:
        return "".join(w[0] for w in sig_words)

    # Otherwise return kebab slug up to 3 words
    clean_kebab = "-".join(words[:3])
    return clean_kebab if clean_kebab else "anime"

def get_subtitle_filename(slug: str, ep: int, ext: str = "srt") -> str:
    """Format subtitle filename according to user specification: e.g. jjk-1-ep.srt"""
    return f"{slug}-{ep}-ep.{ext}"

if __name__ == "__main__":
    test_cases = [
        {"title": {"romaji": "Jujutsu Kaisen", "english": "Jujutsu Kaisen"}},
        {"title": {"romaji": "Shingeki no Kyojin", "english": "Attack on Titan"}},
        {"title": {"romaji": "DEATH NOTE", "english": "Death Note"}},
        {"title": {"romaji": "Kimetsu no Yaiba", "english": "Demon Slayer: Kimetsu no Yaiba"}},
        {"title": {"romaji": "One Punch Man", "english": "One-Punch Man"}},
        {"title": {"romaji": "Boku no Hero Academia", "english": "My Hero Academia"}},
        {"title": {"romaji": "Hunter x Hunter (2011)", "english": "Hunter x Hunter"}},
        {"title": {"romaji": "Fullmetal Alchemist: Brotherhood"}},
        {"title": {"romaji": "Toradora!"}}
    ]
    for c in test_cases:
        slug = get_anime_slug(c)
        fname = get_subtitle_filename(slug, 1, "srt")
        print(f"{c['title']['romaji']} -> slug: '{slug}' -> file: '{fname}'")
    assert get_subtitle_filename(get_anime_slug({"title": {"romaji": "Jujutsu Kaisen"}}), 1) == "jjk-1-ep.srt"
    assert get_subtitle_filename(get_anime_slug({"title": {"romaji": "Jujutsu Kaisen"}}), 2) == "jjk-2-ep.srt"
    print("core/slugs.py self-check PASSED.")
