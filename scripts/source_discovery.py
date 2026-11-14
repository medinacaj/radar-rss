#!/usr/bin/env python3
"""Bounded, deterministic discovery of Spanish public publisher RSS/Atom feeds.

Public state is derived build data, never a change to curated subscriptions.
AUTO denotes technical/heuristic validation, not editorial or fact verification.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit
import xml.etree.ElementTree as ET

from collect import iso, parse_opml
from safe_publisher import (BudgetExceeded, FetchError, UnsafeURL, SafeFetcher,
                            PinnedHTTPSConnection, checked_url, publisher_key, resolve_public)
from auto_sources import RejectedFeed, xml_root, validate_feed
from site_config import DATA_URL

INTERVAL = timedelta(hours=48)
MAX_VALIDATION_AGE = timedelta(days=90)
MAX_ADDITIONS = 5
MAX_SOURCES = 100
MAX_PUBLISHERS = 22
MAX_FEEDS_PER_PUBLISHER = 2
MAX_REQUESTS = 100
MAX_SECONDS = 180
MAX_BYTES = 1_000_000
MAX_STATE_BYTES = 250_000
REVALIDATE = 5
METHOD = 'publisher-homepage-rss-autodiscovery'
PUBLIC_STATE_URL = DATA_URL+'discovered-sources.json'

def seed_url(rule: dict) -> str:
    return 'https://news.google.com/rss/search?' + urlencode({
        'q': rule['query'], 'hl': 'es-419', 'gl': 'CL', 'ceid': 'CL:es-419'})


class FeedLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if (tag.lower() == 'link' and 'alternate' in (values.get('rel') or '').lower().split()
                and (values.get('type') or '').lower().split(';')[0] in
                ('application/rss+xml', 'application/atom+xml') and values.get('href')):
            self.links.append(values['href'])


def cleaned_sources(state: dict, policy: dict, now: datetime | None = None, *, check_seed: bool = True) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    sources, urls, covered = [], set(), set()
    for row in (state.get('sources') or [])[:MAX_SOURCES] if isinstance(state.get('sources', []), list) else []:
        try:
            if not isinstance(row, dict) or row.get('category') not in policy:
                continue
            homepage = checked_url(row['website'])
            publisher = urlsplit(homepage).hostname
            url = checked_url(row['url'], publisher)
            key = (publisher_key(publisher), row['category'])
            if url in urls or key in covered or row['id'] != sha256(url.encode()).hexdigest()[:16]:
                continue
            provenance = row['provenance']
            if (provenance.get('method') != METHOD or provenance.get('publisher') != publisher
                    or (check_seed and provenance.get('seed_url') != seed_url(policy[row['category']]))
                    or not 3 <= provenance.get('usable_headlines', 0) <= 60):
                continue
            seed = checked_url(provenance['seed_url'], 'news.google.com')
            if urlsplit(seed).path != '/rss/search':
                continue
            accepted = datetime.fromisoformat(row['accepted_at'].replace('Z', '+00:00'))
            validated = datetime.fromisoformat(row['validated_at'].replace('Z', '+00:00'))
            if (not accepted.tzinfo or not validated.tzinfo or not accepted <= validated <= now+timedelta(minutes=5)
                    or validated < now-MAX_VALIDATION_AGE):
                continue
            sources.append({'id': row['id'], 'name': 'AUTO — '+str(row['name']).removeprefix('AUTO — ')[:100],
                            'category': row['category'], 'url': url, 'website': homepage,
                            'accepted_at': row['accepted_at'], 'validated_at': row['validated_at'],
                            'provenance': {k: provenance[k] for k in
                                           ('method', 'seed_url', 'publisher', 'usable_headlines')}})
            urls.add(url)
            covered.add(key)
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    return sources


def load_state(path: Path, policy: dict, *, now: datetime | None = None) -> dict:
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError('Estado demasiado grande')
        state = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            raise ValueError('Estado inválido')
    except (OSError, ValueError):
        state = {}
    return sanitize_state(state, policy, now)


def sanitize_state(state: dict, policy: dict, now: datetime | None = None) -> dict:
    result = {**{key: state.get(key) for key in ('last_checked_at', 'next_category', 'next_revalidation')},
              'version': 1, 'sources': cleaned_sources(state, policy, now)}
    if state.get('recovery_pending') is True:
        result['recovery_pending'] = True
    scan = state.get('last_scan')
    if isinstance(scan, dict):
        result['last_scan'] = {key: min(1000, max(0, scan[key])) for key in
                               ('added', 'seed_folders', 'candidate_publishers', 'errors', 'seed_successes',
                                'seed_errors', 'publisher_errors', 'robots_denials', 'rejected_feeds')
                               if isinstance(scan.get(key), int)}
        result['last_scan']['method'] = METHOD
        result['last_scan']['network_unavailable'] = bool(scan.get('network_unavailable'))
        if scan.get('outcome') in ('unavailable', 'partial', 'added', 'no_eligible_sources'):
            result['last_scan']['outcome'] = scan['outcome']
    return result


def valid_registry(doc: dict, policy: dict, now: datetime) -> bool:
    try:
        if (not isinstance(doc, dict) or doc.get('version') != 1 or not isinstance(doc.get('sources'), list)
                or len(doc['sources']) > MAX_SOURCES or len(cleaned_sources(doc, policy, now)) != len(doc['sources'])):
            return False
        stamp = datetime.fromisoformat(doc['last_checked_at'].replace('Z', '+00:00'))
        return stamp.tzinfo is not None and stamp <= now+timedelta(minutes=5)
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def recover_state(path: Path, policy: dict, now: datetime, *, fetcher=None) -> dict:
    """Cache fallback is confined to the repository's single trusted public URL."""
    cached = load_state(path, policy, now=now)
    try:
        raw = path.read_bytes() if path.stat().st_size <= MAX_STATE_BYTES else b''
        doc = json.loads(raw)
        if valid_registry(doc, policy, now) and not doc.get('recovery_pending'):
            return cached  # Never replace a valid cache, including a newer one.
    except (OSError, ValueError):
        pass
    cached['recovery_pending'] = True
    try:
        transport = fetcher if fetcher is not None else SafeFetcher(seconds=8, max_requests=4, exchange_seconds=6)
        raw = transport.get(PUBLIC_STATE_URL, publisher=urlsplit(DATA_URL).hostname, limit=MAX_STATE_BYTES)
        if len(raw) > MAX_STATE_BYTES:
            raise ValueError('Registro publicado demasiado grande')
        doc = json.loads(raw)
        if not valid_registry(doc, policy, now):
            raise ValueError('Registro publicado inválido')
        # Use the same sanitization as a local cache, without writing an
        # unvalidated response or introducing a second schema.
        restored = dict(sanitize_state(doc, policy, now), recovery_pending=False)
        print(f"Registro AUTO recuperado de Pages: {len(restored['sources'])} fuentes")
        return restored
    except FetchError as exc:
        if exc.reason == 'http_404':
            cached['recovery_pending'] = False
            print('Pages aún no publica registro AUTO (404); se inicia con las fuentes curadas.')
        else:
            print('Registro AUTO publicado no disponible; se conserva el estado local y se reintentará recuperar.')
    except (ValueError, TypeError):
        print('Registro AUTO publicado inválido; se conserva el estado local y se reintentará recuperar.')
    return cached


