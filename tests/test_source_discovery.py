"""Offline behavioral tests for automatic publisher discovery and its safety boundary."""
from datetime import datetime, timedelta, timezone
from contextlib import redirect_stdout
import io
from email.utils import format_datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_discovery as discovery
import collect

NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
CATEGORY = '01 - Inteligencia Artificial'
RULE = {'query': 'inteligencia artificial', 'terms': ['inteligencia artificial']}


def rss(titles=None, when=NOW, publisher='nuevo.example', language='es', dated=True):
    titles = titles or ['La inteligencia artificial mejora los servicios de salud',
                        'Los avances de la inteligencia artificial en las empresas',
                        'El futuro de la inteligencia artificial para la educación']
    root = ET.Element('rss', version='2.0')
    channel = ET.SubElement(root, 'channel')
    ET.SubElement(channel, 'title').text = 'Nuevo medio'
    ET.SubElement(channel, 'language').text = language
    for i, title in enumerate(titles):
        entry = ET.SubElement(channel, 'item')
        ET.SubElement(entry, 'title').text = title
        ET.SubElement(entry, 'link').text = f'https://{publisher}/noticias/{i}'
        if dated:
            ET.SubElement(entry, 'pubDate').text = format_datetime(when)
    return ET.tostring(root)


def seed(publisher='nuevo.example'):
    return f'<rss><channel><item><source url="https://{publisher}">Nuevo medio</source></item></channel></rss>'.encode()


class FixtureFetcher:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        response = self.documents.get(url)
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise discovery.FetchError('unavailable')
        return response


def accepted():
    return {'id': sha256(b'https://nuevo.example/feed').hexdigest()[:16],
            'name': 'AUTO — Nuevo medio', 'category': CATEGORY,
            'url': 'https://nuevo.example/feed', 'website': 'https://nuevo.example/',
            'accepted_at': '2026-11-12T12:00:00Z', 'validated_at': '2026-11-12T12:00:00Z',
            'provenance': {'method': 'publisher-homepage-rss-autodiscovery',
                           'seed_url': discovery.seed_url(RULE), 'publisher': 'nuevo.example',
                           'usable_headlines': 3}}


class FeedValidationTests(unittest.TestCase):
    def test_accepts_recent_spanish_relevant_feed_with_evidence(self):
        evidence = discovery.validate_feed(rss(), RULE, 'nuevo.example', NOW)
        self.assertEqual(evidence['usable_headlines'], 3)

    def test_rejects_old_undated_future_english_irrelevant_and_cross_publisher(self):
        cases = [rss(when=NOW-timedelta(days=46)), rss(dated=False),
                 rss(when=NOW+timedelta(days=2)),
                 rss(titles=['The artificial intelligence market is growing',
                             'New artificial intelligence products are available',
                             'Artificial intelligence changes modern healthcare'], language='es'),
                 rss(titles=['La economía mejora en los mercados de Chile',
                             'El gobierno prepara una reforma de la educación',
                             'Las empresas anuncian un aumento de los salarios']),
                 rss(publisher='otro.example'), b'<html><h1>RSS</h1></html>',
                 b'<!DOCTYPE rss [<!ENTITY x "value">]><rss><channel/></rss>']
        for raw in cases:
            with self.subTest(raw=raw[:70]), self.assertRaises(discovery.RejectedFeed):
                discovery.validate_feed(raw, RULE, 'nuevo.example', NOW)

    def test_accepts_atom_with_real_dates_and_original_publisher_links(self):
        entries = ''.join(f'<entry><title>{title}</title><link href="https://nuevo.example/{i}"/>'
                          '<updated>2026-11-14T10:00:00Z</updated></entry>'
                          for i, title in enumerate([
                              'La inteligencia artificial mejora la educación',
                              'Los avances de la inteligencia artificial en la salud',
                              'El futuro de la inteligencia artificial en las empresas']))
        raw = ('<feed xmlns="http://www.w3.org/2005/Atom"><title>Medio</title>'+entries+'</feed>').encode()
        self.assertEqual(discovery.validate_feed(raw, RULE, 'nuevo.example', NOW)['usable_headlines'], 3)

    def test_research_has_730_day_window_without_inventing_dates(self):
        rule = {'terms': ['inteligencia artificial'], 'days': 730}
        self.assertEqual(discovery.validate_feed(rss(when=NOW-timedelta(days=700)), rule,
                                                 'nuevo.example', NOW)['usable_headlines'], 3)
        with self.assertRaises(discovery.RejectedFeed):
            discovery.validate_feed(rss(when=NOW-timedelta(days=731)), rule, 'nuevo.example', NOW)

    def test_local_folder_requires_geography_in_multiple_titles(self):
        rule = {'terms': ['maturin', 'monagas'], 'geographic': True}
        with self.assertRaises(discovery.RejectedFeed):
            discovery.validate_feed(rss(), rule, 'nuevo.example', NOW)
        titles = ['El municipio de Maturín anuncia nuevas obras para la comunidad',
                  'Las escuelas de Monagas reciben una nueva inversión',
                  'El transporte de Maturín mejora para los vecinos']
        self.assertEqual(discovery.validate_feed(rss(titles), rule, 'nuevo.example', NOW)['usable_headlines'], 3)

    def test_repeated_headline_or_link_cannot_satisfy_minimum(self):
        with self.assertRaises(discovery.RejectedFeed):
            discovery.validate_feed(rss(['La inteligencia artificial mejora la vida']*3), RULE, 'nuevo.example', NOW)


