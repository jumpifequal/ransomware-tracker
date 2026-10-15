"""
Purpose: diagnose DNS, HTTPS reachability, request-profile behavior, and content type for a configured source.
When used: run manually in the deployment/runtime environment when a source helper behaves differently from a raw browser or curl request.
Why it exists: distinguishes DNS/egress failures from request-profile, endpoint, and source-specific HTTP behavior.
Inputs/parameters: source name plus optional operation/value.
Outputs: one JSON object describing DNS status and one or more HTTP probes.
High-level behavior: resolves the source host, builds the same allow-listed URL used by the skill, then probes that URL with the configured content profile.
Failure semantics: diagnostic failures are reported as JSON and never interpreted as source absence.
"""
from __future__ import annotations

import argparse
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from _http_common import headers_for
from request_manifest import manifest


SOURCE_PROFILE = {
    "ransomware.live": "api",
    "ransomfeed": "api",
    "ransomlook": "api",
    "bleepingcomputer": "html",
    "cybernews": "html",
    "securityaffairs": "html",
}


def probe(url: str, profile: str) -> dict:
    request = urllib.request.Request(
        url,
        method="GET",
        headers=headers_for(profile),
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            preview = response.read(512).decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": int(response.status),
                "content_type": response.headers.get("Content-Type"),
                "profile": profile,
                "preview": preview[:200],
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": int(exc.code),
            "profile": profile,
            "error": "http_error",
            "preview": body[:200],
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "status": None,
            "profile": profile,
            "error": "network_error",
            "message": str(exc.reason),
        }


def main() -> int:
    parser = argparse.ArgumentParser(prog="diagnose_source.py")
    parser.add_argument("source")
    parser.add_argument("operation")
    parser.add_argument("value", nargs="?")
    parser.add_argument("value2", nargs="?")
    args = parser.parse_args()

    try:
        request = manifest(args.source, args.operation, args.value, args.value2)
    except ValueError as exc:
        print(json.dumps({
            "ok": False,
            "error": {"type": "invalid_input", "message": str(exc)},
        }, ensure_ascii=False, separators=(",", ":")))
        return 2

    url = request["url"]
    host = urllib.parse.urlparse(url).hostname or ""

    try:
        addresses = sorted({
            info[4][0]
            for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        })
        dns = {"ok": True, "addresses": addresses[:4]}
    except OSError as exc:
        dns = {"ok": False, "error": str(exc)}

    profile = SOURCE_PROFILE.get(args.source, "api")
    primary_http = probe(url, profile) if dns["ok"] else None
    alternate_url = request.get("alternate_url")
    alternate_http = None
    if (
        dns["ok"]
        and alternate_url
        and (not primary_http or not primary_http.get("ok"))
    ):
        alternate_profile = "html"
        alternate_http = probe(alternate_url, alternate_profile)

    result = {
        "ok": True,
        "source": args.source,
        "operation": args.operation,
        "url": url,
        "alternate_url": alternate_url,
        "dns": dns,
        "http": primary_http,
        "alternate_http": alternate_http,
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
