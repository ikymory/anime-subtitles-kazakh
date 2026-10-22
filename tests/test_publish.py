import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from subtitle_api.build import build
from subtitle_api.stage import stage
from subtitle_api.validate import validate


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        p = self.root / "subtitles/demo/ep_00.kk.srt"
        p.parent.mkdir(parents=True)
        p.write_text(
            "1\n0:00:01.00 --> 0:00:02.00\nҚазақша ikymory\n", encoding="utf-8"
        )
        (p.parent / "demo-0ep.srt").write_bytes(p.read_bytes())
        self.metadata = self.root / "metadata.json"
        self.metadata.write_text(json.dumps([{"slug": "demo", "id": 1}]))
        self.catalog = self.root / "catalog"
        build(self.root, self.catalog, self.metadata, copy_subtitles=False)

    def test_pages_profile_publishes_canonical_srt_vtt_and_checksums(self):
        public = self.root / "public"
        info = stage(self.catalog, self.root, self.catalog, public)
        detail = json.loads((public / "api/v1/anime/demo.json").read_bytes())
        self.assertIsNone(detail["subtitles"][0]["files"]["ass"])
        self.assertEqual(detail["translated_episodes"], [0])
        self.assertFalse((public / "subtitles/demo/demo-0ep.srt").exists())
        self.assertEqual(info["published_format_files"], 2)
        self.assertEqual(validate(public)["validated_downloads"], 2)

    def test_validator_detects_tampering(self):
        public = self.root / "public"
        stage(self.catalog, self.root, self.catalog, public)
        (public / "subtitles/demo/ep_00.kk.srt").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            validate(public)

    def test_stage_rejects_site_above_budget(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            stage(
                self.catalog, self.root, self.catalog, self.root / "public", max_bytes=1
            )

    def test_stage_detects_changed_source(self):
        (self.root / "subtitles/demo/ep_00.kk.srt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed since build"):
            stage(self.catalog, self.root, self.catalog, self.root / "public")

    def test_validator_rejects_a_url_pointing_at_the_wrong_asset(self):
        public = self.root / "public"
        stage(self.catalog, self.root, self.catalog, public)
        path = public / "api/v1/anime/demo.json"
        detail = json.loads(path.read_bytes())
        detail["subtitles"][0]["files"]["srt"] = "https://example.com/missing.srt"
        path.write_text(json.dumps(detail))
        with self.assertRaisesRegex(ValueError, "URL"):
            validate(public)

    def test_validator_rejects_invalid_cues_even_if_checksums_match(self):
        public = self.root / "public"
        stage(self.catalog, self.root, self.catalog, public)
        path = public / "api/v1/anime/demo.json"
        detail = json.loads(path.read_bytes())
        payload = b"not a subtitle"
        asset = detail["subtitles"][0]["assets"]["srt"]
        (public / asset["path"]).write_bytes(payload)
        asset["sha256"] = hashlib.sha256(payload).hexdigest()
        asset["bytes"] = len(payload)
        path.write_text(json.dumps(detail))
        with self.assertRaisesRegex(ValueError, "Invalid exported subtitle"):
            validate(public)


if __name__ == "__main__":
    unittest.main()
