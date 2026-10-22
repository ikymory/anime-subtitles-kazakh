import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from subtitle_api.build import build
from subtitle_api.subtitles import Cue, parse_subtitle


class QualityTests(unittest.TestCase):
    def test_reviewed_quarantine_excludes_only_unchanged_evidenced_tracks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "subtitles/demo/ep_01.kk.srt"
            source.parent.mkdir(parents=True)
            source.write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nҚазақша мәтін.\n",
                encoding="utf-8",
                newline="\n",
            )
            original = source.read_bytes()
            metadata = root / "catalog.json"
            metadata.write_text(json.dumps([{"slug": "demo"}]), encoding="utf-8")
            (root / "quarantine.json").write_text(
                json.dumps(
                    {
                        "tracks": [
                            {
                                "slug": "demo",
                                "episode": 1,
                                "source_path": "subtitles/demo/ep_01.kk.srt",
                                "source_sha256": hashlib.sha256(original).hexdigest(),
                                "reason": "Test evidenced synthetic dialogue",
                                "evidence": "test fixture",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output = root / "output"
            result = build(root, output, metadata)
            self.assertEqual(result["total_episodes"], 0)
            detail = json.loads((output / "api/v1/anime/demo.json").read_bytes())
            self.assertEqual(detail["quarantined_episodes"], [1])
            self.assertFalse((output / "subtitles/demo/ep_01.kk.srt").exists())
            self.assertEqual(source.read_bytes(), original)
            source.write_bytes(original.replace(b"\n", b"\r\n"))
            build(root, root / "crlf-output", metadata)
            source.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "Quarantine source changed"):
                build(root, root / "other", metadata)

    def test_build_derives_conflicting_format_from_primary_dialogue(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "subtitles/demo"
            source.mkdir(parents=True)
            (source / "ep_01.kk.srt").write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nҚайырлы таң!\n", encoding="utf-8"
            )
            (source / "ep_01.kk.vtt").write_text(
                "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nБасқа мәтін!\n",
                encoding="utf-8",
            )
            metadata = root / "catalog.json"
            metadata.write_text(json.dumps([{"slug": "demo"}]), encoding="utf-8")
            output = root / "output"
            build(root, output, metadata)
            detail = json.loads((output / "api/v1/anime/demo.json").read_bytes())
            asset = detail["subtitles"][0]["assets"]["vtt"]
            self.assertEqual(asset["origin"], "derived")
            self.assertIn("normalized_subtitle_serialization", detail["quality_flags"])
            stats = json.loads((output / "api/v1/stats.json").read_bytes())
            self.assertEqual(stats["canonical_format_files"], 3)
            cues = parse_subtitle(
                (output / asset["path"]).read_text(encoding="utf-8"), "vtt"
            )
            self.assertEqual(cues[0].text, "Қайырлы таң!")
            self.assertEqual(
                (source / "ep_01.kk.vtt").read_text(encoding="utf-8").splitlines()[-1],
                "Басқа мәтін!",
            )

    def test_dialogue_fingerprint_ignores_watermarks_timing_and_formatting(self):
        from subtitle_api.quality import dialogue_fingerprint

        text = [f"Бұл ұзақ сөйлем нөмірі {index}, шынайы әңгіме." for index in range(6)]
        first = [
            Cue(index * 1000, index * 1000 + 500, line)
            for index, line in enumerate(text)
        ]
        second = [
            Cue(index * 2000, index * 2000 + 1500, f"<i>{line}</i>")
            for index, line in enumerate(text)
        ]
        first.append(Cue(10000, 11000, "@ikymory"))
        self.assertEqual(dialogue_fingerprint(first), dialogue_fingerprint(second))
        self.assertIsNone(dialogue_fingerprint([Cue(0, 1000, "Иә.")]))
        second[-1] = Cue(10000, 12000, "Бұл мүлде басқа сөйлем.")
        self.assertNotEqual(dialogue_fingerprint(first), dialogue_fingerprint(second))

    def test_title_identity_audit_does_not_use_ambiguous_legacy_ids(self):
        from subtitle_api.quality import duplicate_title_groups

        entries = [
            {"slug": "one", "id": 1, "title": {"english": "My Anime!"}},
            {"slug": "two", "id": 2, "title": {"romaji": "Ｍｙ Anime"}},
            {"slug": "three", "id": 1, "title": {"english": "Different Anime"}},
        ]
        self.assertEqual(duplicate_title_groups(entries), [["one", "two"]])

    def test_duplicate_findings_are_propagated_to_release_and_track(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = (
                "\n\n".join(
                    f"{index + 1}\n00:00:{index * 2:02d},000 --> 00:00:{index * 2 + 1:02d},000\nБұл ұзақ сөйлем нөмірі {index}, шынайы әңгіме."
                    for index in range(6)
                )
                + "\n"
            )
            entries = [
                {"slug": slug, "title": {"english": "Same Anime"}}
                for slug in ("first", "second")
            ]
            for entry in entries:
                target = root / "subtitles" / entry["slug"] / "ep_01.kk.srt"
                target.parent.mkdir(parents=True)
                target.write_text(payload, encoding="utf-8")
            metadata = root / "catalog.json"
            metadata.write_text(json.dumps(entries), encoding="utf-8")
            output = root / "output"
            build(root, output, metadata)
            detail = json.loads((output / "api/v1/anime/first.json").read_bytes())
            self.assertIn(
                "duplicate_dialogue_content", detail["subtitles"][0]["quality_flags"]
            )
            self.assertIn("duplicate_title_identity", detail["quality_flags"])
            self.assertEqual(detail["translation_provenance"], "legacy_untraced")
            stats = json.loads((output / "api/v1/stats.json").read_bytes())
            self.assertEqual(stats["duplicate_title_groups"], 1)
            self.assertEqual(stats["duplicate_dialogue_groups"], 1)


if __name__ == "__main__":
    unittest.main()
