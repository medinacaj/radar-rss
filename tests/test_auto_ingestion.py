"""AUTO feeds must keep their discovery safety boundary on every hourly fetch."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from threading import Event

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import collect
import source_discovery as discovery
import safe_publisher
import auto_sources

NOW = datetime(2027, 2, 20, 12, tzinfo=timezone.utc)
CATEGORY = '01 - Inteligencia Artificial'


def source():
    return {'id': 'auto', 'name': 'AUTO — Medio', 'category': CATEGORY,
            'url': 'https://nuevo.example/feed', 'website': 'https://nuevo.example/',
            'is_radar': False, 'is_auto': True}


def rss(extra=''):
    rows = ''.join(f'<item><title>{title}</title><link>https://nuevo.example/{i}</link>'
                   f'<pubDate>{format_datetime(NOW)}</pubDate></item>'
                   for i, title in enumerate([
                       'La inteligencia artificial mejora los servicios de salud',
                       'Los avances de la inteligencia artificial en las empresas',
                       'El futuro de la inteligencia artificial para la educación']))
    return ('<rss><channel>'+rows+extra+'</channel></rss>').encode()


class AutoIngestionTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict('os.environ', {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.curated_transport = patch.object(collect, 'get_feed', side_effect=AssertionError('AUTO used curated transport'))
        self.curated_transport.start()
        self.addCleanup(self.curated_transport.stop)

    def test_every_auto_fetch_uses_pinned_transport_and_current_feed_validation(self):
        with patch.object(collect, 'get_feed', side_effect=AssertionError('weaker curated transport')), \
                patch.object(safe_publisher.SafeFetcher, 'get', return_value=rss()) as fetch, \
                patch.object(safe_publisher, 'resolve_public', return_value='93.184.216.34'):
            items, status = collect.get_one(source(), NOW, 12)
        self.assertEqual(status['state'], 'ok')
        self.assertEqual(len(items), 3)
        self.assertEqual(fetch.call_args.kwargs['publisher'], 'nuevo.example')
        self.assertTrue(all(item['image'] is None for item in items))

    def test_hourly_change_cannot_publish_off_publisher_private_http_or_undated_links(self):
        extra = ''.join(f'<item><title>La inteligencia artificial mejora la vida de todos {i}</title>'
                        f'<link>{url}</link><pubDate>{format_datetime(NOW)}</pubDate></item>'
                        for i, url in enumerate(['https://otro.example/1', 'https://127.0.0.1/2',
                                                'http://nuevo.example/3', 'https://www.nuevo.example/4']))
        extra += '<item><title>La inteligencia artificial anuncia las nuevas soluciones</title><link>https://nuevo.example/no-date</link></item>'
        def dns(host, **kwargs):
            if host.startswith('www.'):
                raise safe_publisher.UnsafeURL('private DNS')
            return '93.184.216.34'
        with patch.object(safe_publisher.SafeFetcher, 'get', return_value=rss(extra)), \
                patch.object(safe_publisher, 'resolve_public', side_effect=dns):
            items, status = collect.get_one(source(), NOW, 12)
        self.assertEqual(status['state'], 'ok')
        self.assertEqual(len(items), 3)
        self.assertEqual({item['url'] for item in items}, {f'https://nuevo.example/{i}' for i in range(3)})

    def test_changed_language_or_topic_is_rejected_at_hourly_ingestion(self):
        with patch.object(safe_publisher.SafeFetcher, 'get', return_value=b'<html>no RSS</html>'), \
                patch.object(collect, 'get_feed', side_effect=AssertionError('curated transport used')):
            items, status = collect.get_one(source(), NOW, 12)
        self.assertEqual(items, [])
        self.assertEqual(status['state'], 'error')

    def test_auto_fetch_never_retries_429_or_follows_http_cross_publisher_redirects(self):
        cases = [(429, {}, b''), (302, {'location': 'http://nuevo.example/feed2'}, b''),
                 (302, {'location': 'https://otro.example/feed'}, b'')]
        for response in cases:
            with self.subTest(response=response), \
                    patch.object(safe_publisher.SafeFetcher, '_allowed'), \
                    patch.object(safe_publisher.SafeFetcher, '_request', return_value=response) as request, \
                    patch.object(collect, 'get_feed', side_effect=AssertionError('curated transport used')):
                items, status = collect.get_one(source(), NOW, 12)
                self.assertEqual(items, [])
                self.assertEqual(status['state'], 'error')
                self.assertEqual(request.call_count, 1)

    def test_auto_fetch_rejects_changed_private_dns_before_opening_socket(self):
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443))]
        with patch.object(safe_publisher.socket, 'getaddrinfo', return_value=private), \
                patch.object(safe_publisher.socket, 'socket') as connect, \
                patch.object(collect, 'get_feed', side_effect=AssertionError('curated transport used')):
            items, status = collect.get_one(source(), NOW, 12)
        self.assertEqual(items, [])
        self.assertEqual(status['state'], 'error')
        connect.assert_not_called()

    def test_dns_change_after_feed_connection_cannot_reconnect_to_private_address(self):
        raw = rss()
        payload = b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw
        fixture_socket = DripSocket(payload, len(payload))
        connected = []
        class Connection(safe_publisher.PinnedHTTPSConnection):
            def connect(self):
                connected.append(self.address)
                self.sock = self._transport_socket = fixture_socket
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443))]
        with patch.object(safe_publisher.SafeFetcher, '_allowed'), \
                patch.object(safe_publisher.socket, 'getaddrinfo', side_effect=[public, private]) as dns, \
                patch.object(safe_publisher, 'PinnedHTTPSConnection', Connection), \
                patch.object(collect, 'get_feed', side_effect=AssertionError('curated transport used')):
            items, status = collect.get_one(source(), NOW, 12)
        self.assertEqual(connected, ['93.184.216.34'])
        self.assertEqual(dns.call_count, 2)
        self.assertEqual(items, [])
        self.assertEqual(status['state'], 'error')

    def test_unverified_cached_auto_article_is_not_republished_or_enriched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            opml = root/'runtime.opml'
            opml.write_text(f'<opml><body><outline text="{CATEGORY}"><outline title="AUTO — Medio" '
                            'radarAuto="validated-v1" xmlUrl="https://nuevo.example/feed" '
                            'htmlUrl="https://nuevo.example/"/></outline></body></opml>')
            src = collect.parse_opml(opml)[0]
            out = root/'web/data'
            out.mkdir(parents=True)
            prior = {'id': 'old-unsafe', 'url': 'https://127.0.0.1/private', 'title': 'Old unsafe article',
                     'published_at': collect.iso(NOW), 'first_seen_at': collect.iso(NOW),
                     'source_ids': [src['id']], 'categories': [CATEGORY], 'image': None}
            (out/'articles.json').write_text(json.dumps({'items': [prior]}))
            with patch.object(collect, 'NOW', return_value=NOW), \
                    patch.object(safe_publisher.SafeFetcher, 'get', return_value=rss()), \
                    patch.object(safe_publisher, 'resolve_public', return_value='93.184.216.34'), \
                    patch.object(collect, 'lookup_original_image', side_effect=AssertionError('AUTO OG fetched')) as image, \
                    redirect_stdout(io.StringIO()):
                collect.collect(opml, out, 45, 1, 12, image_fallback=True)
            items = json.loads((out/'articles.json').read_text())['items']
            self.assertTrue(items)
            self.assertNotIn('old-unsafe', {item['id'] for item in items})
            self.assertTrue(all(item['url'].startswith('https://nuevo.example/') for item in items))
            image.assert_not_called()

    def test_auto_og_enrichment_is_never_queued(self):
        article = {'id': 'a', 'title': 'News', 'url': 'https://nuevo.example/a', 'image': None,
                   'published_at': collect.iso(NOW), 'source_ids': ['auto']}
        with patch.object(collect, 'lookup_original_image', side_effect=AssertionError('AUTO OG fetched')):
            result = collect.recover_missing_images([article], NOW, [source()])
        self.assertEqual(result['checked'], 0)

    def test_auto_fetch_has_small_total_per_feed_budget(self):
        with patch.object(auto_sources, 'SafeFetcher') as constructor, \
                patch.object(safe_publisher, 'resolve_public', return_value='93.184.216.34'):
            constructor.return_value.get.return_value = rss()
            collect.get_one(source(), NOW, 12)
        self.assertLessEqual(constructor.call_args.kwargs['seconds'], 12)
        self.assertLessEqual(constructor.call_args.kwargs['max_requests'], 8)

    def test_runtime_now_is_injected_for_fresh_and_expired_state_in_2027(self):
        url = 'https://nuevo.example/feed'
        from hashlib import sha256
        row = dict(source(), id=sha256(url.encode()).hexdigest()[:16],
                   accepted_at=collect.iso(NOW-timedelta(days=1)), validated_at=collect.iso(NOW-timedelta(days=1)),
                   provenance={'method': discovery.METHOD, 'seed_url': discovery.seed_url({'query': 'AI'}),
                               'publisher': 'nuevo.example', 'usable_headlines': 3})
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'runtime.opml'
            discovery.write_runtime_opml(ROOT/'sources/feeds.opml', {'sources': [row]}, output, now=NOW)
            parsed = collect.parse_opml(output)
            self.assertEqual(len(parsed), 444)
            self.assertTrue(next(s for s in parsed if s['id'] == row['id'])['is_auto'])
            discovery.write_runtime_opml(ROOT/'sources/feeds.opml', {'sources': [row]}, output,
                                         now=NOW+timedelta(days=91))
            self.assertEqual(len(collect.parse_opml(output)), 443)


class DripStream(io.RawIOBase):
    def __init__(self, payload, fast_prefix, aborted):
        self.payload, self.position, self.fast_prefix, self.aborted = payload, 0, fast_prefix, aborted

    def readable(self):
        return True

    def readinto(self, buffer):
        if self.position >= self.fast_prefix:
            self.aborted.wait(.002)
        if self.aborted.is_set():
            raise OSError('socket shut down by absolute deadline')
        if self.position >= len(self.payload):
            return 0
        count = min(len(buffer), max(1, self.fast_prefix-self.position))
        data = self.payload[self.position:self.position+count]
        buffer[:len(data)] = data
        self.position += len(data)
        return len(data)


class DripSocket:
    def __init__(self, payload, fast_prefix):
        self.aborted = Event()
        self.stream = DripStream(payload, fast_prefix, self.aborted)

    def makefile(self, mode):
        return io.BufferedReader(self.stream, buffer_size=32)

    def sendall(self, data):
        pass

    def settimeout(self, timeout):
        pass

    def shutdown(self, how):
        self.aborted.set()

    def close(self):
        # A response.makefile retains the descriptor, just like a real socket.
        pass


class AbsoluteDeadlineTests(unittest.TestCase):
    def test_absolute_deadline_interrupts_trickled_headers_and_chunk_framing(self):
        header = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'
        cases = [(b'HTTP/1.1 200 OK\r\nX-Long: '+b'a'*10_000+b'\r\n\r\n', 0),
                 (header+b'1'+b' '*10_000+b'\r\nx\r\n0\r\n\r\n', len(header)),
                 (header.replace(b'\r\n\r\n', b'\r\nConnection: close\r\n\r\n')+
                  b'1'+b' '*10_000+b'\r\nx\r\n0\r\n\r\n', len(header)+19)]
        for payload, fast_prefix in cases:
            fake_socket = DripSocket(payload, fast_prefix)
            class Connection(safe_publisher.PinnedHTTPSConnection):
                def connect(self):
                    self.sock = fake_socket
                    self._transport_socket = fake_socket
            with self.subTest(phase='headers' if not fast_prefix else 'chunk framing'), \
                    patch.dict('os.environ', {}, clear=True), \
                    patch.object(safe_publisher, 'resolve_public', return_value='93.184.216.34'), \
                    patch.object(safe_publisher, 'PinnedHTTPSConnection', Connection):
                fetcher = safe_publisher.SafeFetcher(seconds=1, exchange_seconds=.05)
                started = time.monotonic()
                with self.assertRaises(safe_publisher.FetchError):
                    fetcher._request('https://nuevo.example/feed', 100_000)
                elapsed = time.monotonic()-started
                self.assertLess(elapsed, .5)
                self.assertGreater(elapsed, .03)
                self.assertTrue(fake_socket.aborted.is_set())
                self.assertGreater(fake_socket.stream.position, fast_prefix)


if __name__ == '__main__':
    unittest.main()
