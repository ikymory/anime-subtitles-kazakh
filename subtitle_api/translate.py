"""Plan or execute official DeepL translation of explicitly identified subtitle tracks.

The input JSON contains a ``tracks`` list with anime_id (anilist:N or
myanimelist:N), slug, episode, path relative to --source, source_lang, and optional
context/source_url. Planning is offline. Execution needs DEEPL_AUTH_KEY and an
explicit character budget; it produces machine-translated SRT/VTT plus provenance
outside the source tree. A processed track never establishes complete-anime or
human-reviewed coverage.
"""

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable

from .subtitles import Cue, parse_subtitle, render_subtitle

TARGET = "KK"
MODEL = "prefer_quality_optimized"
MAX_BODY_BYTES = 128 * 1024
MAX_TEXTS = 50
ENDPOINTS = frozenset({"https://api.deepl.com", "https://api-free.deepl.com"})


class TranslationError(ValueError):
    """Safe, transcript-free operational failure suitable for CLI output."""


def _json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cache_key(
    text: str,
    source_lang: str,
    target_lang: str,
    model: str,
    context: str,
    anime_id: str,
) -> str:
    return _hash(
        _json(
            [
                "deepl-v1",
                source_lang,
                target_lang,
                model,
                _hash(context.encode("utf-8")),
                anime_id,
                text,
            ]
        )
    )


def request_payload(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    context: str,
    model: str = MODEL,
) -> bytes:
    return _json(
        {
            "text": texts,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model_type": model,
            "context": context,
            "preserve_formatting": True,
            "split_sentences": "nonewlines",
        }
    )


def make_batches(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    context: str,
    model: str = MODEL,
) -> list[list[str]]:
    batches = []
    batch = []
    for text in texts:
        candidate = batch + [text]
        if (
            len(candidate) > MAX_TEXTS
            or len(request_payload(candidate, source_lang, target_lang, context, model))
            > MAX_BODY_BYTES
        ):
            if not batch:
                raise TranslationError(
                    "A single cue and context exceed the DeepL request size limit"
                )
            batches.append(batch)
            batch = [text]
            if (
                len(request_payload(batch, source_lang, target_lang, context, model))
                > MAX_BODY_BYTES
            ):
                raise TranslationError(
                    "A single cue and context exceed the DeepL request size limit"
                )
        else:
            batch = candidate
    if batch:
        batches.append(batch)
    return batches