def covered_publishers(sources: list[dict]) -> set[tuple[str, str]]:
    return {(publisher_key(urlsplit(s.get('website') or s['url']).hostname or ''), s['category'])
            for s in sources if publisher_key(urlsplit(s.get('website') or s['url']).hostname or '') != 'news.google.com'}


def discover(curated: list[dict], policy: dict, state: dict, fetcher, now: datetime) -> dict:
    result = deepcopy(state)
    result.update(version=1, sources=cleaned_sources(state, policy, now))
    try:
        checked = datetime.fromisoformat(str(state.get('last_checked_at')).replace('Z', '+00:00'))
        if now-INTERVAL < checked <= now:
            return result
    except (ValueError, TypeError):
        pass
    result['last_checked_at'] = iso(now)
    categories = list(policy)
    if not categories:
        return result
    offset = state.get('next_category')
    offset = offset % len(categories) if isinstance(offset, int) else 0
    categories = categories[offset:]+categories[:offset]
    result['next_category'] = (offset+1) % len(categories)
    candidates, errors = [], 0
    seed_successes = seed_errors = publisher_errors = robots_denials = rejected_feeds = 0
    existing_publishers = covered_publishers(curated+result['sources'])
    # Always investigate every folder before spending the admission quota.
    for category in categories:
        try:
            seed = seed_url(policy[category])
            root = xml_root(fetcher.get(seed, publisher='news.google.com'))
            seed_successes += 1
            seen = set()
            for node in root.iter('source'):
                try:
                    homepage = checked_url(node.get('url') or '')
                    host = urlsplit(homepage).hostname
                    publisher = publisher_key(host)
                    if (publisher in seen or publisher == 'news.google.com'
                            or (publisher, category) in existing_publishers):
                        continue
                    seen.add(publisher)
                    candidates.append((category, f'https://{host}/', (node.text or host).strip()[:100], seed))
                except UnsafeURL:
                    continue
                if len(seen) >= 2:
                    break
        except (FetchError, RejectedFeed) as exc:
            errors += 1
            seed_errors += 1
            robots_denials += getattr(exc, 'reason', None) == 'robots'
    # Revalidate a rotating bounded slice, preserving acceptance on network failures.
    prior = result['sources']
    cursor = state.get('next_revalidation')
    cursor = cursor % len(prior) if isinstance(cursor, int) and prior else 0
    checked_sources = (prior[cursor:]+prior[:cursor])[:REVALIDATE]
    result['next_revalidation'] = (cursor+REVALIDATE) % max(1, len(prior))
    for source in checked_sources:
        try:
            raw = fetcher.get(source['url'], publisher=source['provenance']['publisher'])
            evidence = validate_feed(raw, policy[source['category']], source['provenance']['publisher'], now,
                                     verify_host=getattr(fetcher, 'verify_article_host', None))
            source['validated_at'] = iso(now)
            source['provenance']['usable_headlines'] = evidence['usable_headlines']
        except (UnsafeURL, RejectedFeed):
            result['sources'].remove(source)
            rejected_feeds += 1
        except FetchError as exc:
            errors += 1
            robots_denials += exc.reason == 'robots'
    all_sources = curated+result['sources']
    urls = {checked_url(s['url']) for s in all_sources if s.get('url', '').startswith('https://')}
    covered = covered_publishers(all_sources)
    added = 0
    for category, homepage, name, seed in candidates[:MAX_PUBLISHERS]:
        if added >= MAX_ADDITIONS or len(result['sources']) >= MAX_SOURCES:
            break
        host = urlsplit(homepage).hostname
        key = (publisher_key(host), category)
        if key in covered:
            continue
        try:
            links = FeedLinks()
            links.feed(fetcher.get(homepage, publisher=host, limit=256_000).decode('utf-8', errors='replace'))
            feed_urls = []
            for href in links.links[:20]:
                try:
                    url = checked_url(urljoin(homepage, href), host)
                    if url not in urls and url not in feed_urls:
                        feed_urls.append(url)
                except UnsafeURL:
                    continue
            for url in feed_urls[:MAX_FEEDS_PER_PUBLISHER]:
                try:
                    evidence = validate_feed(fetcher.get(url, publisher=host), policy[category], host, now,
                                             verify_host=getattr(fetcher, 'verify_article_host', None))
                except RejectedFeed:
                    rejected_feeds += 1
                    continue
                source = {'id': sha256(url.encode()).hexdigest()[:16], 'name': 'AUTO — '+name,
                          'category': category, 'url': url, 'website': homepage,
                          'accepted_at': iso(now), 'validated_at': iso(now),
                          'provenance': {'method': METHOD, 'seed_url': seed, 'publisher': host,
                                         'usable_headlines': evidence['usable_headlines']}}
                result['sources'].append(source)
                urls.add(url)
                covered.add(key)
                added += 1
                break
        except (FetchError, ValueError) as exc:
            errors += 1
            publisher_errors += 1
            robots_denials += getattr(exc, 'reason', None) == 'robots'
    outcome = ('unavailable' if not seed_successes else 'partial' if seed_errors or publisher_errors
               else 'added' if added else 'no_eligible_sources')
    result['last_scan'] = {'added': added, 'seed_folders': len(categories),
                           'seed_successes': seed_successes, 'seed_errors': seed_errors,
                           'publisher_errors': publisher_errors, 'robots_denials': robots_denials,
                           'rejected_feeds': rejected_feeds, 'outcome': outcome,
                           'candidate_publishers': min(len(candidates), MAX_PUBLISHERS),
                           'errors': errors, 'method': METHOD,
                           'network_unavailable': bool(getattr(fetcher, 'proxy_configured', False))}
    return result


