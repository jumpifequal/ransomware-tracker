"""
Purpose: shared HTTPS transport and deterministic response normalization for REST and OSINT helpers.
When used: imported by each source-specific helper before invoking an allow-listed public endpoint.
Why it exists: centralizes bounded retries, response-size limits, JSON/RSS/HTML parsing, and machine-readable failures.
Inputs/parameters: trusted HTTPS base URL, validated path/query values, timeout, retry count, and maximum response bytes.
Outputs: a dictionary containing HTTP status, content type, and parsed data.
High-level behavior: performs GET-only HTTPS requests, retries transient failures, parses JSON/RSS when possible, and otherwise extracts bounded HTML metadata and links.
Failure semantics: raises SafeRequestError for validation, transport, HTTP, decoding, or response-size failures; callers serialize the failure as JSON.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any

MAX_RESPONSE_BYTES = 2_000_000
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
BACKOFF_SECONDS = (5, 15)
HEADER_PROFILES = {
    "api": {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
    },
    "rss": {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    },
    "html": {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html, application/xhtml+xml, */*",
    },
}


def headers_for(profile: str) -> dict[str, str]:
    try:
        return dict(HEADER_PROFILES[profile])
    except KeyError as exc:
        raise SafeRequestError(
            "invalid_header_profile",
            f"unsupported header profile: {profile}",
        ) from exc


class SafeRequestError(Exception):
    def __init__(
        self,
        kind: str,
        message: str,
        status: int | None = None,
        body: str | None = None,
    ):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.message = message
        self.body = body


class HtmlMetadataParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self.metadata: dict[str, str] = {}
        self._href: str | None = None
        self._text: list[str] = []
        self._title_open = False
        self._title: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        lowered = tag.lower()
        values = {key.lower(): value for key, value in attrs if key}

        if lowered == "a":
            href = values.get("href")
            if href:
                self._href = urllib.parse.urljoin(self.base_url, href)
                self._text = []
            return

        if lowered == "title":
            self._title_open = True
            self._title = []
            return

        if lowered == "meta":
            key = (
                values.get("property")
                or values.get("name")
                or values.get("itemprop")
            )
            content = values.get("content")
            if key and content:
                self.metadata[key.lower()] = " ".join(content.split())[:4000]
            return

        if lowered == "link":
            rel = (values.get("rel") or "").lower()
            href = values.get("href")
            if href and "canonical" in rel:
                self.metadata["canonical"] = urllib.parse.urljoin(
                    self.base_url,
                    href,
                )

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)
        if self._title_open:
            self._title.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "a" and self._href:
            title = " ".join("".join(self._text).split())
            if title and self._href.startswith("https://"):
                self.links.append(
                    {"title": title[:500], "url": self._href}
                )
            self._href = None
            self._text = []
        elif lowered == "title":
            title = " ".join("".join(self._title).split())
            if title:
                self.metadata.setdefault("title", title[:1000])
            self._title_open = False
            self._title = []


def retry_delay_seconds(
    status: int | None,
    attempt: int,
    retry_after: str | None = None,
    body: str | None = None,
) -> int:
    """Return a bounded, source-safe retry delay for transient failures."""
    if status == 429:
        if retry_after:
            try:
                seconds = int(retry_after.strip())
                if 1 <= seconds <= 300:
                    return seconds + 2
            except ValueError:
                pass

        lowered = (body or "").casefold()
        if "1 per 1 minute" in lowered or "per 1 minute" in lowered:
            return 65

        return 65

    if attempt < len(BACKOFF_SECONDS):
        return BACKOFF_SECONDS[attempt]
    return BACKOFF_SECONDS[-1]


def _read_limited(response: Any, max_bytes: int) -> bytes:
    data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise SafeRequestError(
            "response_too_large",
            f"response exceeded {max_bytes} bytes",
        )
    return data


def parse_rss(body: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(body)
    items: list[dict[str, str]] = []
    candidates = root.findall(".//item")
    if not candidates:
        candidates = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    def node_text(item: Any, names: list[str]) -> str:
        for name in names:
            node = item.find(name)
            if node is None:
                continue
            if node.text:
                return " ".join(node.text.split())
            href = node.attrib.get("href")
            if href:
                return href
        return ""

    for item in candidates[:100]:
        items.append(
            {
                "title": node_text(
                    item,
                    ["title", "{http://www.w3.org/2005/Atom}title"],
                ),
                "link": node_text(
                    item,
                    ["link", "{http://www.w3.org/2005/Atom}link"],
                ),
                "published": node_text(
                    item,
                    [
                        "pubDate",
                        "published",
                        "{http://www.w3.org/2005/Atom}published",
                        "{http://www.w3.org/2005/Atom}updated",
                    ],
                ),
                "summary": node_text(
                    item,
                    [
                        "description",
                        "summary",
                        "{http://www.w3.org/2005/Atom}summary",
                    ],
                )[:4000],
            }
        )
    return items


def parse_html(body: bytes, url: str) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace")
    parser = HtmlMetadataParser(url)
    parser.feed(text)

    metadata = parser.metadata
    article = {
        "title": (
            metadata.get("og:title")
            or metadata.get("twitter:title")
            or metadata.get("title")
            or ""
        ),
        "description": (
            metadata.get("og:description")
            or metadata.get("description")
            or metadata.get("twitter:description")
            or ""
        ),
        "published": (
            metadata.get("article:published_time")
            or metadata.get("datepublished")
            or metadata.get("date")
            or ""
        ),
        "canonical": metadata.get("canonical", ""),
    }

    return {
        "article": article,
        "links": parser.links[:100],
        "html_excerpt": text[:12000],
    }


def get(
    base_url: str,
    path: str,
    query: dict[str, Any] | None = None,
    timeout: int = 20,
    retries: int = 3,
    max_bytes: int = MAX_RESPONSE_BYTES,
    profile: str = "api",
) -> dict[str, Any]:
    if not base_url.startswith("https://"):
        raise SafeRequestError(
            "invalid_base_url",
            "only HTTPS base URLs are allowed",
        )
    if not path.startswith("/"):
        raise SafeRequestError(
            "invalid_path",
            "path must start with '/'",
        )
    if retries < 1 or retries > 3:
        raise SafeRequestError(
            "invalid_retries",
            "retries must be between 1 and 3",
        )

    url = urllib.parse.urljoin(
        base_url.rstrip("/") + "/",
        path.lstrip("/"),
    )
    if query:
        encoded = urllib.parse.urlencode(
            {key: value for key, value in query.items() if value is not None}
        )
        if encoded:
            url += "?" + encoded

    last_error: SafeRequestError | None = None

    for attempt in range(retries):
        retry_after = None
        request = urllib.request.Request(
            url,
            method="GET",
            headers=headers_for(profile),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                content_type = (
                    response.headers.get("Content-Type") or ""
                ).split(";")[0].strip().lower()
                body = _read_limited(response, max_bytes)

                if "json" in content_type:
                    try:
                        data = json.loads(body.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise SafeRequestError(
                            "invalid_json",
                            str(exc),
                            status,
                        ) from exc
                    return {
                        "status": status,
                        "content_type": content_type,
                        "data": data,
                    }

                if "xml" in content_type or body.lstrip().startswith(b"<?xml"):
                    try:
                        data = {"items": parse_rss(body)}
                    except ET.ParseError as exc:
                        raise SafeRequestError(
                            "invalid_xml",
                            str(exc),
                            status,
                        ) from exc
                    return {
                        "status": status,
                        "content_type": content_type,
                        "data": data,
                    }

                return {
                    "status": status,
                    "content_type": content_type or "text/html",
                    "data": parse_html(body, url),
                }

        except urllib.error.HTTPError as exc:
            error_body = exc.read(8192).decode("utf-8", errors="replace")
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            last_error = SafeRequestError(
                "http_error",
                f"HTTP {exc.code}",
                int(exc.code),
                error_body,
            )
            if exc.code not in TRANSIENT_STATUS:
                raise last_error
        except urllib.error.URLError as exc:
            last_error = SafeRequestError(
                "network_error",
                str(exc.reason),
            )
        except TimeoutError as exc:
            last_error = SafeRequestError(
                "timeout",
                str(exc),
            )

        if attempt < retries - 1:
            retry_after_value = locals().get("retry_after")
            delay = retry_delay_seconds(
                last_error.status if last_error else None,
                attempt,
                retry_after_value,
                last_error.body if last_error else None,
            )
            time.sleep(delay)

    if last_error is None:
        raise SafeRequestError(
            "unknown_error",
            "request failed without a captured error",
        )
    raise last_error
