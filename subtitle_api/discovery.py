"""Deterministic discovery metadata for real published pages and measured coverage."""

import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from xml.etree.ElementTree import Element, SubElement, indent, tostring

_START = "subtitle-discovery:start"
_END = "subtitle-discovery:end"
_TITLE = "Қазақша аниме субтитрлер | Kazakh Anime Subtitles — ikymory"
_DESCRIPTION = (
    "Қазақша аниме субтитрлер мұрағаты: қолжетімді тректер, SRT/VTT және JSON API. "
    "Машиналық аударма; адам тексеруі, дәлдігі және толықтығы расталмаған."
)
_EN_DESCRIPTION = (
    "Kazakh anime subtitle archive with machine-translated tracks, download manifests "
    "and a read-only JSON API. Translation accuracy, human review and complete-series "
    "coverage are not verified."
)


def _base_url(value: str) -> str:
    if not isinstance(value, str) or any(
        char.isspace() or char in '\\<>"' for char in value
    ):
        raise ValueError("Base URL must be a safe absolute HTTP(S) URL")
    parsed = urlsplit(value)
    try:
        valid = (
            parsed.scheme in ("http", "https")
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and parsed.port != 0
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError as error:
        raise ValueError("Invalid base URL") from error
    decoded_path = unquote(parsed.path)
    if (
        not valid
        or any(char.isspace() or char in '\\<>"' for char in decoded_path)
        or any(part in (".", "..") for part in decoded_path.split("/"))
    ):
        raise ValueError("Invalid base URL")
    path = quote(decoded_path.rstrip("/"), safe="/:@!$&'()*+,;=-._~")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _counts(catalog: dict, stats: dict) -> tuple[int, int]:
    entries = catalog.get("data")
    if not isinstance(entries, list):
        raise ValueError("Catalog data must be a list")
    values = []
    for name in ("total", "total_episodes"):
        count = catalog.get(name)
        if (
            type(count) is not int
            or count < 0
            or stats.get(name) != count
            or type(stats.get(name)) is not int
        ):
            raise ValueError(f"Inconsistent catalog/stats count: {name}")
        values.append(count)
    if values[0] != len(entries):
        raise ValueError("Catalog release count does not match its entries")
    return values[0], values[1]


class _HeadMetadata(HTMLParser):
    """Locate metadata without interpreting tag-like strings inside authored scripts."""

    def __init__(self, document: str):
        super().__init__(convert_charrefs=False)
        self.document = document
        self.offsets = [0]
        for line in document.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.head_start = None
        self.head_end = None
        self.inside = False
        self.removing = None
        self.generated_start = None
        self.ranges = []

    def position(self) -> int:
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.position()
        if tag == "head":
            if self.head_start is not None:
                raise ValueError("Page must have exactly one head")
            self.inside = True
            self.head_start = start + len(self.get_starttag_text())
            return
        if not self.inside or self.removing:
            return
        attrs = dict(attrs)
        kind = (attrs.get("type") or "").lower()
        if tag == "title" or (tag == "script" and kind == "application/ld+json"):
            self.removing = (tag, start)
        elif (
            tag == "meta"
            and (
                (attrs.get("name") or "").lower()
                in ("description", "keywords", "author", "robots", "theme-color")
                or (attrs.get("name") or "").lower().startswith("twitter:")
                or (attrs.get("property") or "").lower().startswith("og:")
            )
        ) or (
            tag == "link"
            and (
                (attrs.get("rel") or "").lower() in ("canonical", "sitemap", "icon")
                or (
                    (attrs.get("rel") or "").lower() == "alternate"
                    and kind
                    in (
                        "application/ld+json",
                        "application/json",
                        "application/vnd.oai.openapi+json",
                    )
                )
            )
        ):
            self.ranges.append((start, start + len(self.get_starttag_text())))

    def handle_endtag(self, tag):
        if not self.inside:
            return
        start = self.position()
        end = self.document.find(">", start) + 1
        if self.removing and self.removing[0] == tag:
            self.ranges.append((self.removing[1], end))
            self.removing = None
        if tag == "head":
            if self.removing or self.generated_start is not None:
                raise ValueError("Unclosed metadata in page head")
            self.head_end = start
            self.inside = False

    def handle_comment(self, data):
        if not self.inside:
            return
        start = self.position()
        if data.strip() == _START:
            if self.generated_start is not None:
                raise ValueError("Duplicate generated metadata in page head")
            newline = (
                "\r\n" if self.document[max(0, start - 2) : start] == "\r\n" else "\n"
            )
            self.generated_start = (
                start - len(newline)
                if self.document[:start].endswith(newline)
                else start
            )
        elif data.strip() == _END:
            if self.generated_start is None:
                raise ValueError("Unexpected generated metadata marker in page head")
            end = self.document.find("-->", start) + 3
            if self.document[end:].startswith("\r\n"):
                end += 2
            elif self.document[end:].startswith("\n"):
                end += 1
            self.ranges.append((self.generated_start, end))
            self.generated_start = None


def _html_metadata(root: Path, base: str, schema: str) -> str:
    def meta(name, value, *, property=False):
        attribute = "property" if property else "name"
        return f'<meta {attribute}="{escape(name, quote=True)}" content="{escape(value, quote=True)}">'

    def link(rel, relative, kind=None):
        mime = f' type="{kind}"' if kind else ""
        return f'<link rel="{rel}"{mime} href="{escape(base + "/" + relative, quote=True)}">'

    lines = [
        f"<title>{escape(_TITLE)}</title>",
        meta("description", _DESCRIPTION),
        meta("author", "ikymory"),
        meta("robots", "index, follow"),
        link("canonical", ""),
        link("sitemap", "sitemap.xml", "application/xml"),
        link("alternate", "discovery.jsonld", "application/ld+json"),
        meta("og:type", "website", property=True),
        meta("og:site_name", "Anime Subtitles Kazakh · ikymory", property=True),
        meta("og:title", _TITLE, property=True),
        meta("og:description", _DESCRIPTION, property=True),
        meta("og:url", base + "/", property=True),
        meta("og:locale", "kk_KZ", property=True),
        meta("twitter:card", "summary"),
        meta("twitter:title", _TITLE),
        meta("twitter:description", _EN_DESCRIPTION),
    ]
    if (root / "api/v1/anime.json").is_file():
        lines.append(link("alternate", "api/v1/anime.json", "application/json"))
    if (root / "openapi.json").is_file():
        lines.append(
            link("alternate", "openapi.json", "application/vnd.oai.openapi+json")
        )
    if (root / "favicon.svg").is_file():
        lines.append(link("icon", "favicon.svg", "image/svg+xml"))
    if (root / "social-card.svg").is_file():
        lines.extend(
            [
                meta("og:image", base + "/social-card.svg", property=True),
                meta(
                    "og:image:alt", "Kazakh subtitle archive by ikymory", property=True
                ),
                meta("twitter:image", base + "/social-card.svg"),
                meta("twitter:image:alt", "Kazakh subtitle archive by ikymory"),
            ]
        )
    # Escape HTML raw-text delimiters even when future schema fields contain '<'.
    safe_schema = (
        schema.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )
    lines.append('<script type="application/ld+json">\n' + safe_schema + "</script>")
    return "\n".join("  " + line for line in lines)


def _refresh_head(document: str, block: str) -> str:
    parsed = _HeadMetadata(document)
    parsed.feed(document)
    parsed.close()
    if parsed.head_start is None or parsed.head_end is None:
        raise ValueError("Page must contain a complete head element")
    ranges = []
    for start, end in sorted(parsed.ranges):
        if ranges and start <= ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], max(end, ranges[-1][1]))
        else:
            ranges.append((start, end))
    preserved = document[parsed.head_start : parsed.head_end]
    for start, end in reversed(ranges):
        preserved = (
            preserved[: start - parsed.head_start]
            + preserved[end - parsed.head_start :]
        )
    newline = "\r\n" if "\r\n" in document else "\n"
    generated = (
        "\n<!-- " + _START + " -->\n" + block + "\n<!-- " + _END + " -->\n"
    ).replace("\n", newline)
    return (
        document[: parsed.head_start]
        + generated
        + preserved
        + document[parsed.head_end :]
    )


