import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

from subtitle_api.discovery import write_discovery


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.meta = []
        self.schemas = []
        self.in_schema = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link":
            self.links.append(attrs)
        if tag == "meta":
            self.meta.append(attrs)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_schema = True

    def handle_data(self, data):
        if self.in_schema:
            self.schemas.append(json.loads(data))

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_schema = False


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = "https://example.test/anime-subtitles-kazakh"
        self.catalog = {
            "total": 1,
            "total_episodes": 2,
            "language": "kk",
            "data": [
                {
                    "slug": "demo",
                    "title": {"english": "Unverified </script><img src=x>"},
                    "episodes": 99,
                    "available_episodes_count": 2,
                    "averageScore": 100,
                    "translated_episodes": [0, 264],
                }
            ],
        }
        self.stats = {
            "total": 1,
            "total_episodes": 2,
            "human_verified_translations": 0,
            "complete_series_verified": 0,
        }

    def page(
        self, relative, text="<!doctype html><html><head></head><body>UI</body></html>"
    ):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def generate(self, **kwargs):
        return write_discovery(
            self.root, self.catalog, self.stats, kwargs.get("base_url", self.base)
        )

    def test_sitemap_lists_only_real_canonical_pages_under_project_path(self):
        self.page("index.html")
        self.page("api.html")
        self.page(
            "api/index.html", '<meta http-equiv="refresh" content="0;url=../api.html">'
        )
        self.page("api/v1/anime/demo.json", "{}")
        self.generate()
        root = ET.fromstring((self.root / "sitemap.xml").read_bytes())
        locations = [node.text for node in root.findall("{*}url/{*}loc")]
        self.assertEqual(
            locations,
            [
                "https://example.test/anime-subtitles-kazakh/",
                "https://example.test/anime-subtitles-kazakh/api.html",
            ],
        )
        self.assertFalse(root.findall("{*}url/{*}lastmod"))
        robots = (self.root / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Allow: /anime-subtitles-kazakh/\n", robots)
        self.assertIn(
            "Sitemap: https://example.test/anime-subtitles-kazakh/sitemap.xml\n",
            robots,
        )
        self.assertIn("origin root", robots)

    def test_dataset_counts_tracks_without_promoting_unverified_metadata(self):
        self.page("api/v1/anime.json", "{}")
        self.page("api/v1/stats.json", "{}")
        self.page("api/v1/audit.json", "{}")
        original = copy.deepcopy((self.catalog, self.stats))
        self.generate()
        document = json.loads((self.root / "discovery.jsonld").read_bytes())
        dataset = next(x for x in document["@graph"] if x["@type"] == "Dataset")
        self.assertIn("1 release entries", dataset["description"])
        self.assertIn("2 usable subtitle tracks", dataset["description"])
        self.assertIn("machine-translated", dataset["description"])
        self.assertIn("human", dataset["description"])
        self.assertEqual(dataset["inLanguage"], "kk")
        self.assertEqual(
            dataset["distribution"][0]["contentUrl"],
            "https://example.test/anime-subtitles-kazakh/api/v1/anime.json",
        )
        payload = json.dumps(document)
        for invented in (
            "FAQPage",
            "aggregateRating",
            "Review",
            "99",
            "264",
            "Unverified",
        ):
            self.assertNotIn(invented, payload)
        self.assertEqual((self.catalog, self.stats), original)

    def test_does_not_advertise_missing_distribution_or_pages(self):
        self.generate()
        document = json.loads((self.root / "discovery.jsonld").read_bytes())
        dataset = next(x for x in document["@graph"] if x["@type"] == "Dataset")
        self.assertNotIn("distribution", dataset)
        root = ET.fromstring((self.root / "sitemap.xml").read_bytes())
        self.assertEqual(root.findall("{*}url"), [])
        self.assertFalse((self.root / "index.html").exists())

    def test_refreshes_only_head_metadata_preserving_body_and_authored_code(self):
        authored = '<script>const markup = "<title>Keep</title>";</script>'
        body = '<body><p id="exact">Қазақша UI</p><script>go()</script></body></html>'
        self.page(
            "index.html",
            '<!doctype html><html><head><meta charset="UTF-8">'
            '<title>Old</title><link rel="canonical" href="https://old.test/">'
            '<meta name="description" content="Old"><meta property="og:image" content="old">'
            '<script type="application/ld+json">{"@type":"FAQPage"}</script>'
            + authored
            + "</head>"
            + body,
        )
        self.page("api/v1/anime.json", "{}")
        self.page("favicon.svg", "<svg/>")
        self.page("social-card.svg", "<svg/>")
        self.page("openapi.json", "{}")
        self.generate()
        result = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(result.split("</head>", 1)[1], body)
        self.assertIn(authored, result)
        parser = HeadParser()
        parser.feed(result.split("</head>", 1)[0])
        canonicals = [
            link["href"] for link in parser.links if link.get("rel") == "canonical"
        ]
        self.assertEqual(canonicals, [self.base + "/"])
        descriptions = [
            meta for meta in parser.meta if meta.get("name") == "description"
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertIn("Машиналық", descriptions[0]["content"])
        self.assertEqual(len(parser.schemas), 1)
        self.assertEqual(
            parser.schemas[0], json.loads((self.root / "discovery.jsonld").read_bytes())
        )
        self.assertTrue(
            any(link.get("type") == "application/ld+json" for link in parser.links)
        )
        self.assertTrue(any(link.get("rel") == "sitemap" for link in parser.links))
        self.assertTrue(
            any(
                link.get("type") == "application/vnd.oai.openapi+json"
                for link in parser.links
            )
        )
        self.assertEqual(
            result.count("<title>"), 2
        )  # Main title and authored script text.

    def test_xml_escaping_and_local_base_url_rewrite(self):
        self.page("index.html")
        self.page("api.html")
        self.generate(base_url="http://localhost:8000/catalog&archive/")
        root = ET.fromstring((self.root / "sitemap.xml").read_bytes())
        self.assertEqual(
            root.find("{*}url/{*}loc").text, "http://localhost:8000/catalog&archive/"
        )
        parser = HeadParser()
        parser.feed((self.root / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(
            next(
                link["href"] for link in parser.links if link.get("rel") == "canonical"
            ),
            "http://localhost:8000/catalog&archive/",
        )
        self.assertNotIn("ikymory.github.io", json.dumps(parser.schemas))

    def test_repeated_generation_is_byte_and_mtime_stable(self):
        self.page("index.html")
        self.generate()
        before = {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()
        }
        self.generate()
        after = {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()
        }
        self.assertEqual(before, after)

    def test_crlf_body_and_authored_script_bytes_survive_rebasing(self):
        path = self.root / "index.html"
        body = b'<body>\r\n<div data-custom="true">Keep</div>\r\n</body></html>\r\n'
        authored = b'<script>const keep = "<title>literal</title>";</script>\r\n'
        path.write_bytes(
            b"<!doctype html>\r\n<html><head>\r\n" + authored + b"</head>" + body
        )
        self.generate()
        self.generate(base_url="http://localhost:8000")
        result = path.read_bytes()
        self.assertEqual(result.split(b"</head>", 1)[1], body)
        self.assertIn(authored, result)
        parser = HeadParser()
        parser.feed(result.decode("utf-8").split("</head>", 1)[0])
        self.assertEqual(
            [link["href"] for link in parser.links if link.get("rel") == "canonical"],
            ["http://localhost:8000/"],
        )
        self.assertEqual(len(parser.schemas), 1)
        self.assertNotIn(self.base, json.dumps(parser.schemas))
        self.assertNotIn(b"\n", result.replace(b"\r\n", b""))

    def test_rejects_inconsistent_counts_before_writing_outputs(self):
        self.stats["total_episodes"] = 99
        with self.assertRaisesRegex(ValueError, "count"):
            self.generate()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_unsafe_base_urls_before_writing(self):
        for base in (
            "javascript:alert(1)",
            "https://example.test/path?secret=1",
            "https://example.test/#fragment",
            "https://user:password@example.test",
            "https://example.test/a/../b",
            "https://example.test/%2e%2e/path",
            "https://example.test/path\nUser-agent: blocked",
            "https://example.test/path\\folder",
            "https://example.test:bad/",
        ):
            with self.subTest(base=base), self.assertRaises(ValueError):
                self.generate(base_url=base)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_malformed_head_is_rejected_without_rewriting_page(self):
        path = self.page(
            "index.html", "<html><head><title>Unclosed</title><body>UI</body></html>"
        )
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "head"):
            self.generate()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.root / "discovery.jsonld").exists())


if __name__ == "__main__":
    unittest.main()
