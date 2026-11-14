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
import http.client
import ipaddress
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import socket
import ssl
import time
from threading import Thread
import unicodedata
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

from collect import AGENT, entry_date, extract_html, feedparser, iso, parse_opml

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
SPANISH = frozenset(('el la los las un una unos unas de del al en para por con sin que como '
                     'se su sus es son mas nuevos nuevas nuevo nueva sobre entre desde hasta '
                     'segun tras hacia ante durante y o este esta estos estas mejora anuncia '
                     'inversion educacion investigacion tecnologia economia gestion').split())


class FetchError(ValueError):
    """Unavailable or disallowed public endpoint; do not bypass/retry."""
    def __init__(self, message: str, *, reason: str = 'network'):
        super().__init__(message)
        self.reason = reason


class UnsafeURL(FetchError):
    """A URL or DNS answer is outside the permitted public publisher boundary."""


class BudgetExceeded(FetchError):
    """The cycle has exhausted its time or request budget."""


class RejectedFeed(ValueError):
    """Document fails reproducible feed/content checks."""


def fold(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


def publisher_key(host: str) -> str:
    return host.lower().removeprefix('www.')


def checked_url(url: str, publisher: str | None = None) -> str:
    """Strict syntactic boundary; DNS is checked separately when connecting."""
    try:
        if not isinstance(url, str) or len(url) > 2048 or re.search(r'[\s\\\x00-\x1f\x7f]', url):
            raise ValueError('invalid characters')
        parsed = urlsplit(url)
        host = parsed.hostname or ''
        if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or not host or '.' not in host
                or host.endswith('.') or re.search(r'[^a-zA-Z0-9.-]', host)
                or host.lower().endswith(('.local', '.internal', '.localhost', '.test', '.invalid'))):
            raise ValueError('invalid public HTTPS URL')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('literal addresses are not publisher domains')
        if publisher is not None and publisher_key(host) != publisher_key(publisher):
            raise ValueError('different publisher')
        return urlunsplit(('https', host.lower(), parsed.path or '/', parsed.query, ''))
    except (ValueError, TypeError) as exc:
        raise UnsafeURL('URL fuera del dominio público autorizado') from exc