def write_discovery(
    output_root: Path, catalog: dict, stats: dict, base_url: str
) -> dict[str, int]:
    """Write idempotent metadata without altering catalog inputs or visible page UI.

    Call after generated JSON and authored pages/assets are in their final location.
    A project-path robots.txt is informational; only an origin-root robots.txt controls
    crawler access. Sitemap entries intentionally exclude API JSON and redirect pages.
    """
    root = Path(output_root)
    base = _base_url(base_url)
    releases, tracks = _counts(catalog, stats)
    home = base + "/"
    dataset = {
        "@type": "Dataset",
        "@id": home + "#dataset",
        "name": "Anime Subtitles Kazakh — ikymory",
        "description": (
            f"{releases:,} release entries and {tracks:,} usable subtitle tracks. "
            + _EN_DESCRIPTION
            + " Release entries are not distinct anime; track counts do not establish "
            "complete episode or series coverage. Metadata and episode numbering "
            "remain unverified. No video or audio is hosted."
        ),
        "inLanguage": "kk",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {
            "@type": "Person",
            "name": "ikymory",
            "url": "https://github.com/ikymory",
        },
        "sameAs": "https://github.com/ikymory/anime-subtitles-kazakh",
        "keywords": ["Kazakh subtitles", "қазақша аниме субтитрлер", "SRT", "WebVTT"],
        "measurementTechnique": (
            "Automated subtitle parsing and canonical track manifests; "
            "structural validation does not establish linguistic accuracy."
        ),
    }
    graph = [dataset]
    if (root / "index.html").is_file():
        dataset["url"] = home
        graph.extend(
            [
                {
                    "@type": "WebSite",
                    "@id": home + "#website",
                    "url": home,
                    "name": "Anime Subtitles Kazakh — ikymory",
                    "inLanguage": ["kk", "en", "ja"],
                    "description": _EN_DESCRIPTION,
                },
                {
                    "@type": "CollectionPage",
                    "@id": home + "#catalog-page",
                    "url": home,
                    "name": _TITLE,
                    "inLanguage": "kk",
                    "isPartOf": {"@id": home + "#website"},
                    "mainEntity": {"@id": home + "#dataset"},
                },
            ]
        )
    if (root / "api/v1/anime.json").is_file():
        dataset["distribution"] = [
            {
                "@type": "DataDownload",
                "name": "Release catalog and available-track metadata",
                "encodingFormat": "application/json",
                "contentUrl": base + "/api/v1/anime.json",
            }
        ]
    reports = [
        {"@type": "CreativeWork", "name": name, "url": base + "/" + relative}
        for relative, name in (
            ("api/v1/stats.json", "Measured coverage statistics"),
            ("api/v1/audit.json", "Automated findings requiring review"),
        )
        if (root / relative).is_file()
    ]
    if reports:
        dataset["subjectOf"] = reports
    schema = (
        json.dumps(
            {"@context": "https://schema.org", "@graph": graph},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    sitemap = Element("urlset", {"xmlns": namespace})
    pages = [
        relative
        for relative in ("index.html", "api.html")
        if (root / relative).is_file()
    ]
    for relative in pages:
        SubElement(SubElement(sitemap, "url"), "loc").text = (
            home if relative == "index.html" else base + "/" + relative
        )
    indent(sitemap, space="  ")
    robots = (
        "# Crawler rules are effective only at the origin root /robots.txt.\n"
        "# GitHub Pages project paths cannot configure the origin root.\n"
        "User-agent: *\n"
        f"Allow: {urlsplit(home).path}\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    outputs = {
        root / "robots.txt": robots.encode("utf-8"),
        root / "sitemap.xml": tostring(sitemap, encoding="utf-8", xml_declaration=True)
        + b"\n",
        root / "discovery.jsonld": schema.encode("utf-8"),
    }
    index = root / "index.html"
    if index.is_file():
        outputs[index] = _refresh_head(
            index.read_bytes().decode("utf-8"), _html_metadata(root, base, schema)
        ).encode("utf-8")
    root.mkdir(parents=True, exist_ok=True)
    for path, payload in outputs.items():
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
    return {"sitemap_pages": len(pages), "schema_entities": len(graph)}
