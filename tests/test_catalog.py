import json
import tempfile
import unittest
from pathlib import Path

from subtitle_api.build import build
from subtitle_api.subtitles import identify_file, normalize_subtitle, parse_subtitle

SRT = "1\n00:00:00,500 --> 00:00:02,000\nСәлем, әлем!\n"
VTT = "WEBVTT\n\n00:00:00.500 --> 00:00:02.000\nСәлем, әлем!\n"
ASS = "[Script Info]\nScriptType: v4.00+\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.50,0:00:02.00,Default,,0,0,0,,Сәлем, әлем!\n"


class SubtitleTests(unittest.TestCase):
    def test_episode_recognition_anchors_the_whole_filename(self):
        self.assertEqual(identify_file("zom-100", "zom-100-2ep.srt"), (2, "srt", 1))
        self.assertEqual(identify_file("zom-100", "ep_02.kk.srt"), (2, "srt", 0))
        self.assertIsNone(identify_file("zom-100", "other-100ep.srt"))
        self.assertEqual(identify_file("zom-100", "ep_00.kk.srt"), (0, "srt", 0))

    def test_all_three_formats_produce_the_same_cue(self):
        cues = [
            parse_subtitle(text, ext)
            for ext, text in [("srt", SRT), ("vtt", VTT), ("ass", ASS)]
        ]
        self.assertEqual(cues[0], cues[1])
        self.assertEqual(cues[0], cues[2])
        self.assertEqual(cues[0][0].text, "Сәлем, әлем!")

    def test_rejects_overflow_timestamps_and_zero_length(self):
        for text in [
            SRT.replace("00:00:02,000", "00:60:02,000"),
            SRT.replace("00:00:02,000", "00:00:00,500"),
            "",
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_subtitle(text, "srt")

    def test_ass_text_can_contain_commas_and_reordered_columns(self):
        text = "[Events]\nFormat: Start, End, Text\nDialogue: 0:00:00.50,0:00:02.00,Сәлем, әлем!\n"
        self.assertEqual(parse_subtitle(text, "ass")[0].text, "Сәлем, әлем!")

    def test_vtt_cue_settings_and_notes_are_supported(self):
        text = "WEBVTT\n\nNOTE attribution\nhello\n\ncue-id\n00:00:00.500 --> 00:00:02.000 align:start\nСәлем, әлем!\n"
        self.assertEqual(parse_subtitle(text, "vtt"), parse_subtitle(SRT, "srt"))

    def test_normalizes_mixed_ass_timestamps_without_changing_dialogue(self):
        broken = SRT.replace("00:00:00,500", "0:00:00.50").replace(
            "00:00:02,000", "0:00:02.00"
        )
        self.assertEqual(normalize_subtitle(broken, "srt"), SRT)
        self.assertEqual(
            parse_subtitle(normalize_subtitle(broken, "srt"), "srt"),
            parse_subtitle(SRT, "srt"),
        )

    def test_normalization_does_not_invent_durations(self):
        broken = SRT.replace("00:00:02,000", "00:00:00,500")
        with self.assertRaises(ValueError):
            parse_subtitle(normalize_subtitle(broken, "srt"), "srt")

    def test_empty_cues_are_removed_without_losing_dialogue(self):
        text = SRT + "\n2\n00:00:03,000 --> 00:00:04,000\n\n"
        self.assertEqual(
            parse_subtitle(normalize_subtitle(text, "srt"), "srt"),
            parse_subtitle(SRT, "srt"),
        )


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "public"
        self.metadata = self.root / "metadata.json"

    def write_asset(self, slug, filename, text):
        path = self.root / "subtitles" / slug / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_build(self, entries):
        self.metadata.write_text(json.dumps(entries), encoding="utf-8")
        return build(self.root, self.output, self.metadata)

    def test_counts_episode_tracks_once_and_only_links_existing_formats(self):
        self.write_asset("demo", "ep_01.kk.srt", SRT)
        self.write_asset("demo", "demo-1ep.srt", SRT)
        self.write_asset("demo", "ep_01.kk.vtt", VTT)
        result = self.run_build(
            [{"id": 123, "slug": "demo", "title": {"english": "Demo"}, "episodes": 12}]
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["total_episodes"], 1)
        self.assertEqual(result["total_files"], 3)
        detail = json.loads((self.output / "api/v1/anime/demo.json").read_text())
        self.assertEqual(detail["subtitles"][0]["assets"]["ass"]["origin"], "derived")
        self.assertEqual(detail["translated_episodes"], [1])
        self.assertEqual(detail["coverage_status"], "unverified")
        self.assertIn(
            "/subtitles/demo/ep_01.kk.vtt", detail["subtitles"][0]["files"]["vtt"]
        )

    def test_duplicate_ids_have_explicit_disambiguation(self):
        for slug in ["first", "second"]:
            self.write_asset(slug, "ep_01.kk.srt", SRT)
        self.run_build(
            [
                {"id": 123, "slug": slug, "title": {"english": slug}}
                for slug in ["first", "second"]
            ]
        )
        alias = json.loads((self.output / "api/v1/anime/123.json").read_text())
        self.assertEqual(alias["error"]["code"], "ambiguous_legacy_id")
        self.assertEqual(len(alias["matches"]), 2)

    def test_rejects_invalid_format_instead_of_advertising_it(self):
        self.write_asset("demo", "ep_01.kk.srt", SRT)
        self.write_asset("demo", "ep_01.kk.vtt", "not a subtitle")
        self.run_build([{"slug": "demo", "title": {"english": "Demo"}}])
        detail = json.loads((self.output / "api/v1/anime/demo.json").read_text())
        self.assertEqual(detail["subtitles"][0]["assets"]["vtt"]["origin"], "derived")
        audit = json.loads((self.output / "api/v1/audit.json").read_text())
        self.assertGreater(audit["issue_counts"].get("invalid_subtitle", 0), 0)

    def test_missing_release_is_a_build_error(self):
        with self.assertRaisesRegex(ValueError, "no subtitle"):
            self.run_build([{"slug": "missing"}])

    def test_build_is_byte_deterministic(self):
        self.write_asset("demo", "ep_01.kk.srt", SRT)
        entries = [{"slug": "demo", "title": {"english": "Demo"}}]
        self.run_build(entries)
        before = {
            str(p.relative_to(self.output)): p.read_bytes()
            for p in self.output.rglob("*.json")
        }
        self.run_build(entries)
        after = {
            str(p.relative_to(self.output)): p.read_bytes()
            for p in self.output.rglob("*.json")
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