class DiscoveryStateTests(unittest.TestCase):
    def run_scan(self, state=None, documents=None, curated=None, policy=None):
        fetcher = FixtureFetcher(documents or {})
        result = discovery.discover(curated or [], policy or {CATEGORY: RULE}, state or {}, fetcher, NOW)
        return result, fetcher

    def documents(self):
        return {discovery.seed_url(RULE): seed(), 'https://nuevo.example/':
                b'<html><head><link rel="alternate" type="application/rss+xml" href="/feed"></head></html>',
                'https://nuevo.example/feed': rss()}

    def test_discovers_auto_source_and_exports_real_provenance(self):
        result, _ = self.run_scan(documents=self.documents())
        self.assertEqual(len(result['sources']), 1)
        source = result['sources'][0]
        self.assertTrue(source['name'].startswith('AUTO — '))
        self.assertEqual(source['provenance']['seed_url'], discovery.seed_url(RULE))
        self.assertEqual(source['provenance']['usable_headlines'], 3)
        self.assertEqual(source['accepted_at'], '2026-11-14T12:00:00Z')

    def test_unavailable_and_empty_successful_scans_have_different_outcomes(self):
        unavailable, _ = self.run_scan()
        self.assertEqual(unavailable['last_scan']['outcome'], 'unavailable')
        self.assertEqual(unavailable['last_scan']['seed_errors'], 1)
        self.assertEqual(unavailable['last_scan']['seed_successes'], 0)
        empty, _ = self.run_scan(documents={discovery.seed_url(RULE): b'<rss><channel/></rss>'})
        self.assertEqual(empty['last_scan']['outcome'], 'no_eligible_sources')
        self.assertEqual(empty['last_scan']['seed_successes'], 1)
        self.assertEqual(empty['last_scan']['seed_errors'], 0)
        docs = self.documents()
        docs['https://nuevo.example/'] = discovery.FetchError('robots denies', reason='robots')
        blocked, _ = self.run_scan(documents=docs)
        self.assertEqual(blocked['last_scan']['robots_denials'], 1)
        self.assertEqual(blocked['last_scan']['outcome'], 'partial')

    def test_empty_completed_scan_throttles_for_48h_and_boundary_runs(self):
        result, _ = self.run_scan()
        again, fetcher = self.run_scan(state=result)
        self.assertEqual(fetcher.calls, [])
        self.assertEqual(again['last_checked_at'], result['last_checked_at'])
        old = dict(result, last_checked_at=collect.iso(NOW-timedelta(hours=48)))
        _, fetcher = self.run_scan(state=old)
        self.assertTrue(fetcher.calls)

    def test_future_timestamp_cannot_disable_scans_indefinitely(self):
        _, fetcher = self.run_scan(state={'last_checked_at': '2099-01-01T00:00:00Z'})
        self.assertTrue(fetcher.calls)

    def test_transient_error_preserves_accepted_sources(self):
        source = accepted()
        state = {'sources': [source], 'last_checked_at': '2026-11-12T12:00:00Z'}
        result, _ = self.run_scan(state=state)
        self.assertEqual(result['sources'], [source])
        self.assertEqual(result['last_checked_at'], collect.iso(NOW))

    def test_conclusive_failed_revalidation_excludes_invalid_feed(self):
        result, _ = self.run_scan(state={'sources': [accepted()]}, documents={
            'https://nuevo.example/feed': b'<html>Not RSS</html>'})
        self.assertEqual(result['sources'], [])

    def test_duplicates_of_curated_url_or_publisher_category_are_excluded(self):
        for existing in [dict(accepted()), dict(accepted(), url='https://nuevo.example/other')]:
            result, fetcher = self.run_scan(curated=[existing], documents=self.documents())
            self.assertEqual(result['sources'], [])
            self.assertNotIn('https://nuevo.example/', fetcher.calls)

    def test_already_covered_seed_publishers_do_not_consume_candidate_slots(self):
        docs = self.documents()
        docs[discovery.seed_url(RULE)] = (
            '<rss><channel><item><source url="https://existing1.example">Existing 1</source></item>'
            '<item><source url="https://existing2.example">Existing 2</source></item>'
            '<item><source url="https://nuevo.example">Nuevo</source></item></channel></rss>').encode()
        curated = [dict(accepted(), url=f'https://existing{i}.example/feed',
                        website=f'https://existing{i}.example/') for i in (1, 2)]
        result, _ = self.run_scan(curated=curated, documents=docs)
        self.assertEqual(len(result['sources']), 1)
        self.assertEqual(result['sources'][0]['url'], 'https://nuevo.example/feed')

    def test_every_folder_seed_is_investigated_even_after_addition_limit(self):
        policy = {f'{i:02} - Topic': dict(RULE, query=f'topic {i}') for i in range(11)}
        docs = {}
        for i, rule in enumerate(policy.values()):
            host = f'editor{i}.example'
            docs[discovery.seed_url(rule)] = seed(host)
            docs[f'https://{host}/'] = b'<link rel="alternate" type="application/rss+xml" href="/feed">'
            docs[f'https://{host}/feed'] = rss(publisher=host)
        result, fetcher = self.run_scan(policy=policy, documents=docs)
        self.assertEqual(len(result['sources']), 5)
        self.assertTrue(all(discovery.seed_url(rule) in fetcher.calls for rule in policy.values()))
        self.assertNotEqual(result['next_category'], 0)

    def test_total_auto_sources_are_capped_at_100_and_revalidation_at_five(self):
        sources = []
        for i in range(100):
            host = f'previo{i}.example'
            url = f'https://{host}/feed'
            source = accepted()
            source.update(id=sha256(url.encode()).hexdigest()[:16], url=url, website=f'https://{host}/')
            source['provenance']['publisher'] = host
            sources.append(source)
        result, fetcher = self.run_scan(state={'sources': sources}, documents=self.documents())
        self.assertEqual(len(result['sources']), 100)
        self.assertNotIn('https://nuevo.example/', fetcher.calls)
        self.assertEqual(len([url for url in fetcher.calls if 'previo' in url]), 5)

    def test_next_cycle_starts_with_next_category(self):
        policy = {'a': dict(RULE, query='a'), 'b': dict(RULE, query='b')}
        result, _ = self.run_scan(policy=policy)
        result['last_checked_at'] = collect.iso(NOW-timedelta(hours=48))
        _, fetcher = self.run_scan(state=result, policy=policy)
        self.assertEqual(fetcher.calls[0], discovery.seed_url(policy['b']))

    def test_cross_publisher_autodiscovery_links_are_ignored(self):
        docs = self.documents()
        docs['https://nuevo.example/'] = b'<link rel="alternate" type="application/rss+xml" href="https://evil.example/feed">'
        result, fetcher = self.run_scan(documents=docs)
        self.assertEqual(result['sources'], [])
        self.assertNotIn('https://evil.example/feed', fetcher.calls)

    def test_policy_covers_all_eleven_curated_categories(self):
        policy = json.loads((ROOT/'sources/discovery-policy.json').read_text())['categories']
        self.assertEqual(set(policy), {s['category'] for s in collect.parse_opml(ROOT/'sources/feeds.opml')})

    def test_runtime_catalog_preserves_443_ids_and_11_folders(self):
        path = ROOT/'sources/feeds.opml'
        before = path.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'runtime.opml'
            discovery.write_runtime_opml(path, {'sources': [accepted()]}, output)
            original = collect.parse_opml(path)
            runtime = collect.parse_opml(output)
        self.assertEqual(len(original), 443)
        self.assertEqual(len(runtime), 444)
        self.assertEqual({s['id'] for s in original}, {s['id'] for s in runtime if not s['name'].startswith('AUTO — ')})
        self.assertEqual(len({s['category'] for s in runtime}), 11)
        self.assertEqual(path.read_bytes(), before)

    def test_cli_writes_state_and_runtime_and_retains_scan_evidence_between_cycles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy = root/'policy.json'
            curated = root/'curated.opml'
            policy.write_text(json.dumps({'categories': {CATEGORY: RULE}}))
            curated.write_text(f'<opml><body><outline text="{CATEGORY}"><outline title="Existing" '
                               'xmlUrl="https://existing.example/feed" htmlUrl="https://existing.example/"/>'
                               '</outline></body></opml>')
            args = ['source_discovery.py', '--opml', str(curated), '--policy', str(policy),
                    '--state', str(root/'state.json'), '--runtime-opml', str(root/'runtime.opml')]
            fetcher = FixtureFetcher(self.documents())
            with patch.object(sys, 'argv', args), patch.object(discovery, 'SafeFetcher', return_value=fetcher), \
                    patch.object(discovery, 'datetime', wraps=datetime) as clock, redirect_stdout(io.StringIO()):
                clock.now.return_value = NOW
                discovery.main()
                first = json.loads((root/'state.json').read_text())
                discovery.main()
            second = json.loads((root/'state.json').read_text())
            self.assertEqual(second['last_scan'], first['last_scan'])
            self.assertEqual(len(collect.parse_opml(root/'runtime.opml')), 2)
            self.assertEqual(len(fetcher.calls), 3)
            self.assertFalse((root/'state.tmp').exists())

    def test_normal_collection_publishes_auto_sources_and_consistent_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root/'runtime.opml'
            discovery.write_runtime_opml(ROOT/'sources/feeds.opml', {'sources': [accepted()]}, runtime)
            with patch.object(collect, 'NOW', return_value=NOW), \
                    patch.object(collect, 'get_feed', return_value=rss()), redirect_stdout(io.StringIO()):
                result = collect.collect(runtime, root/'web/data', 45, 1, 12)
            sources = json.loads((root/'web/data/sources.json').read_text())['sources']
            articles = json.loads((root/'web/data/articles.json').read_text())
            status = json.loads((root/'web/data/status.json').read_text())['feeds']
        self.assertEqual(result['sources'], 444)
        self.assertEqual(articles['total_sources'], 444)
        self.assertEqual(len(sources), len(status))
        self.assertEqual({s['id'] for s in sources}, {s['id'] for s in status})
        self.assertEqual(sum(s['name'].startswith('AUTO — ') for s in sources), 1)
        self.assertTrue(any(accepted()['id'] in item['source_ids'] for item in articles['items']))

    def test_runtime_assembler_rejects_forged_stale_future_and_wrong_category_sources(self):
        cases = [dict(accepted(), id='forged'), dict(accepted(), category='Other'),
                 dict(accepted(), validated_at='2099-01-01T00:00:00Z'),
                 dict(accepted(), accepted_at='2020-01-01T00:00:00Z', validated_at='2020-01-01T00:00:00Z'),
                 dict(accepted(), provenance=dict(accepted()['provenance'], method='unverified'))]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'runtime.opml'
            for source in cases:
                discovery.write_runtime_opml(ROOT/'sources/feeds.opml', {'sources': [source]}, output)
                self.assertEqual(len(collect.parse_opml(output)), 443)

    def test_state_loader_rejects_untrusted_or_oversized_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'state.json'
            path.write_text(json.dumps({'sources': [dict(accepted(), url='https://127.0.0.1/feed')]}))
            self.assertEqual(discovery.load_state(path, {CATEGORY: RULE})['sources'], [])
            path.write_bytes(b' '*300_000)
            self.assertEqual(discovery.load_state(path, {CATEGORY: RULE})['sources'], [])


