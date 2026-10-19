import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from subtitle_api.build import build
from subtitle_api.server import create_server


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        for slug in ["first", "second"]:
            p = root / "subtitles" / slug / "ep_01.kk.srt"
            p.parent.mkdir(parents=True)
            p.write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nҚазақша\n", encoding="utf-8"
            )
        metadata = root / "metadata.json"
        metadata.write_text(
            json.dumps(
                [
                    {
                        "slug": slug,
                        "id": 7,
                        "title": {"english": slug, "kazakh": "Қазақша"},
                        "genres": ["Fantasy"],
                        "format": "TV",
                        "seasonYear": 2024,
                    }
                    for slug in ["first", "second"]
                ]
            ),
            encoding="utf-8",
        )
        cls.public = root / "public"
        build(root, cls.public, metadata)
        (cls.public / "index.html").write_text("<h1>Catalog</h1>")
        cls.server = create_server(cls.public, "127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.headers, response.read()
        connection.close()
        return result

    def test_pagination_and_case_insensitive_filtering(self):
        status, headers, body = self.request(
            "/api/v1/anime?genre=fantasy&limit=1&offset=1"
        )
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["data"][0]["slug"], "second")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual(
            json.loads(self.request("/api/v1/anime?q=first")[2])["total"], 1
        )

    def test_query_validation(self):
        for query in [
            "limit=0",
            "limit=101",
            "offset=-1",
            "limit=x",
            "year=no",
            "q=" + ("a" * 201),
            "unknown=value",
            "limit=1&limit=2",
        ]:
            with self.subTest(query=query):
                status, _, body = self.request("/api/v1/anime?" + query)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(body)["error"]["code"], "invalid_query")

    def test_details_and_ambiguous_legacy_ids(self):
        self.assertEqual(
            json.loads(self.request("/api/v1/anime/first")[2])["slug"], "first"
        )
        self.assertEqual(self.request("/api/v1/anime/7")[0], 409)
        self.assertEqual(self.request("/api/v1/anime/7.json")[0], 409)
        self.assertEqual(self.request("/api/v1/anime/missing")[0], 404)

    def test_head_caching_and_options(self):
        _, headers, body = self.request("/api/v1/anime")
        self.assertEqual(
            self.request("/api/v1/anime", headers={"If-None-Match": headers["ETag"]})[
                0
            ],
            304,
        )
        head = self.request("/api/v1/anime", "HEAD")
        self.assertEqual(head[0], 200)
        self.assertEqual(head[2], b"")
        self.assertEqual(head[1]["Content-Length"], str(len(body)))
        self.assertEqual(self.request("/api/v1/anime", "OPTIONS")[0], 204)
        self.assertEqual(self.request("/api/v1/anime", "POST")[0], 405)

    def test_traversal_and_hidden_files_are_blocked(self):
        for path in [
            "/../metadata.json",
            "/%2e%2e/metadata.json",
            "/.env",
            "/subtitles/../../../metadata.json",
            "/api/v1/anime/../metadata",
        ]:
            with self.subTest(path=path):
                self.assertIn(self.request(path)[0], [400, 403, 404])

    def test_stats_health_and_subtitle_mime(self):
        self.assertEqual(self.request("/health")[0], 200)
        self.assertEqual(
            json.loads(self.request("/api/v1/stats")[2])["total_episodes"], 2
        )
        status, headers, body = self.request("/subtitles/first/ep_01.kk.srt")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("application/x-subrip"))
        self.assertIn("Қазақша", body.decode("utf-8"))

    def test_static_catalog_remains_compatible(self):
        self.assertEqual(json.loads(self.request("/api/v1/anime.json")[2])["total"], 2)
        self.assertEqual(self.request("/")[0], 200)
        status, headers, _ = self.request("/api/v1/no-such-route")
        self.assertEqual(status, 404)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")

    def test_extensionless_detail_cannot_follow_a_symlink_outside_public(self):
        outside = Path(self.tmp.name) / "private.json"
        outside.write_text('{"secret":"private"}')
        link = self.public / "api/v1/anime/outside.json"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        try:
            status, _, body = self.request("/api/v1/anime/outside")
            self.assertEqual(status, 403)
            self.assertNotIn(b"private", body)
        finally:
            link.unlink()

    def test_automatic_directory_index_cannot_escape_public(self):
        outside = Path(self.tmp.name) / "private.html"
        outside.write_text("SECRET_MARKER")
        folder = self.public / "nested"
        folder.mkdir(exist_ok=True)
        link = folder / "index.html"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        try:
            status, _, body = self.request("/nested/")
            self.assertEqual(status, 403)
            self.assertNotIn(b"SECRET_MARKER", body)
        finally:
            link.unlink()

    def test_malformed_percent_encoding_returns_bad_request(self):
        for path in ["/api/v1/anime?q=%FF", "/api/v1/anime?q=%ZZ", "/api/v1/anime/%ZZ"]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 400)

    def test_invalid_dataset_is_a_server_error(self):
        target = self.public / "api/v1/anime/corrupt.json"
        target.write_text("{broken")
        try:
            status, _, body = self.request("/api/v1/anime/corrupt")
            self.assertEqual(status, 500)
            self.assertEqual(json.loads(body)["error"]["code"], "dataset_unavailable")
        finally:
            target.unlink()


if __name__ == "__main__":
    unittest.main()
