#!/usr/bin/env python3
"""Audit the public OPML without network requests or changing its organization."""
from __future__ import annotations

import argparse
import collections
import json
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def safe_public_url(url: str) -> bool:
    """Reject clearly unsafe OPML URLs before they reach the public collector.

    This is a static validation only. The collector separately validates DNS
    addresses on every request and redirect; this code does not make DNS calls.
    """
    if not isinstance(url, str) or not url or any(
        ch.isspace() or ord(ch) < 32 or ord(ch) == 127 or ch == '\\'
        for ch in url
    ):
        return False
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password):
            return False
        _ = parsed.port
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname in ("localhost", "localhost.localdomain") or hostname.endswith(
            (".localhost", ".local", ".internal")
        ):
            return False
        try:
            return ipaddress.ip_address(hostname).is_global
        except ValueError:
            return True  # DNS is verified by the collector, not by this audit.
    except ValueError:
        return False


def audit(path: Path) -> dict:
    root = ET.parse(path).getroot()
    if root.tag.lower() != "opml":
        raise ValueError("Documento OPML inválido")
    body = root.find("body")
    if body is None:
        raise ValueError("Falta body en OPML")
    categories = []
    seen = {}
    problems = []
    totals = collections.Counter()
    for section in body.findall("outline"):
        category = section.get("text") or section.get("title") or ""
        categories.append(category)
        for node in section.iter("outline"):
            url = (node.get("xmlUrl") or "").strip()
            if not url:
                continue
            name = (node.get("title") or node.get("text") or "").strip()
            parsed = urlsplit(url)
            totals[category] += 1
            if not name:
                problems.append({"category": category, "url": url, "issue": "missing-name"})
            if not safe_public_url(url):
                problems.append({"category": category, "url": url, "issue": "invalid-feed-url"})
            if url in seen:
                problems.append({"category": category, "url": url, "issue": "duplicate-url", "first_category": seen[url]})
            else:
                seen[url] = category
            website = node.get("htmlUrl", "").strip()
            if website and not safe_public_url(website):
                problems.append({"category": category, "url": url, "issue": "invalid-website"})
    return {"feed_count": sum(totals.values()), "unique_feed_count": len(seen),
            "categories": dict(totals), "category_count": len(categories),
            "problems": problems, "problem_count": len(problems)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditar catálogo OPML sin consultar sitios externos")
    parser.add_argument("--opml", type=Path, default=Path("sources/feeds.opml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit(args.opml)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['feed_count']} fuentes en {result['category_count']} carpetas · {result['problem_count']} problemas")
        for issue in result["problems"]:
            print(f"- {issue['issue']}: {issue['url']}")
    return 1 if result["problem_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
