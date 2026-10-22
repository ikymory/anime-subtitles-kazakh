import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from subtitle_api import translate
from subtitle_api.subtitles import parse_subtitle

SRT = "1\n00:00:00,503 --> 00:00:02,017\nHello there.\n\n2\n00:00:03,111 --> 00:00:04,555\nGood night.\n\n3\n00:00:05,123 --> 00:00:06,987\nHello there.\n"
SECRET = "test-private-key:fx"


class Reply(io.BytesIO):
    def __init__(self, value):
        super().__init__(json.dumps(value, ensure_ascii=False).encode())


class DeepLService:
    """Only replace the external HTTP boundary; real planning/cache/rendering run."""

    def __init__(self, translations=None, limit=1000000, languages=None):
        self.translations = translations
        self.limit = limit
        self.languages = languages if languages is not None else [{"language": "KK"}]
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        if request.full_url.endswith("/languages?type=target"):
            return Reply(self.languages)
        if request.full_url.endswith("/usage"):
            return Reply({"character_count": 0, "character_limit": self.limit})
        body = json.loads(request.data)
        if self.translations is not None:
            return Reply({"translations": self.translations})
        dictionary = {"Hello there.": "Сәлеметсіз бе.", "Good night.": "Қайырлы түн."}
        return Reply(
            {
                "translations": [
                    {
                        "text": dictionary.get(text, "Қазақша мәтін."),
                        "detected_source_language": "EN",
                        "model_type_used": "quality_optimized",
                    }
                    for text in body["text"]
                ]
            }
        )

    def translation_bodies(self):
        return [
            json.loads(r.data)
            for r in self.requests
            if r.full_url.endswith("/translate")
        ]


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "episode.srt").write_text(SRT, encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.record = {
            "anime_id": "anilist:123",
            "slug": "a-new-title",
            "episode": 1,
            "path": "episode.srt",
            "source_lang": "EN",
            "context": "A new title",
        }
        self.write_manifest([self.record])
        self.cache = self.root / ".build" / "cache"
        self.output = self.root / "output"
        self.environment = patch.dict(os.environ, {"DEEPL_AUTH_KEY": SECRET})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_manifest(self, records):
        self.manifest.write_text(json.dumps({"tracks": records}), encoding="utf-8")

    def plan(self):
        return translate.make_plan(self.manifest, self.source, self.cache)

    def execute(self, service=None, max_characters=1000):
        service = service or DeepLService()
        client = translate.DeepLClient(opener=service, sleep=lambda seconds: None)
        return translate.execute_plan(
            self.plan(),
            self.output,
            self.cache,
            max_characters=max_characters,
            client=client,
        )

    def test_plan_counts_unique_text_without_requesting_or_caching(self):
        plan = self.plan()
        self.assertEqual(plan.summary()["distinct_anime"], 1)
        self.assertEqual(plan.summary()["tracks"], 1)
        self.assertEqual(plan.summary()["uncached_characters"], 23)
        self.assertEqual(plan.summary()["cues"], 3)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.output.exists())

    def test_translation_preserves_each_cue_time_and_duplicate_row(self):
        service = DeepLService()
        result = self.execute(service)
        for ext in ("srt", "vtt"):
            cues = parse_subtitle(
                (self.output / "a-new-title" / f"ep_01.kk.{ext}").read_text("utf-8"),
                ext,
            )
            self.assertEqual(
                [(c.start, c.end) for c in cues],
                [(503, 2017), (3111, 4555), (5123, 6987)],
            )
            self.assertEqual(
                [c.text for c in cues],
                ["Сәлеметсіз бе.", "Қайырлы түн.", "Сәлеметсіз бе."],
            )
        self.assertEqual(
            service.translation_bodies()[0]["text"], ["Hello there.", "Good night."]
        )
        self.assertEqual(result["processed_tracks"], 1)
        self.assertEqual(result["complete_anime"], 0)
        provenance = json.loads(
            (self.output / "a-new-title" / "ep_01.kk.provenance.json").read_text(
                "utf-8"
            )
        )
        self.assertFalse(provenance["human_review"])
        self.assertEqual(provenance["provider"], "DeepL")
        self.assertEqual(provenance["cues"], 3)
        self.assertEqual(len(provenance["source_sha256"]), 64)
        self.assertEqual(set(provenance["output_sha256"]), {"srt", "vtt"})
        self.assertNotIn(SECRET, json.dumps(provenance))

    def test_cache_resumes_without_billable_requests(self):
        self.execute()
        plan = self.plan()
        self.assertEqual(plan.summary()["uncached_characters"], 0)
        service = DeepLService()
        result = translate.execute_plan(
            plan,
            self.root / "other",
            self.cache,
            max_characters=1,
            client=translate.DeepLClient(opener=service),
        )
        self.assertEqual(result["submitted_characters_this_run"], 0)
        self.assertEqual(service.translation_bodies(), [])

    def test_cache_isolated_by_language_context_model_and_title(self):
        first = translate.cache_key(
            "Hello", "EN", "KK", "prefer_quality_optimized", "title one", "anilist:123"
        )
        candidates = [
            ("EN", "KK", "prefer_quality_optimized", "title two", "anilist:123"),
            ("DE", "KK", "prefer_quality_optimized", "title one", "anilist:123"),
            ("EN", "DE", "prefer_quality_optimized", "title one", "anilist:123"),
            ("EN", "KK", "quality_optimized", "title one", "anilist:123"),
            ("EN", "KK", "prefer_quality_optimized", "title one", "anilist:456"),
        ]
        self.assertTrue(
            all(translate.cache_key("Hello", *args) != first for args in candidates)
        )

    def test_short_or_extra_provider_arrays_fail_before_output(self):
        for items in (
            [],
            [{"text": "Сәлем.", "detected_source_language": "EN"}],
            [{"text": "Сәлем.", "detected_source_language": "EN"}] * 3,
        ):
            with (
                self.subTest(count=len(items)),
                self.assertRaises(translate.TranslationError),
            ):
                self.execute(DeepLService(translations=items))
        self.assertFalse(self.output.exists())

    def test_copied_or_blank_or_mismatched_language_output_fails_closed(self):
        for item in (
            {"text": "Hello there.", "detected_source_language": "EN"},
            {"text": " ", "detected_source_language": "EN"},
            {"text": "Сәлем.", "detected_source_language": "JA"},
            {"text": "Сәлем.\n\nТүн.", "detected_source_language": "EN"},
        ):
            with self.subTest(item=item), self.assertRaises(translate.TranslationError):
                self.execute(DeepLService(translations=[item, item]))
        self.assertFalse(self.output.exists())

    def test_budget_and_live_quota_guard_prevent_translation(self):
        for budget, quota in ((22, 100000), (1000, 22)):
            service = DeepLService(limit=quota)
            with (
                self.subTest(budget=budget, quota=quota),
                self.assertRaises(translate.TranslationError),
            ):
                self.execute(service, max_characters=budget)
            self.assertEqual(service.translation_bodies(), [])

    def test_substantive_source_cannot_be_replaced_by_punctuation_placeholders(self):
        for placeholder in ("...", "…", "!!!", "♪", "<i>...</i>"):
            item = {"text": placeholder, "detected_source_language": "EN"}
            with (
                self.subTest(placeholder=placeholder),
                self.assertRaises(translate.TranslationError),
            ):
                self.execute(DeepLService(translations=[item, item]))
        self.assertFalse(self.output.exists())
        self.assertFalse(self.cache.exists())

    def test_punctuation_only_source_remains_a_legitimate_cue(self):
        (self.source / "episode.srt").write_text(
            SRT.replace("Hello there.", "...").replace("Good night.", "?!"),
            encoding="utf-8",
        )
        service = DeepLService(
            translations=[
                {"text": "...", "detected_source_language": "EN"},
                {"text": "?!", "detected_source_language": "EN"},
            ]
        )
        self.execute(service)
        cues = parse_subtitle(
            (self.output / "a-new-title" / "ep_01.kk.srt").read_text("utf-8"), "srt"
        )
        self.assertEqual([cue.text for cue in cues], ["...", "?!", "..."])

    def test_cjk_script_output_requires_review_before_kazakh_publication(self):
        for untranslated in (
            "こんにちは。",
            "Good night. おやすみ",
            "晚安。",
            "잘 자요.",
        ):
            item = {"text": untranslated, "detected_source_language": "EN"}
            with (
                self.subTest(untranslated=untranslated),
                self.assertRaises(translate.TranslationError),
            ):
                self.execute(DeepLService(translations=[item, item]))
        self.assertFalse(self.output.exists())

    def test_source_cjk_sentence_cannot_be_translated_into_placeholder(self):
        (self.source / "episode.srt").write_text(
            SRT.replace("Hello there.", "こんにちは。").replace(
                "Good night.", "おやすみ。"
            ),
            encoding="utf-8",
        )
        self.write_manifest([dict(self.record, source_lang="JA")])
        item = {"text": "…", "detected_source_language": "JA"}
        with self.assertRaises(translate.TranslationError):
            self.execute(DeepLService(translations=[item, item]))
        self.assertFalse(self.output.exists())

    def test_kazakh_support_is_checked_before_billable_request(self):
        service = DeepLService(languages=[{"language": "EN"}])
        with self.assertRaises(translate.TranslationError):
            self.execute(service)
        self.assertEqual(service.translation_bodies(), [])

    def test_unicode_request_byte_limit_and_fifty_text_limit(self):
        batches = translate.make_batches(["界" * 10000] * 55, "JA", "KK", "ctx")
        self.assertEqual(sum(len(batch) for batch in batches), 55)
        for batch in batches:
            payload = translate.request_payload(batch, "JA", "KK", "ctx")
            self.assertLessEqual(len(payload), 128 * 1024)
            self.assertLessEqual(len(batch), 50)
        with self.assertRaises(translate.TranslationError):
            translate.make_batches(["界" * 50000], "JA", "KK", "ctx")

    def test_same_content_under_different_anime_id_is_rejected(self):
        other = dict(self.record, anime_id="anilist:456", slug="different-anime")
        self.write_manifest([self.record, other])
        with self.assertRaises(translate.TranslationError):
            self.plan()

    def test_duplicate_track_or_identity_slug_alias_is_rejected(self):
        for other in (dict(self.record), dict(self.record, slug="alias", episode=2)):
            self.write_manifest([self.record, other])
            with (
                self.subTest(other=other),
                self.assertRaises(translate.TranslationError),
            ):
                self.plan()

    def test_source_path_escape_and_output_inside_source_are_rejected(self):
        self.write_manifest([dict(self.record, path="../manifest.json")])
        with self.assertRaises(translate.TranslationError):
            self.plan()
        self.write_manifest([self.record])
        with self.assertRaises(translate.TranslationError):
            translate.execute_plan(
                self.plan(),
                self.source / "output",
                self.cache,
                max_characters=1000,
                client=translate.DeepLClient(opener=DeepLService()),
            )

    def test_output_subdirectory_symlink_cannot_write_back_into_source(self):
        self.output.mkdir()
        try:
            (self.output / "a-new-title").symlink_to(
                self.source, target_is_directory=True
            )
        except OSError:
            self.skipTest("Directory symlink creation unavailable")
        service = DeepLService()
        with self.assertRaises(translate.TranslationError):
            self.execute(service)
        self.assertEqual(service.requests, [])
        self.assertFalse((self.source / "ep_01.kk.srt").exists())

    def test_existing_output_is_never_overwritten(self):
        path = self.output / "a-new-title" / "ep_01.kk.srt"
        path.parent.mkdir(parents=True)
        original = b"authored subtitle must survive"
        path.write_bytes(original)
        service = DeepLService()
        with self.assertRaises(translate.TranslationError):
            self.execute(service)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(service.requests, [])

    def test_multi_track_failure_resumes_same_output_without_retranslating_completed_track(
        self,
    ):
        (self.source / "second.srt").write_text(
            SRT.replace("Hello there.", "We should go.").replace(
                "Good night.", "The train is here."
            ),
            "utf-8",
        )
        self.write_manifest(
            [self.record, dict(self.record, episode=2, path="second.srt")]
        )

        class SecondTrackFailure(DeepLService):
            def open(self, request, timeout):
                if (
                    request.full_url.endswith("/translate")
                    and self.translation_bodies()
                ):
                    raise urllib.error.HTTPError(
                        request.full_url, 456, "quota", {}, None
                    )
                return super().open(request, timeout)

        with self.assertRaises(translate.TranslationError):
            self.execute(SecondTrackFailure())
        first_files = list((self.output / "a-new-title").glob("ep_01.kk.*"))
        self.assertEqual(len(first_files), 3)
        original = {
            path: (path.read_bytes(), path.stat().st_mtime_ns) for path in first_files
        }
        self.assertFalse((self.output / "a-new-title" / "ep_02.kk.srt").exists())
        service = DeepLService()
        result = self.execute(service)
        self.assertEqual(result["processed_tracks"], 1)
        self.assertEqual(result["skipped_verified_tracks"], 1)
        self.assertEqual(len(service.translation_bodies()), 1)
        self.assertEqual(
            service.translation_bodies()[0]["text"],
            ["We should go.", "The train is here."],
        )
        for path, value in original.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), value)
        service = DeepLService()
        result = self.execute(service, max_characters=1)
        self.assertEqual(result["processed_tracks"], 0)
        self.assertEqual(result["skipped_verified_tracks"], 2)
        self.assertEqual(service.translation_bodies(), [])

    def test_resume_rejects_partial_or_tampered_or_mismatched_output_before_network(
        self,
    ):
        self.execute()
        directory = self.output / "a-new-title"
        paths = {
            ext: directory / f"ep_01.kk.{ext}"
            for ext in ("srt", "vtt", "provenance.json")
        }
        original = {ext: path.read_bytes() for ext, path in paths.items()}
        for mutation in (
            "missing",
            "tampered",
            "identity",
            "source_hash",
            "human_review",
            "timing",
        ):
            for ext, path in paths.items():
                path.write_bytes(original[ext])
            provenance = json.loads(original["provenance.json"])
            if mutation == "missing":
                paths["provenance.json"].unlink()
            elif mutation == "tampered":
                paths["vtt"].write_bytes(b"tampered")
            else:
                if mutation == "identity":
                    provenance["anime_id"] = "anilist:999"
                elif mutation == "source_hash":
                    provenance["source_sha256"] = "0" * 64
                elif mutation == "human_review":
                    provenance["human_review"] = True
                elif mutation == "timing":
                    import hashlib

                    changed = original["srt"].replace(b"00:00:00,503", b"00:00:00,504")
                    paths["srt"].write_bytes(changed)
                    provenance["output_sha256"]["srt"] = hashlib.sha256(
                        changed
                    ).hexdigest()
                paths["provenance.json"].write_text(json.dumps(provenance), "utf-8")
            service = DeepLService()
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(translate.TranslationError),
            ):
                self.execute(service)
            self.assertEqual(service.requests, [])

    def test_all_existing_output_is_validated_before_translating_any_pending_track(
        self,
    ):
        (self.source / "second.srt").write_text(
            SRT.replace("Hello there.", "A different opening."), "utf-8"
        )
        second = dict(self.record, episode=2, path="second.srt")
        self.write_manifest([second])
        self.execute()
        (self.output / "a-new-title" / "ep_02.kk.vtt").write_bytes(b"tampered")
        self.write_manifest([self.record, second])
        service = DeepLService()
        with self.assertRaises(translate.TranslationError):
            self.execute(service)
        self.assertEqual(service.requests, [])

    def test_output_failure_never_publishes_partial_subtitle(self):
        self.output.mkdir()
        original_link = os.link

        def fail_second_link(source, destination, **kwargs):
            if str(destination).endswith(".vtt"):
                raise OSError("simulated publication failure")
            return original_link(source, destination, **kwargs)

        with patch.object(os, "link", side_effect=fail_second_link):
            with self.assertRaises(translate.TranslationError):
                self.execute()
        self.assertEqual(list(self.output.rglob("*.srt")), [])
        self.assertEqual(list(self.output.rglob("*.vtt")), [])
        self.assertEqual(list(self.output.rglob("*.tmp")), [])

    def test_mixed_identity_namespaces_are_rejected_to_prevent_alias_duplicates(self):
        (self.source / "other.srt").write_text(
            SRT.replace("Hello there.", "A different opening."), "utf-8"
        )
        self.write_manifest(
            [
                self.record,
                dict(
                    self.record,
                    anime_id="myanimelist:456",
                    slug="different-anime",
                    path="other.srt",
                ),
            ]
        )
        with self.assertRaises(translate.TranslationError):
            self.plan()

    def test_cli_plan_needs_no_credentials_and_execute_requires_budget(self):
        environment = dict(os.environ)
        environment.pop("DEEPL_AUTH_KEY", None)
        base = [
            sys.executable,
            "-m",
            "subtitle_api.translate",
            "--manifest",
            str(self.manifest),
            "--source",
            str(self.source),
            "--cache-dir",
            str(self.cache),
        ]
        process = subprocess.run(
            base + ["--plan"], capture_output=True, text=True, env=environment
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["uncached_characters"], 23)
        self.assertFalse(self.cache.exists())
        process = subprocess.run(
            base + ["--execute"], capture_output=True, text=True, env=environment
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("max-characters", process.stderr)

    def test_key_level_usage_limit_is_enforced(self):
        class KeyLimited(DeepLService):
            def open(self, request, timeout):
                if request.full_url.endswith("/usage"):
                    return Reply(
                        {
                            "character_count": 0,
                            "character_limit": 100000,
                            "api_key_character_count": 98,
                            "api_key_character_limit": 100,
                        }
                    )
                return super().open(request, timeout)

        service = KeyLimited()
        with self.assertRaises(translate.TranslationError):
            self.execute(service)
        self.assertEqual(service.translation_bodies(), [])

    def test_corrupt_cache_is_not_silently_replaced_or_used(self):
        self.execute()
        cache_file = next(self.cache.glob("*.json"))
        cache_file.write_text("{not-json", "utf-8")
        with self.assertRaises(translate.TranslationError):
            self.plan()

    def test_changed_source_after_plan_is_rejected_before_requests(self):
        plan = self.plan()
        (self.source / "episode.srt").write_text(
            SRT.replace("Hello there.", "Changed dialogue."), "utf-8"
        )
        service = DeepLService()
        with self.assertRaises(translate.TranslationError):
            translate.execute_plan(
                plan,
                self.output,
                self.cache,
                max_characters=1000,
                client=translate.DeepLClient(opener=service),
            )
        self.assertEqual(service.requests, [])

    def test_http_errors_never_expose_key_or_transcript(self):
        class Failure:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(
                    request.full_url,
                    403,
                    SECRET + " Hello there.",
                    {},
                    io.BytesIO((SECRET + " Hello there.").encode()),
                )

        client = translate.DeepLClient(opener=Failure())
        with self.assertRaises(translate.TranslationError) as caught:
            client.preflight(23)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIn("Hello there.", str(caught.exception))
        self.assertNotIn(SECRET, repr(client))

    def test_official_endpoints_only_and_missing_key_fail_closed(self):
        with self.assertRaises(translate.TranslationError):
            translate.DeepLClient(endpoint="https://attacker.example")
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaises(translate.TranslationError),
        ):
            translate.DeepLClient(opener=DeepLService())

    def test_transient_failures_are_bounded_and_auth_not_retried(self):
        class Failure:
            def __init__(self, status):
                self.count = 0
                self.status = status

            def open(self, request, timeout):
                self.count += 1
                raise urllib.error.HTTPError(
                    request.full_url,
                    self.status,
                    "unsafe body",
                    {"Retry-After": "99999"},
                    None,
                )

        for status, attempts in ((429, 4), (503, 4), (403, 1), (456, 1)):
            service = Failure(status)
            sleeps = []
            client = translate.DeepLClient(opener=service, sleep=sleeps.append)
            with (
                self.subTest(status=status),
                self.assertRaises(translate.TranslationError),
            ):
                client.preflight(23)
            self.assertEqual(service.count, attempts)
            self.assertTrue(all(delay <= 30 for delay in sleeps))

    def test_retried_paid_requests_cannot_exceed_character_or_quota_budget(self):
        class OneRetry(DeepLService):
            def __init__(self, limit):
                super().__init__(limit=limit)
                self.failed = False

            def open(self, request, timeout):
                if request.full_url.endswith("/translate") and not self.failed:
                    self.failed = True
                    self.requests.append(request)
                    raise urllib.error.HTTPError(
                        request.full_url, 503, "temporary", {}, None
                    )
                return super().open(request, timeout)

        for budget, quota in ((23, 1000), (1000, 23)):
            service = OneRetry(quota)
            with (
                self.subTest(budget=budget, quota=quota),
                self.assertRaises(translate.TranslationError),
            ):
                self.execute(service, max_characters=budget)
            self.assertEqual(len(service.translation_bodies()), 1)
        service = OneRetry(1000)
        result = self.execute(service, max_characters=46)
        self.assertEqual(result["submitted_characters_this_run"], 46)
        self.assertEqual(len(service.translation_bodies()), 2)

    def test_progress_cache_survives_later_batch_failure(self):
        texts = [f"Distinct sentence {number}." for number in range(51)]
        source = "\n\n".join(
            f"{n + 1}\n00:00:{n:02d},000 --> 00:00:{n:02d},999\n{text}"
            for n, text in enumerate(texts)
        )
        (self.source / "episode.srt").write_text(source, encoding="utf-8")

        class LaterFailure(DeepLService):
            def open(self, request, timeout):
                if (
                    request.full_url.endswith("/translate")
                    and self.translation_bodies()
                ):
                    raise urllib.error.HTTPError(
                        request.full_url, 456, "quota", {}, None
                    )
                return super().open(request, timeout)

        with self.assertRaises(translate.TranslationError):
            self.execute(LaterFailure(), max_characters=10000)
        self.assertFalse(self.output.exists())
        self.assertEqual(
            self.plan().summary()["uncached_characters"], len("Distinct sentence 50.")
        )


if __name__ == "__main__":
    unittest.main()
