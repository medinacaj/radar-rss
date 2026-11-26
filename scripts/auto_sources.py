#!/usr/bin/env python3
"""Feed eligibility shared by admission and every hourly AUTO ingestion.

No collector imports: curated collection keeps its existing transport and rules.
"""
from __future__ import annotations

from calendar import timegm
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

try:
    import feedparser
except ModuleNotFoundError:
    import feedparser_compat as feedparser
from safe_publisher import MAX_BYTES, FetchError, SafeFetcher, UnsafeURL, checked_url

AUTO_SECONDS = 12
AUTO_REQUESTS = 8
SPANISH = frozenset(('el la los las un una unos unas de del al en para por con sin que como '
                     'se su sus es son mas nuevos nuevas nuevo nueva sobre entre desde hasta '
                     'segun tras hacia ante durante y o este esta estos estas mejora anuncia '
                     'inversion educacion investigacion tecnologia economia gestion').split())


class RejectedFeed(ValueError):
    """Document fails reproducible feed/content checks."""


def fold(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


class PlainTitle(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignore += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.ignore:
            self.ignore -= 1

    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data)


def entry_date(entry):
    for key in ('published_parsed', 'updated_parsed', 'created_parsed'):
        if entry.get(key):
            try:
                return datetime.fromtimestamp(timegm(entry[key]), timezone.utc)
            except (ValueError, OverflowError, TypeError):
                pass
    for key in ('published', 'updated'):
        try:
            dt = parsedate_to_datetime(entry.get(key, ''))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except (TypeError, ValueError, IndexError):
            pass
    return None


def xml_root(raw: bytes):
    if (len(raw) > MAX_BYTES or b'\x00' in raw
            or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper()):
        raise RejectedFeed('XML excesivo o con entidades')
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RejectedFeed('XML inválido') from exc
    if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed',
                        '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'):
        raise RejectedFeed('No es RSS/Atom')
    return root


def eligible_entries(raw: bytes, rule: dict, publisher: str, now: datetime, *, verify_host=None):
    xml_root(raw)
    parsed = feedparser.parse(raw)
    seen_titles, seen_links, checked_hosts = set(), set(), {}
    usable = spanish = relevant = 0
    eligible = []
    days = 730 if rule.get('days') == 730 else 45
    cutoff = now-timedelta(days=days)
    for entry in parsed.entries[:60]:
        text = PlainTitle()
        text.feed(str(entry.get('title', '')))
        title = re.sub(r'\s+', ' ', ' '.join(text.parts)).strip()[:290]
        normalized = fold(title)
        date = entry_date(entry)
        try:
            link = checked_url(entry.get('link', ''), publisher)
            if verify_host:
                host = urlsplit(link).hostname
                if host not in checked_hosts:
                    try:
                        verify_host(host)
                        checked_hosts[host] = True
                    except UnsafeURL:
                        checked_hosts[host] = False
                if not checked_hosts[host]:
                    continue
        except UnsafeURL:
            continue
        if (len(title) < 18 or not date or not cutoff <= date <= now+timedelta(hours=6)
                or normalized in seen_titles or link in seen_links):
            continue
        seen_titles.add(normalized)
        seen_links.add(link)
        usable += 1
        words = set(re.findall(r'[a-z]+', normalized))
        is_spanish = len(words & SPANISH) >= 2
        spanish += is_spanish
        matches = any(re.search(r'(?<!\w)'+re.escape(fold(term))+r'(?!\w)', normalized)
                      for term in rule['terms'])
        relevant += bool(is_spanish and matches)
        if is_spanish and matches:
            eligible.append(entry)
    if usable < 3 or spanish / usable < .6 or relevant < 2 or relevant / usable < .5:
        raise RejectedFeed('Pocos titulares recientes en español o pertinencia insuficiente')
    evidence = {'usable_headlines': usable, 'spanish_headlines': spanish, 'relevant_headlines': relevant,
                'window_days': days}
    return eligible, evidence


def validate_feed(raw: bytes, rule: dict, publisher: str, now: datetime, *, verify_host=None) -> dict:
    return eligible_entries(raw, rule, publisher, now, verify_host=verify_host)[1]


@lru_cache(maxsize=1)
def category_policy():
    return json.loads((Path(__file__).resolve().parents[1]/'sources/discovery-policy.json').read_text())['categories']


def current_entries(source: dict, now: datetime):
    publisher = urlsplit(checked_url(source['website'])).hostname
    url = checked_url(source['url'], publisher)
    rule = category_policy().get(source['category'])
    if rule is None:
        raise RejectedFeed('Categoría AUTO sin política de validación')
    fetcher = SafeFetcher(seconds=AUTO_SECONDS, max_requests=AUTO_REQUESTS, exchange_seconds=6)
    raw = fetcher.get(url, publisher=publisher)
    entries, _ = eligible_entries(raw, rule, publisher, now, verify_host=fetcher.verify_article_host)
    fetcher.check_time()
    return entries