class NetworkSafetyTests(unittest.TestCase):
    def setUp(self):
        # Mocked network tests deliberately isolate the inherited transport policy.
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_configured_proxy_prevents_dns_or_socket_and_preserves_accepted_state(self):
        with patch.dict(os.environ, {'HTTPS_PROXY': 'http://proxy.example:8080'}), \
                patch('source_discovery.socket.getaddrinfo') as dns, \
                patch('source_discovery.socket.create_connection') as connect:
            fetcher = self.fetcher()
            with self.assertRaises(discovery.FetchError):
                fetcher.get('https://example.com/feed')
            result = discovery.discover([], {CATEGORY: RULE}, {'sources': [accepted()]}, fetcher, NOW)
            self.assertEqual(result['sources'], [accepted()])
            self.assertTrue(result['last_scan']['network_unavailable'])
            dns.assert_not_called()
            connect.assert_not_called()

    def fetcher(self):
        return discovery.SafeFetcher()

    @patch('source_discovery.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))])
    def test_rejects_unsafe_urls_and_mixed_private_dns_without_connecting(self, dns):
        unsafe = ['http://example.com/', 'https://user:pass@example.com/', 'https://127.0.0.1/',
                  'https://[::1]/', 'https://localhost/', 'https://example.com:444/',
                  'https://example.com.evil/feed', 'https://example.com/\nfoo']
        fetcher = self.fetcher()
        with patch.object(fetcher, '_request') as request:
            for url in unsafe:
                with self.subTest(url=url), self.assertRaises(discovery.UnsafeURL):
                    fetcher.get(url, publisher='example.com')
            request.assert_not_called()
        dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443)),
                            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
        with self.assertRaises(discovery.UnsafeURL):
            discovery.resolve_public('example.com')

    def test_redirect_to_private_or_other_publisher_is_never_requested(self):
        fetcher = self.fetcher()
        with patch.object(fetcher, '_request', side_effect=[(404, {}, b''), (302, {'location': 'https://127.0.0.1/'}, b'')]) as request:
            with self.assertRaises(discovery.UnsafeURL):
                fetcher.get('https://example.com/', publisher='example.com')
            self.assertEqual(request.call_count, 2)

    def test_robots_denial_and_403_are_not_bypassed(self):
        fetcher = self.fetcher()
        with patch.object(fetcher, '_request', return_value=(200, {}, b'User-agent: *\nDisallow: /feed\n')) as request:
            with self.assertRaises(discovery.FetchError):
                fetcher.get('https://example.com/feed', publisher='example.com')
            self.assertEqual(request.call_count, 1)
        fetcher = self.fetcher()
        with patch.object(fetcher, '_request', return_value=(403, {}, b'')) as request:
            with self.assertRaises(discovery.FetchError):
                fetcher.get('https://example.com/feed', publisher='example.com')
            self.assertEqual(request.call_count, 1)

    def test_request_and_wall_clock_budgets(self):
        fetcher = self.fetcher()
        fetcher.requests_left = 0
        with self.assertRaises(discovery.BudgetExceeded):
            fetcher.get('https://example.com/')
        fetcher = self.fetcher()
        fetcher.deadline = 0
        with self.assertRaises(discovery.BudgetExceeded):
            fetcher.get('https://example.com/')

    def test_byte_limit_rejects_oversized_body_without_unbounded_read(self):
        fetcher = self.fetcher()
        response = unittest.mock.Mock()
        response.getheaders.return_value = []
        response.read1.return_value = b'x'*11
        connection = unittest.mock.Mock()
        connection.getresponse.return_value = response
        with patch('source_discovery.resolve_public', return_value='93.184.216.34'), \
                patch('source_discovery.PinnedHTTPSConnection', return_value=connection):
            with self.assertRaises(discovery.FetchError):
                fetcher._request('https://example.com/feed', 10)
        response.read.assert_not_called()
        connection.close.assert_called_once()

    def test_robots_respects_named_crawler_and_crawl_delay(self):
        fetcher = self.fetcher()
        with patch.object(fetcher, '_request', return_value=(200, {}, b'User-agent: RadarRSS\nDisallow: /feed\n')):
            with self.assertRaises(discovery.FetchError):
                fetcher.get('https://example.com/feed', publisher='example.com')
        fetcher = self.fetcher()
        with patch.object(fetcher, '_request', side_effect=[
                (200, {}, b'User-agent: *\nCrawl-delay: 120\n'), (200, {}, b'ok')]) as request:
            self.assertEqual(fetcher.get('https://example.com/'), b'ok')
            with self.assertRaises(discovery.FetchError):
                fetcher.get('https://example.com/feed')
            self.assertEqual(request.call_count, 2)

    def test_dns_timeout_is_bounded(self):
        from threading import Event
        release = Event()
        def stuck_dns(*args, **kwargs):
            release.wait(1)
            return []
        try:
            with patch('source_discovery.socket.getaddrinfo', side_effect=stuck_dns):
                with self.assertRaises(discovery.FetchError):
                    discovery.resolve_public('example.com', timeout=.001)
        finally:
            release.set()

    def test_tls_connection_uses_verified_pinned_ip_and_original_hostname(self):
        context = unittest.mock.Mock()
        with patch('source_discovery.socket.create_connection') as connect:
            connection = discovery.PinnedHTTPSConnection('example.com', '93.184.216.34', 5, context)
            connection.connect()
            self.assertEqual(connect.call_args.args[0], ('93.184.216.34', 443))
            context.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='example.com')

    def test_workflow_caches_state_uses_runtime_and_attempt_specific_pages_artifact(self):
        workflow = (ROOT/'.github/workflows/deploy.yml').read_text()
        self.assertIn('17 * * * *', workflow)
        self.assertIn('python scripts/source_discovery.py', workflow)
        self.assertIn('--opml "$RUNNER_TEMP/effective-feeds.opml"', workflow)
        self.assertGreaterEqual(workflow.count('web/data/discovered-sources.json'), 2)
        self.assertIn('name: github-pages-${{ github.run_attempt }}', workflow)
        self.assertIn('artifact_name: github-pages-${{ github.run_attempt }}', workflow)
        self.assertIn('artifact_name: ${{ needs.build.outputs.artifact_name }}', workflow)
        self.assertIn('actions/cache/restore@v4', workflow)
        self.assertIn('actions/cache/save@v4', workflow)
        self.assertLess(workflow.index('actions/cache/save@v4'), workflow.index('      - name: Obtener noticias'))


if __name__ == '__main__':
    unittest.main()
