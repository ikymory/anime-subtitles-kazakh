"""Local/self-hosted read-only API. Put a reverse proxy in front for production."""

import argparse
import hashlib
import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, unquote, urlsplit


class ApiHandler(SimpleHTTPRequestHandler):
    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".srt": "application/x-subrip; charset=utf-8",
        ".vtt": "text/vtt; charset=utf-8",
        ".ass": "text/x-ssa; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "If-None-Match")
        self.send_header("Access-Control-Expose-Headers", "ETag, Content-Length")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_json(self, data, status=200, *, cache=True):
        body = (
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        etag = '"' + hashlib.sha256(body).hexdigest() + '"'
        if (
            cache
            and status == 200
            and any(
                token.strip().removeprefix("W/") in (etag, "*")
                for token in self.headers.get("If-None-Match", "").split(",")
            )
        ):
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "public, max-age=300")
            self.end_headers()
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Cache-Control",
            "public, max-age=300" if cache and status == 200 else "no-store",
        )
        if status == 200 and cache:
            self.send_header("ETag", etag)
        if status == 405:
            self.send_header("Allow", "GET, HEAD, OPTIONS")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def error(self, status, code, message):
        self.send_json(
            {"error": {"code": code, "message": message}}, status, cache=False
        )

    def send_error(self, code, message=None, explain=None):
        self.error(
            code,
            "not_found" if code == 404 else "http_error",
            message or self.responses.get(code, ("Request failed",))[0],
        )

    def list_directory(self, path):
        self.error(404, "not_found", "Directory listing is disabled")

    def send_head(self):
        # SimpleHTTPRequestHandler selects index.html after resolving a directory.
        # Check the final file as well as the requested directory itself.
        root = Path(self.directory).resolve()
        target = Path(self.translate_path(self.path)).resolve()
        if target.is_dir():
            for name in ("index.html", "index.htm"):
                candidate = target / name
                if candidate.exists():
                    target = candidate.resolve()
                    break
        if not target.is_relative_to(root):
            self.error(403, "forbidden", "Path is outside the public directory")
            return None
        return super().send_head()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        self.error(405, "method_not_allowed", "This API is read-only")

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            self.route()
        except json.JSONDecodeError:
            self.error(
                500,
                "dataset_unavailable",
                "Dataset is unavailable; rebuild the catalog",
            )
        except (ValueError, UnicodeError):
            self.error(400, "invalid_query", "Invalid path or query parameters")
        except (FileNotFoundError, IsADirectoryError):
            self.error(404, "not_found", "Resource not found")
        except OSError:
            self.error(
                500,
                "dataset_unavailable",
                "Dataset is unavailable; rebuild the catalog",
            )

    def route(self):
        if re.search(r"%(?![0-9A-Fa-f]{2})", self.path):
            raise ValueError("Invalid percent encoding")
        url = urlsplit(self.path)
        path = unquote(url.path, errors="strict")
        parts = path.replace("\\", "/").split("/")
        if "\x00" in path or any(part.startswith(".") for part in parts if part):
            self.error(
                400, "invalid_path", "Hidden paths and traversal are not allowed"
            )
            return
        root = Path(self.directory).resolve()
        resolved = (root / path.lstrip("/")).resolve()
        if not resolved.is_relative_to(root):
            self.error(403, "forbidden", "Path is outside the public directory")
            return
        if path == "/health":
            self.send_json(
                {"status": "ok", "releases": self.server.catalog["total"]}, cache=False
            )
        elif path == "/api/v1/anime":
            self.search(url.query)
        elif path in ("/api/v1/stats", "/api/v1/stats.json"):
            self.send_json(self.server.stats)
        elif path in ("/api/v1/anime.json", "/api/v1/audit.json"):
            self.send_json(json.loads(resolved.read_bytes()))
        elif path.startswith("/api/v1/anime/"):
            identifier = path.removeprefix("/api/v1/anime/").removesuffix(".json")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
                self.error(404, "not_found", "Unknown release identifier")
                return
            target = (root / "api/v1/anime" / (identifier + ".json")).resolve()
            if not target.is_relative_to(root):
                self.error(403, "forbidden", "Path is outside the public directory")
                return
            detail = json.loads(target.read_bytes())
            self.send_json(detail, 409 if "error" in detail else 200)
        elif path.startswith("/api/") and path != "/api/index.html":
            self.error(404, "not_found", "Unknown API endpoint")
        else:
            super().do_GET() if self.command != "HEAD" else super().do_HEAD()

    def search(self, query):
        params = parse_qs(
            query, keep_blank_values=True, max_num_fields=16, errors="strict"
        )
        if set(params) - {"q", "genre", "format", "year", "limit", "offset"} or any(
            len(v) != 1 for v in params.values()
        ):
            raise ValueError("Unknown or duplicate parameter")

        def value(key, default=""):
            return params.get(key, [default])[0]

        limit, offset = int(value("limit", "24")), int(value("offset", "0"))
        q, genre, format_ = (
            value("q").strip().casefold(),
            value("genre").casefold(),
            value("format").upper(),
        )
        year = int(value("year")) if value("year") else None
        if (
            not 1 <= limit <= 100
            or not 0 <= offset <= 1000000
            or len(q) > 200
            or len(genre) > 100
            or len(format_) > 20
            or year is not None
            and not 1900 <= year <= 2200
        ):
            raise ValueError("Out-of-range parameter")

        def matches(item):
            titles = item.get("title") or {}
            searchable = " ".join(
                [item["slug"], *[str(v) for v in titles.values() if v]]
            ).casefold()
            return (
                (not q or q in searchable)
                and (
                    not genre or genre in [g.casefold() for g in item.get("genres", [])]
                )
                and (not format_ or item.get("format") == format_)
                and (year is None or item.get("seasonYear") == year)
            )

        selected = [item for item in self.server.catalog["data"] if matches(item)]
        self.send_json(
            {
                "total": len(selected),
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < len(selected),
                "data": selected[offset : offset + limit],
            }
        )


def create_server(
    directory: Path, host: str = "127.0.0.1", port: int = 8000
) -> ThreadingHTTPServer:
    directory = Path(directory).resolve()
    catalog = json.loads((directory / "api/v1/anime.json").read_bytes())
    stats = json.loads((directory / "api/v1/stats.json").read_bytes())
    server = ThreadingHTTPServer(
        (host, port), partial(ApiHandler, directory=str(directory))
    )
    server.daemon_threads = True
    server.catalog = catalog
    server.stats = stats
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with create_server(args.directory, args.host, args.port) as server:
        print(
            f"Subtitle API: http://{server.server_address[0]}:{server.server_address[1]}",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
