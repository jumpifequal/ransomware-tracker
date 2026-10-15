"""
Purpose: diagnose DNS and outbound-network failures without treating alternate DNS as an operational bypass.
When used: only when multiple source helpers fail at DNS/egress or when transport behavior is ambiguous.
Why it exists: separates source availability from system-resolver failure and broader runtime egress restrictions.
Inputs/parameters: one or more hostnames plus optional public resolver IP and timeout.
Outputs: JSON report containing system DNS results, optional direct resolver probes, and an aggregate runtime diagnosis.
High-level behavior: tests the system resolver for each hostname; optionally probes the configured public resolver over UDP/TCP 53; never substitutes returned IPs into source requests.
Failure semantics: probe failures are reported as diagnostic evidence only and never converted directly into source UNAVAILABLE states.
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
from typing import Any


def _dns_query(name: str, txid: int = 0x4242) -> bytes:
    header = struct.pack("!HHHHHH", txid, 0x0100, 1, 0, 0, 0)
    qname = b"".join(
        bytes([len(label)]) + label.encode("ascii")
        for label in name.rstrip(".").split(".")
    ) + b"\x00"
    return header + qname + struct.pack("!HH", 1, 1)


def system_dns(hostname: str) -> dict[str, Any]:
    try:
        addresses = sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
            }
        )
        return {"ok": True, "addresses": addresses}
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }


def public_dns_probe(
    hostname: str,
    resolver: str = "8.8.8.8",
    timeout: float = 3.0,
) -> dict[str, Any]:
    query = _dns_query(hostname)
    result: dict[str, Any] = {
        "resolver": resolver,
        "udp53": {"ok": False},
        "tcp53": {"ok": False},
    }

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp.settimeout(timeout)
        udp.sendto(query, (resolver, 53))
        packet, peer = udp.recvfrom(4096)
        result["udp53"] = {
            "ok": True,
            "peer": f"{peer[0]}:{peer[1]}",
            "bytes": len(packet),
        }
    except Exception as exc:
        result["udp53"] = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    finally:
        udp.close()

    try:
        with socket.create_connection((resolver, 53), timeout=timeout) as tcp:
            tcp.sendall(struct.pack("!H", len(query)) + query)
            prefix = tcp.recv(2)
            if len(prefix) != 2:
                raise RuntimeError("missing DNS TCP length prefix")
            expected = struct.unpack("!H", prefix)[0]
            body = bytearray()
            while len(body) < expected:
                chunk = tcp.recv(expected - len(body))
                if not chunk:
                    break
                body.extend(chunk)
            result["tcp53"] = {
                "ok": len(body) == expected,
                "bytes": len(body),
            }
    except Exception as exc:
        result["tcp53"] = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    return result


def classify_runtime(
    system_results: list[dict[str, Any]],
    public_probe: dict[str, Any] | None = None,
) -> str:
    attempted = [item for item in system_results if "ok" in item]
    failures = [item for item in attempted if not item.get("ok")]

    if attempted and not failures:
        return "SYSTEM_DNS_OK"

    if len(failures) >= 2:
        if public_probe is not None:
            udp_ok = bool(public_probe.get("udp53", {}).get("ok"))
            tcp_ok = bool(public_probe.get("tcp53", {}).get("ok"))
            if not udp_ok and not tcp_ok:
                return "RUNTIME_WIDE_DNS_OR_EGRESS_RESTRICTION"
            return "SYSTEM_RESOLVER_FAILURE"
        return "POSSIBLE_RUNTIME_WIDE_DNS_FAILURE"

    if failures:
        return "HOST_OR_RESOLVER_FAILURE"

    return "INSUFFICIENT_EVIDENCE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hostnames", nargs="+")
    parser.add_argument("--public-resolver", default="8.8.8.8")
    parser.add_argument("--probe-public-dns", action="store_true")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    host_results = [
        {"hostname": hostname, **system_dns(hostname)}
        for hostname in args.hostnames
    ]

    public_result = None
    if args.probe_public_dns:
        public_result = public_dns_probe(
            args.hostnames[0],
            resolver=args.public_resolver,
            timeout=args.timeout,
        )

    print(
        json.dumps(
            {
                "hosts": host_results,
                "public_dns": public_result,
                "runtime_state": classify_runtime(host_results, public_result),
                "operational_bypass": False,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