def write_runtime_opml(curated_path: Path, state: dict, output: Path, *, now: datetime | None = None):
    tree = ET.parse(curated_path)
    body = tree.getroot().find('body')
    folders = {(node.get('text') or node.get('title')): node for node in body.findall('outline')}
    curated = parse_opml(curated_path)
    urls = {source['url'] for source in curated}
    covered = covered_publishers(curated)
    for source in cleaned_sources(state, {category: {} for category in folders}, now, check_seed=False):
        category = source['category']
        try:
            url = checked_url(source['url'], urlsplit(source['website']).hostname)
        except (UnsafeURL, KeyError):
            continue
        key = (publisher_key(urlsplit(source['website']).hostname), category)
        if category not in folders or url in urls or key in covered:
            continue
        ET.SubElement(folders[category], 'outline', {'text': source['name'], 'title': source['name'],
                      'type': 'rss', 'xmlUrl': url, 'htmlUrl': source['website'], 'radarAuto': 'validated-v1'})
        urls.add(url)
        covered.add(key)
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opml', type=Path, default=Path('sources/feeds.opml'))
    parser.add_argument('--policy', type=Path, default=Path('sources/discovery-policy.json'))
    parser.add_argument('--state', type=Path, default=Path('web/data/discovered-sources.json'))
    parser.add_argument('--runtime-opml', type=Path, required=True)
    parser.add_argument('--recover-published', action='store_true', help='Recuperar registro AUTO de Pages si falta la cache')
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding='utf-8'))['categories']
    curated = parse_opml(args.opml)
    if set(policy) != {source['category'] for source in curated}:
        raise ValueError('La política debe cubrir todas las carpetas del catálogo')
    now = datetime.now(timezone.utc)
    state = recover_state(args.state, policy, now) if args.recover_published else load_state(args.state, policy, now=now)
    result = discover(curated, policy, state, SafeFetcher(), now)
    if result.get('last_scan', {}).get('network_unavailable'):
        print('Proxy configurado: no se intenta conexión directa; se conserva el catálogo validado vigente.')
    args.state.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.state.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(args.state)
    write_runtime_opml(args.opml, result, args.runtime_opml, now=now)
    print(f"Descubrimiento: {len(result['sources'])} fuentes AUTO; última revisión {result.get('last_checked_at')}")
    print('Última revisión:', json.dumps(result.get('last_scan', {}), ensure_ascii=False))


if __name__ == '__main__':
    main()