def _validate_translation(source: str, item: object, source_lang: str) -> dict:
    if not isinstance(item, dict):
        raise TranslationError("DeepL returned a malformed translation")
    text = item.get("text")
    detected = item.get("detected_source_language")
    if (
        not isinstance(text, str)
        or not text.strip()
        or "\x00" in text
        or "\ufffd" in text
        or re.search(r"\n[ \t]*\n", text)
        or not isinstance(detected, str)
        or not re.fullmatch(r"[A-Z]{2,3}(?:-[A-Z]{2})?", detected)
        or detected.split("-")[0] != source_lang.split("-")[0]
    ):
        raise TranslationError(
            "DeepL returned empty, malformed, or mismatched-language text"
        )
    # Judge visible dialogue, not SRT/VTT styling tags or HTML entity names.
    # These are rejection heuristics, not evidence of Kazakh fluency/accuracy.
    visible_source = html.unescape(re.sub(r"<[^>]*>", "", source))
    visible_text = html.unescape(re.sub(r"<[^>]*>", "", text))
    if any(character.isalpha() for character in visible_source):
        if not any(character.isalpha() for character in visible_text):
            raise TranslationError(
                "DeepL replaced substantive dialogue with punctuation or a placeholder"
            )
        if any(
            character.isalpha()
            and any(
                script in unicodedata.name(character, "")
                for script in ("CJK", "HIRAGANA", "KATAKANA", "HANGUL", "BOPOMOFO")
            )
            for character in visible_text
        ):
            raise TranslationError(
                "DeepL output retains CJK script; human review is required before Kazakh publication"
            )
        # Unchanged names may be legitimate, but require review instead of being
        # silently counted as translated dialogue.
        original = re.sub(r"\s+", " ", visible_source).strip().casefold()
        translated = re.sub(r"\s+", " ", visible_text).strip().casefold()
        if original == translated:
            raise TranslationError(
                "DeepL returned copied source text; human review is required"
            )
    model_used = item.get("model_type_used")
    if model_used is not None and model_used not in (
        "quality_optimized",
        "latency_optimized",
    ):
        raise TranslationError("DeepL returned an unknown model identifier")
    return {
        "text": text,
        "detected_source_language": detected,
        "model_type_used": model_used,
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        # Never forward the Authorization header to a redirect destination.
        raise TranslationError("DeepL redirect refused")


class DeepLClient:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        opener=None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        key = os.environ.get("DEEPL_AUTH_KEY", "").strip()
        if not key or any(char.isspace() for char in key):
            raise TranslationError(
                "Set DEEPL_AUTH_KEY in the environment before execution"
            )
        self.endpoint = endpoint or (
            "https://api-free.deepl.com"
            if key.endswith(":fx")
            else "https://api.deepl.com"
        )
        if self.endpoint not in ENDPOINTS:
            raise TranslationError("Only official DeepL API endpoints are permitted")
        self._key = key
        self._opener = opener or urllib.request.build_opener(_NoRedirect())
        self._sleep = sleep
        self._character_budget = None
        self._available_characters = None
        self.submitted_characters = 0

    def set_character_budget(self, maximum: int) -> None:
        if type(maximum) is not int or maximum < 1:
            raise TranslationError("A positive request character budget is required")
        self._character_budget = maximum
        self.submitted_characters = 0

    def _request(self, route: str, body: bytes | None = None, *, characters: int = 0):
        for attempt in range(4):
            if body is not None:
                allowed = self._character_budget
                if allowed is None:
                    raise TranslationError(
                        "Configure an explicit character budget before translation"
                    )
                if self._available_characters is not None:
                    allowed = min(allowed, self._available_characters)
                # Reserve every attempt conservatively. A 5xx response does not
                # prove that the provider did not translate and bill the text.
                if self.submitted_characters + characters > allowed:
                    raise TranslationError(
                        "Character budget or verified quota cannot cover another paid request attempt"
                    )
                self.submitted_characters += characters
            request = urllib.request.Request(
                self.endpoint + route,
                data=body,
                headers={
                    "Authorization": "DeepL-Auth-Key " + self._key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST" if body is not None else "GET",
            )
            try:
                with self._opener.open(request, timeout=45) as response:
                    raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise TranslationError("DeepL response exceeded the permitted size")
                return json.loads(raw)
            except urllib.error.HTTPError as error:
                status = error.code
                retry_after = (
                    error.headers.get("Retry-After", "") if error.headers else ""
                )
                error.close()
                if status in (429, 500, 502, 503, 504, 529) and attempt < 3:
                    delay = min(2**attempt, 30)
                    try:
                        delay = min(max(float(retry_after), 0), 30)
                    except (ValueError, TypeError):
                        try:
                            delay = min(
                                max(
                                    (
                                        parsedate_to_datetime(retry_after)
                                        - datetime.now(timezone.utc)
                                    ).total_seconds(),
                                    0,
                                ),
                                30,
                            )
                        except (ValueError, TypeError, OverflowError):
                            pass
                    self._sleep(delay)
                    continue
                if status in (401, 403):
                    raise TranslationError("DeepL authentication failed") from None
                if status == 456:
                    raise TranslationError(
                        "DeepL quota exceeded; no fallback translation was generated"
                    ) from None
                raise TranslationError(
                    f"DeepL request failed (HTTP {status})"
                ) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                # Ambiguous network failures on paid POSTs are not automatically
                # retried: the provider may already have billed the request.
                raise TranslationError(
                    "DeepL network request failed; cached completed batches are retained"
                ) from None
            except (json.JSONDecodeError, UnicodeError):
                raise TranslationError("DeepL returned invalid JSON") from None
        raise TranslationError("DeepL request retry limit reached")

    def preflight(self, characters: int) -> None:
        languages = self._request("/v2/languages?type=target")
        if not isinstance(languages, list) or not any(
            isinstance(item, dict) and item.get("language") == TARGET
            for item in languages
        ):
            raise TranslationError(
                "DeepL does not report Kazakh (KK) target support for this account"
            )
        usage = self._request("/v2/usage")
        if not isinstance(usage, dict):
            raise TranslationError("DeepL returned invalid usage data")
        limits = [(usage.get("character_count"), usage.get("character_limit"))]
        if "api_key_character_count" in usage or "api_key_character_limit" in usage:
            limits.append(
                (
                    usage.get("api_key_character_count"),
                    usage.get("api_key_character_limit"),
                )
            )
        available = []
        for count, limit in limits:
            if (
                type(count) is not int
                or type(limit) is not int
                or count < 0
                or limit < 0
                or count > limit
                or characters > limit - count
            ):
                raise TranslationError(
                    "DeepL available quota is insufficient or could not be verified"
                )
            available.append(limit - count)
        self._available_characters = min(available)

    def translate(self, texts: list[str], source_lang: str, context: str) -> list[dict]:
        body = request_payload(texts, source_lang, TARGET, context)
        if not texts or len(texts) > MAX_TEXTS or len(body) > MAX_BODY_BYTES:
            raise TranslationError("Translation batch violates DeepL request limits")
        result = self._request("/v2/translate", body, characters=sum(map(len, texts)))
        items = result.get("translations") if isinstance(result, dict) else None
        if not isinstance(items, list) or len(items) != len(texts):
            raise TranslationError(
                "DeepL response count does not match the requested cue count"
            )
        return [
            _validate_translation(text, item, source_lang)
            for text, item in zip(texts, items)
        ]


@dataclass(frozen=True)
class Track:
    anime_id: str
    slug: str
    episode: int
    path: Path
    source_lang: str
    context: str
    source_url: str | None
    source_sha256: str
    cues: tuple[Cue, ...]

    def key(self, text: str) -> str:
        return cache_key(
            text, self.source_lang, TARGET, MODEL, self.context, self.anime_id
        )


@dataclass(frozen=True)
class Plan:
    source_root: Path
    tracks: tuple[Track, ...]
    cached: dict[str, dict]

    def summary(self) -> dict:
        unique = {}
        for track in self.tracks:
            unique.update({track.key(c.text): c.text for c in track.cues})
        return {
            "distinct_anime": len({track.anime_id for track in self.tracks}),
            "tracks": len(self.tracks),
            "cues": sum(len(t.cues) for t in self.tracks),
            "unique_texts": len(unique),
            "source_characters": sum(len(c.text) for t in self.tracks for c in t.cues),
            "uncached_characters": sum(
                len(text) for key, text in unique.items() if key not in self.cached
            ),
            "cached_unique_texts": sum(key in self.cached for key in unique),
            "provider": "DeepL",
            "target_lang": TARGET,
            "model_type": MODEL,
            "human_review": False,
            "complete_anime": 0,
        }


def _read_cache(directory: Path, track: Track, text: str) -> dict | None:
    path = directory / (track.key(text) + ".json")
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text("utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("cache_key") != track.key(text)
            or value.get("source_text_sha256") != _hash(text.encode("utf-8"))
        ):
            raise TranslationError("Translation cache entry does not match its source")
        return _validate_translation(text, value.get("translation"), track.source_lang)
    except (OSError, ValueError, TypeError):
        raise TranslationError(
            "Translation cache entry is invalid; inspect it before retrying"
        ) from None


def make_plan(
    manifest: Path, source_root: Path, cache_dir: Path, *, max_anime: int | None = None
) -> Plan:
    source_root = source_root.resolve()
    try:
        document = json.loads(manifest.read_text("utf-8-sig"))
    except (OSError, ValueError):
        raise TranslationError("Cannot read a valid translation manifest") from None
    records = document.get("tracks") if isinstance(document, dict) else None
    if not isinstance(records, list) or not records:
        raise TranslationError("Manifest must provide a nonempty tracks array")
    if max_anime is not None and max_anime < 1:
        raise TranslationError("max-anime must be positive")
    tracks = []
    slots = set()
    id_to_slug = {}
    slug_to_id = {}
    fingerprints = {}
    cached = {}
    namespace = None
    for record in records:
        if not isinstance(record, dict):
            raise TranslationError("Manifest contains an invalid track record")
        anime_id, slug = record.get("anime_id"), record.get("slug")
        episode, relative = record.get("episode"), record.get("path")
        language, context = record.get("source_lang"), record.get("context", "")
        if (
            not isinstance(anime_id, str)
            or not re.fullmatch(r"(?:anilist|myanimelist):[1-9]\d*", anime_id)
            or not isinstance(slug, str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
            or type(episode) is not int
            or not 0 <= episode <= 100000
            or not isinstance(relative, str)
            or not relative
            or not isinstance(language, str)
            or not re.fullmatch(r"[A-Z]{2,3}(?:-[A-Z]{2})?", language)
            or language.split("-")[0] == TARGET
            or not isinstance(context, str)
        ):
            raise TranslationError(
                "Manifest track identity, path, episode, language, or context is invalid"
            )
        if (
            anime_id not in id_to_slug
            and max_anime is not None
            and len(id_to_slug) >= max_anime
        ):
            continue
        current_namespace = anime_id.split(":", 1)[0]
        if namespace is not None and namespace != current_namespace:
            raise TranslationError(
                "Use one external identity namespace per manifest to prevent cross-catalog aliases"
            )
        namespace = current_namespace
        if (
            id_to_slug.get(anime_id, slug) != slug
            or slug_to_id.get(slug, anime_id) != anime_id
        ):
            raise TranslationError(
                "Anime identity and slug must have a one-to-one mapping"
            )
        slot = (anime_id, episode)
        if slot in slots:
            raise TranslationError("Duplicate anime episode in translation manifest")
        slots.add(slot)
        id_to_slug[anime_id], slug_to_id[slug] = slug, anime_id
        path = (source_root / relative).resolve()
        if not path.is_relative_to(source_root) or not path.is_file():
            raise TranslationError(
                "Manifest source path must be a file within the source root"
            )
        ext = path.suffix.lower().lstrip(".")
        if ext not in ("srt", "vtt", "ass"):
            raise TranslationError("Only SRT, VTT, and ASS source tracks are supported")
        try:
            payload = path.read_bytes()
            cues = parse_subtitle(payload.decode("utf-8-sig"), ext)
        except (OSError, ValueError, UnicodeError):
            raise TranslationError(
                "A source track cannot be parsed safely; repair the source before translation"
            ) from None
        if any(not cue.text.strip() for cue in cues):
            raise TranslationError("Source track contains empty dialogue cues")
        fingerprint = _hash(
            _json([re.sub(r"\s+", " ", c.text).strip().casefold() for c in cues])
        )
        if fingerprint in fingerprints:
            raise TranslationError(
                "Duplicate source dialogue detected across manifest tracks"
            )
        fingerprints[fingerprint] = slot
        source_url = record.get("source_url")
        if source_url is not None and (
            not isinstance(source_url, str)
            or not source_url.startswith("https://")
            or "@" in source_url
            or "?" in source_url
            or "#" in source_url
        ):
            raise TranslationError(
                "Source attribution URL must be HTTPS without credentials, query, or fragment"
            )
        # Identity is included in context so identical text from unrelated titles
        # is never reused just because the input context happened to be empty.
        track = Track(
            anime_id,
            slug,
            episode,
            path,
            language,
            f"Anime: {slug}.\n{context}",
            source_url,
            _hash(payload),
            tuple(cues),
        )
        make_batches(
            list(dict.fromkeys(c.text for c in cues)), language, TARGET, track.context
        )
        tracks.append(track)
        for text in dict.fromkeys(c.text for c in cues):
            item = _read_cache(cache_dir, track, text)
            if item is not None:
                cached[track.key(text)] = item
    return Plan(source_root, tuple(tracks), cached)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".deepl-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _paths(output: Path, track: Track) -> dict[str, Path]:
    stem = f"ep_{track.episode:02d}.kk"
    paths = {
        ext: output / track.slug / f"{stem}.{ext}"
        for ext in ("srt", "vtt", "provenance.json")
    }
    if any(not path.resolve().is_relative_to(output) for path in paths.values()):
        raise TranslationError(
            "Translation output path escapes its destination directory"
        )
    return paths


def _publish_exclusive(path: Path, payload: bytes) -> None:
    """Publish complete bytes atomically, refusing an existing destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".deepl-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Same-filesystem hard-link creation is atomic and fails when the name
        # exists, unlike replace()/rename() on platforms that overwrite names.
        # Unsupported filesystems fail safely instead of weakening that promise.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _verified_existing_output(track: Track, paths: dict[str, Path]) -> bool:
    present = [path.exists() for path in paths.values()]
    if not any(present):
        return False
    if not all(present):
        raise TranslationError(
            "Existing translation output is partial; overwrite is forbidden"
        )
    try:
        provenance = json.loads(paths["provenance.json"].read_text("utf-8"))
        expected = {
            "schema_version": "1.0",
            "provider": "DeepL",
            "model_type": MODEL,
            "source_lang": track.source_lang,
            "target_lang": TARGET,
            "anime_id": track.anime_id,
            "slug": track.slug,
            "episode": track.episode,
            "source_sha256": track.source_sha256,
            "context_sha256": _hash(track.context.encode("utf-8")),
            "source_filename": track.path.name,
            "source_url": track.source_url,
            "cues": len(track.cues),
            "translation_accuracy": "not_verified",
        }
        if (
            not isinstance(provenance, dict)
            or any(provenance.get(key) != value for key, value in expected.items())
            or provenance.get("timing_preserved") is not True
            or provenance.get("human_review") is not False
            or provenance.get("complete_anime") is not False
        ):
            raise ValueError("mismatched provenance")
        hashes = provenance.get("output_sha256")
        if not isinstance(hashes, dict) or set(hashes) != {"srt", "vtt"}:
            raise ValueError("missing output hashes")
        detected = provenance.get("detected_source_languages")
        if (
            not isinstance(detected, list)
            or not detected
            or any(
                not isinstance(language, str)
                or not re.fullmatch(r"[A-Z]{2,3}(?:-[A-Z]{2})?", language)
                or language.split("-")[0] != track.source_lang.split("-")[0]
                for language in detected
            )
        ):
            raise ValueError("mismatched source language")
        models = provenance.get("model_type_used")
        if not isinstance(models, list) or any(
            model not in ("quality_optimized", "latency_optimized") for model in models
        ):
            raise ValueError("mismatched model")
        outputs = {}
        for ext in ("srt", "vtt"):
            payload = paths[ext].read_bytes()
            if _hash(payload) != hashes[ext]:
                raise ValueError("mismatched output hash")
            cues = parse_subtitle(payload.decode("utf-8"), ext)
            if len(cues) != len(track.cues) or any(
                (translated.start, translated.end) != (source.start, source.end)
                for translated, source in zip(cues, track.cues)
            ):
                raise ValueError("mismatched cue mapping")
            outputs[ext] = cues
        if outputs["srt"] != outputs["vtt"]:
            raise ValueError("mismatched output dialogue")
        for source, translated in zip(track.cues, outputs["srt"]):
            _validate_translation(
                source.text,
                {"text": translated.text, "detected_source_language": detected[0]},
                track.source_lang,
            )
        return True
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        raise TranslationError(
            "Existing translation output is mismatched or tampered; overwrite is forbidden"
        ) from None


def execute_plan(
    plan: Plan,
    output: Path,
    cache_dir: Path,
    *,
    max_characters: int,
    client: DeepLClient | None = None,
) -> dict:
    output = output.resolve()
    cache_dir = cache_dir.resolve()
    if output.is_relative_to(plan.source_root) or plan.source_root.is_relative_to(
        output
    ):
        raise TranslationError(
            "Translation output must be separate from the source root"
        )
    if type(max_characters) is not int or max_characters < 1:
        raise TranslationError("Execution requires a positive max-characters budget")
    pending = []
    for track in plan.tracks:
        if _hash(track.path.read_bytes()) != track.source_sha256:
            raise TranslationError(
                "A source track changed after planning; replan before execution"
            )
        if not _verified_existing_output(track, _paths(output, track)):
            pending.append(track)
    # Validate every existing triple before any network request, including when
    # an earlier manifest track still needs paid translation. Completed output
    # does not need cache entries or additional character budget to be retained.
    required = Plan(plan.source_root, tuple(pending), plan.cached).summary()[
        "uncached_characters"
    ]
    if required > max_characters:
        raise TranslationError(
            "Planned uncached characters exceed the explicit execution budget"
        )
    client = client or DeepLClient()
    client.set_character_budget(max_characters)
    # This check is mandatory even for a fully cached run: cache is not evidence
    # that the current account still supports the requested target language.
    client.preflight(required)
    values = dict(plan.cached)
    billed = 0
    processed = 0
    for track in pending:
        texts = list(
            dict.fromkeys(c.text for c in track.cues if track.key(c.text) not in values)
        )
        for batch in make_batches(texts, track.source_lang, TARGET, track.context):
            characters = sum(map(len, batch))
            if billed + characters > max_characters:
                raise TranslationError("Execution character budget exhausted")
            translations = client.translate(batch, track.source_lang, track.context)
            # A completed batch is persisted before making another paid request.
            for text, item in zip(batch, translations):
                key = track.key(text)
                value = {
                    "cache_key": key,
                    "provider": "DeepL",
                    "source_text_sha256": _hash(text.encode("utf-8")),
                    "translation": item,
                }
                _atomic_write(cache_dir / (key + ".json"), _json(value))
                values[key] = item
            billed += characters
        translated = [
            Cue(c.start, c.end, values[track.key(c.text)]["text"]) for c in track.cues
        ]
        payloads = {
            ext: render_subtitle(translated, ext).encode("utf-8")
            for ext in ("srt", "vtt")
        }
        for ext, payload in payloads.items():
            if parse_subtitle(payload.decode("utf-8"), ext) != translated:
                raise TranslationError(
                    "Translated track failed cue mapping or timing verification"
                )
        provenance = {
            "schema_version": "1.0",
            "provider": "DeepL",
            "model_type": MODEL,
            "model_type_used": sorted(
                {
                    values[track.key(c.text)]["model_type_used"]
                    for c in track.cues
                    if values[track.key(c.text)]["model_type_used"]
                }
            ),
            "source_lang": track.source_lang,
            "target_lang": TARGET,
            "detected_source_languages": sorted(
                {
                    values[track.key(c.text)]["detected_source_language"]
                    for c in track.cues
                }
            ),
            "anime_id": track.anime_id,
            "slug": track.slug,
            "episode": track.episode,
            "source_filename": track.path.name,
            "source_url": track.source_url,
            "source_sha256": track.source_sha256,
            "context_sha256": _hash(track.context.encode("utf-8")),
            "output_sha256": {ext: _hash(data) for ext, data in payloads.items()},
            "cues": len(translated),
            "timing_preserved": True,
            "human_review": False,
            "translation_accuracy": "not_verified",
            "complete_anime": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        paths = _paths(output, track)
        # Exclusive creation prevents overwriting an output that appeared since
        # the initial guard. Each file is fully serialized before publication.
        published = []
        try:
            for ext, payload in {
                **payloads,
                "provenance.json": _json(provenance),
            }.items():
                path = paths[ext]
                _publish_exclusive(path, payload)
                published.append(path)
        except OSError:
            for path in published:
                path.unlink(missing_ok=True)
            raise TranslationError(
                "Output could not be written without overwriting existing files"
            ) from None
        processed += 1
    return {
        "provider": "DeepL",
        "processed_tracks": processed,
        "skipped_verified_tracks": len(plan.tracks) - len(pending),
        "distinct_anime_with_processed_tracks": len({t.anime_id for t in pending}),
        "distinct_anime_with_completed_tracks": len({t.anime_id for t in plan.tracks}),
        "complete_anime": 0,
        "human_review": False,
        "submitted_characters_this_run": client.submitted_characters,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source", "--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".build/deepl-output"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".build/deepl-cache"))
    parser.add_argument("--max-anime", type=int)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--plan", action="store_true")
    parser.add_argument("--max-characters", type=int)
    parser.add_argument("--endpoint", choices=sorted(ENDPOINTS))
    args = parser.parse_args(argv)
    try:
        plan = make_plan(
            args.manifest, args.source, args.cache_dir, max_anime=args.max_anime
        )
        if args.execute:
            if args.max_characters is None:
                raise TranslationError(
                    "--execute requires an explicit --max-characters budget"
                )
            result = execute_plan(
                plan,
                args.output,
                args.cache_dir,
                max_characters=args.max_characters,
                client=DeepLClient(endpoint=args.endpoint),
            )
        else:
            result = {"mode": "plan", **plan.summary()}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (TranslationError, OSError):
        # Exception messages from this module contain no transcript or response
        # bodies. OS errors can include sensitive paths, so use a generic message.
        import sys

        error = sys.exception()
        print(
            json.dumps(
                {
                    "error": str(error)
                    if isinstance(error, TranslationError)
                    else "Translation filesystem operation failed"
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