def resolve_public(host: str, timeout: float = 3) -> str:
    # libc DNS has no per-call timeout. A daemon worker cannot hold up the build.
    answers = Queue(maxsize=1)
    def lookup():
        try:
            answers.put((True, socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
        except OSError as exc:
            answers.put((False, exc))
    Thread(target=lookup, daemon=True).start()
    try:
        ok, addresses = answers.get(timeout=timeout)
        if not ok:
            raise FetchError('DNS no disponible')
        if not addresses or not all(ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise UnsafeURL('DNS privado o no público')
        return addresses[0][4][0]
    except (Empty, OSError, ValueError) as exc:
        if isinstance(exc, UnsafeURL):
            raise
        raise FetchError('DNS no disponible') from exc


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a vetted IP; certificate verification and SNI use the domain."""
    def __init__(self, host: str, address: str, timeout: float, context: ssl.SSLContext):
        super().__init__(host, timeout=timeout, context=context)
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def configured_proxy() -> bool:
    return any(os.environ.get(key) for key in
               ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'))


class SafeFetcher:
    def __init__(self):
        self.proxy_configured = configured_proxy()
        self.requests_left = MAX_REQUESTS
        self.deadline = time.monotonic() + MAX_SECONDS
        self.robots: dict[str, RobotFileParser] = {}
        self.last_requested: dict[str, float] = {}
        self.context = ssl.create_default_context()

    def _budget(self):
        if self.proxy_configured or configured_proxy():
            self.proxy_configured = True
            # Direct pinned TLS cannot safely honor an inherited proxy. Never
            # bypass it, disable it or expose its potentially secret URL.
            raise FetchError('Proxy configurado: transporte de descubrimiento no disponible')
        if self.requests_left <= 0 or time.monotonic() >= self.deadline:
            raise BudgetExceeded('Límite de solicitudes o tiempo alcanzado')

    def _request(self, url: str, limit: int) -> tuple[int, dict, bytes]:
        self._budget()
        self.requests_left -= 1
        parsed = urlsplit(checked_url(url))
        address = resolve_public(parsed.hostname, timeout=min(3, max(.01, self.deadline-time.monotonic())))
        self._budget_time()
        connection = PinnedHTTPSConnection(parsed.hostname, address,
                                           min(5, max(.1, self.deadline-time.monotonic())), self.context)
        end = min(self.deadline, time.monotonic() + 8)
        try:
            target = urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
            connection.request('GET', target, headers={'User-Agent': AGENT, 'Accept-Encoding': 'identity',
                                                       'Accept-Language': 'es', 'Accept': '*/*'})
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            if headers.get('content-encoding', 'identity').lower() not in ('identity', ''):
                raise FetchError('Respuesta comprimida no admitida')
            length = headers.get('content-length')
            if length is not None and int(length) > limit:
                raise FetchError('Documento demasiado grande')
            chunks, size = [], 0
            while True:
                remaining = end - time.monotonic()
                if remaining <= 0:
                    raise FetchError('Tiempo de descarga agotado')
                if connection.sock:
                    connection.sock.settimeout(min(3, remaining))
                # read1 returns after one socket read, so a drip-fed body cannot
                # keep resetting socket timeouts inside an unbounded read(n).
                chunk = response.read1(min(16_384, limit-size+1))
                size += len(chunk)
                if size > limit:
                    raise FetchError('Documento demasiado grande')
                if not chunk:
                    break
                chunks.append(chunk)
            return response.status, headers, b''.join(chunks)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            if isinstance(exc, FetchError):
                raise
            raise FetchError('Endpoint público no disponible') from exc
        finally:
            connection.close()

    def _budget_time(self):
        if time.monotonic() >= self.deadline:
            raise BudgetExceeded('Tiempo de revisión agotado')

    def _allowed(self, url: str):
        parsed = urlsplit(url)
        origin = f'https://{parsed.hostname}'
        if origin not in self.robots:
            status, _, raw = self._read(origin+'/robots.txt', parsed.hostname, 64_000, robots=False)
            parser = RobotFileParser()
            if status == 404:
                parser.parse([])
            elif status == 200:
                parser.parse(raw.decode('utf-8', errors='replace').splitlines())
            else:
                raise FetchError('robots.txt no disponible o acceso denegado', reason='robots')
            self.robots[origin] = parser
        parser = self.robots[origin]
        delay = 0
        for agent in ('RadarRSS', AGENT):
            if not parser.can_fetch(agent, url):
                raise FetchError('robots.txt no permite la consulta', reason='robots')
            delay = max(delay, parser.crawl_delay(agent) or 0)
            rate = parser.request_rate(agent)
            if rate and rate.requests > 0:
                delay = max(delay, rate.seconds / rate.requests)
        if time.monotonic() < self.last_requested.get(origin, 0)+delay:
            # Skip instead of waiting or defeating the publisher's crawl policy.
            raise FetchError('robots.txt exige más tiempo entre consultas', reason='robots')

    def _read(self, url: str, publisher: str | None, limit: int, *, robots: bool = True):
        for _ in range(4):
            self._budget()
            url = checked_url(url, publisher)
            if robots:
                self._allowed(url)
            status, headers, raw = self._request(url, limit)
            if robots:
                self.last_requested[f'https://{urlsplit(url).hostname}'] = time.monotonic()
            if status in (301, 302, 303, 307, 308):
                location = headers.get('location')
                if not location:
                    raise FetchError('Redirección sin destino')
                url = urljoin(url, location)
                continue
            return status, headers, raw
        raise FetchError('Demasiadas redirecciones')

    def get(self, url: str, *, publisher: str | None = None, limit: int = MAX_BYTES) -> bytes:
        status, _, raw = self._read(url, publisher, min(limit, MAX_BYTES))
        if status != 200:
            raise FetchError(f'HTTP {status}; no se reintenta ni se sortea el bloqueo')
        return raw


def xml_root(raw: bytes):
    if len(raw) > MAX_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise RejectedFeed('XML excesivo o con entidades')
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RejectedFeed('XML inválido') from exc
    if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed',
                        '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'):
        raise RejectedFeed('No es RSS/Atom')
    return root


def validate_feed(raw: bytes, rule: dict, publisher: str, now: datetime) -> dict:
    xml_root(raw)
    parsed = feedparser.parse(raw)
    seen_titles, seen_links = set(), set()
    usable = spanish = relevant = 0
    days = 730 if rule.get('days') == 730 else 45
    cutoff = now-timedelta(days=days)
    for entry in parsed.entries[:60]:
        title = extract_html(str(entry.get('title', '')))[0].strip()
        normalized = fold(title)
        date = entry_date(entry)
        try:
            link = checked_url(entry.get('link', ''), publisher)
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
    if usable < 3 or spanish / usable < .6 or relevant < 2 or relevant / usable < .5:
        raise RejectedFeed('Pocos titulares recientes en español o pertinencia insuficiente')
    return {'usable_headlines': usable, 'spanish_headlines': spanish, 'relevant_headlines': relevant,
            'window_days': days}


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


def load_state(path: Path, policy: dict) -> dict:
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError('Estado demasiado grande')
        state = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            raise ValueError('Estado inválido')
    except (OSError, ValueError):
        state = {}
    result = {**{key: state.get(key) for key in ('last_checked_at', 'next_category', 'next_revalidation')},
              'version': 1, 'sources': cleaned_sources(state, policy)}
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


def covered_publishers(sources: list[dict]) -> set[tuple[str, str]]:
    return {(publisher_key(urlsplit(s.get('website') or s['url']).hostname or ''), s['category'])
            for s in sources if not s.get('is_radar') and urlsplit(s['url']).hostname != 'news.google.com'}


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
            evidence = validate_feed(raw, policy[source['category']], source['provenance']['publisher'], now)
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
                    evidence = validate_feed(fetcher.get(url, publisher=host), policy[category], host, now)
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


def write_runtime_opml(curated_path: Path, state: dict, output: Path):
    tree = ET.parse(curated_path)
    body = tree.getroot().find('body')
    folders = {(node.get('text') or node.get('title')): node for node in body.findall('outline')}
    curated = parse_opml(curated_path)
    urls = {source['url'] for source in curated}
    covered = covered_publishers(curated)
    for source in cleaned_sources(state, {category: {} for category in folders}, check_seed=False):
        category = source['category']
        try:
            url = checked_url(source['url'], urlsplit(source['website']).hostname)
        except (UnsafeURL, KeyError):
            continue
        key = (publisher_key(urlsplit(source['website']).hostname), category)
        if category not in folders or url in urls or key in covered:
            continue
        ET.SubElement(folders[category], 'outline', {'text': source['name'], 'title': source['name'],
                      'type': 'rss', 'xmlUrl': url, 'htmlUrl': source['website']})
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
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding='utf-8'))['categories']
    curated = parse_opml(args.opml)
    if set(policy) != {source['category'] for source in curated}:
        raise ValueError('La política debe cubrir todas las carpetas del catálogo')
    state = load_state(args.state, policy)
    result = discover(curated, policy, state, SafeFetcher(), datetime.now(timezone.utc))
    if result.get('last_scan', {}).get('network_unavailable'):
        print('Proxy configurado: no se intenta conexión directa; se conserva el catálogo validado vigente.')
    args.state.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.state.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(args.state)
    write_runtime_opml(args.opml, result, args.runtime_opml)
    print(f"Descubrimiento: {len(result['sources'])} fuentes AUTO; última revisión {result.get('last_checked_at')}")
    print('Última revisión:', json.dumps(result.get('last_scan', {}), ensure_ascii=False))


if __name__ == '__main__':
    main()
