"""Offline evidence and preservation contracts for worldwide RSS coverage."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from collect import parse_opml
from pending_catalog_history import before_pending_expansions


class WorldCatalogTests(unittest.TestCase):
    def setUp(self):
        self.sources = before_pending_expansions(parse_opml(ROOT / 'sources/feeds.opml'), keep=None)
        path = ROOT / 'sources/world-coverage-verification.json'
        self.record = json.loads(path.read_text()) if path.exists() else {'sources': []}

    def test_new_channels_match_observed_rss_and_catalog(self):
        self.assertEqual(len(self.record['sources']), 35)
        catalog = {s['url']: s for s in self.sources}
        for row in self.record['sources']:
            source = catalog[row['feed']]
            self.assertEqual((source['name'], source['category'], source['website']),
                             (row['name'], row['category'], row['website']))
            self.assertEqual(row['http_status'], 200)
            self.assertIn(row['feed_version'], ('rss20', 'atom10'))
            self.assertEqual(row['status'], 'rss_observed')
            self.assertGreater(row['entries_observed'], 0)
            self.assertGreater(row['recent_dated_entries'], 0)
            self.assertEqual(len(row['response_sha256']), 64)
            observed = datetime.fromisoformat(row['verified_at'])
            published = datetime.fromisoformat(row['last_published_at'].replace('Z', '+00:00'))
            self.assertTrue(observed-timedelta(days=45) <= published <= observed+timedelta(days=1))
            if source['is_radar']:
                self.assertTrue(source['name'].startswith('RADAR — '))
                self.assertEqual(urlsplit(source['url']).hostname, 'news.google.com')
                query = parse_qs(urlsplit(source['url']).query)
                self.assertIn(query['hl'][0], ('es', 'es-419'))
                self.assertIn(query['gl'][0], ('ES', 'MX'))
                if row.get('query'):
                    self.assertEqual(query['q'], [row['query']])
                    self.assertIn('when:7d', row['query'])
            else:
                self.assertEqual(source['url'], 'https://www.technologyreview.es/rss/all')
                self.assertEqual(row['feed_language'], 'es')

    def test_all_276_previous_records_are_preserved(self):
        new_urls = {row['feed'] for row in self.record['sources']}
        original = [s for s in self.sources if s['url'] not in new_urls]
        digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, 'd9bf71a2ce407a7757574c815ffc4e783d48041d91dfe9dcaeb6316a4baa1c59')
        self.assertEqual(len(self.sources), 311)
        self.assertEqual(len({s['url'] for s in self.sources}), 311)
        self.assertEqual(len({s['id'] for s in self.sources}), 311)
        self.assertEqual(len({s['category'] for s in self.sources}), 8)

    def test_regions_topics_and_native_mit_are_present(self):
        keys = {row['key'] for row in self.record['sources']}
        regions = {'northamerica', 'europe', 'middleeast', 'africa', 'southasia', 'eastasia',
                   'southeastasia', 'oceania', 'centralasia', 'centralcaribbean'}
        topics = {'world', 'economy', 'health', 'science', 'sports', 'culture', 'climate',
                  'society', 'education', 'travel', 'emergencies', 'politics'}
        self.assertTrue(regions | topics | {'mit-es-native'} <= keys)
        native = [s for s in self.sources if s['url'] == 'https://www.technologyreview.es/rss/all']
        self.assertEqual(len(native), 1)
        self.assertEqual(native[0]['name'], 'MEDIO — MIT Technology Review en español')
        self.assertTrue(any('MIT Technology Review en español' in s['name'] and s['is_radar'] for s in self.sources))

    def test_previous_native_feeds_are_now_revalidated_without_rewriting_history(self):
        rows = self.record.get('revalidated_native_sources', [])
        self.assertEqual(len(rows), 7)
        for row in rows:
            self.assertEqual(row['status_code'], 200)
            self.assertEqual(row['feed_version'], 'rss20')
            self.assertGreater(row['entries_observed'], 0)
        historical = json.loads((ROOT / 'sources/spanish-ai-verification.json').read_text())
        self.assertTrue(all(r['status'] == 'not_checked_network_policy' for r in historical['pending_direct_feeds']))

    @unittest.skipUnless(shutil.which('node'), 'Node no disponible')
    def test_world_priority_node_regressions(self):
        result = subprocess.run(['node', 'tests/test_home_priority.cjs'], cwd=ROOT,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
