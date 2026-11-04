"""Offline preservation and evidence contracts for the Spanish AI additions."""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from collect import parse_opml
from pending_catalog_history import before_pending_expansions


class SpanishAICatalogTests(unittest.TestCase):
    def setUp(self):
        self.sources = before_pending_expansions(parse_opml(ROOT / 'sources/feeds.opml'), keep=None)
        record = ROOT / 'sources/spanish-ai-verification.json'
        self.record = json.loads(record.read_text()) if record.exists() else {'sources': []}

    def test_five_new_spanish_channels_have_recent_rss_observations(self):
        records = self.record['sources']
        self.assertEqual(len(records), 5)
        by_url = {s['url']: s for s in self.sources}
        for r in records:
            self.assertEqual(r['status'], 'rss_observed')
            self.assertEqual(r['http_status'], 200)
            self.assertFalse(r['bozo'])
            self.assertEqual(r['feed_version'], 'rss20')
            self.assertGreater(r['entries_observed'], 0)
            self.assertGreater(r['recent_dated_entries'], 0)
            self.assertEqual(len(r['response_sha256']), 64)
            source = by_url[r['feed']]
            self.assertTrue(source['is_radar'])
            self.assertEqual((source['name'], source['category'], source['website']),
                             (r['name'], '01 - Inteligencia Artificial', r['website']))
            query = parse_qs(urlsplit(r['feed']).query)
            self.assertEqual(query['hl'], ['es'])
            self.assertEqual(query['q'], [r['query']])
            self.assertIn('when:30d', r['query'])
            checked = datetime.fromisoformat(r['verified_at'])
            published = datetime.fromisoformat(r['last_published_at'].replace('Z', '+00:00'))
            self.assertTrue(checked-timedelta(days=45) <= published <= checked+timedelta(days=1))

    def test_all_previous_271_records_remain_identical(self):
        added = {r['feed'] for r in self.record['sources']}
        added.update(r['feed'] for r in json.loads((ROOT/'sources/world-coverage-verification.json').read_text())['sources'])
        original = [s for s in self.sources if s['url'] not in added]
        digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, '184892ac4967a9293b9514139bc61d2b2026a683d20de9c576920c72496b304b')
        previous_expansion = json.loads((ROOT / 'sources/reliable-expansion-verification.json').read_text())['sources']
        pending_urls = {r['feed'] for r in previous_expansion}
        main_sources = [s for s in original if s['url'] not in pending_urls]
        main_digest = hashlib.sha256(json.dumps(main_sources, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(main_digest, 'f5e294ff5a53550353923023d1d233130cf1709dee4c5dc98da4c18781e5ac06')
        self.assertEqual(len(self.sources), 311)
        self.assertEqual(len({s['id'] for s in self.sources}), 311)
        self.assertEqual(len({s['category'] for s in self.sources}), 8)

    def test_network_restrictions_do_not_masquerade_as_invalid_feeds(self):
        records = self.record.get('pending_direct_feeds', [])
        self.assertGreaterEqual(len(records), 7)
        for record in records:
            self.assertEqual(record['status'], 'not_checked_network_policy')
            self.assertIsNone(record['http_status'])
            self.assertIsNone(record['entries_observed'])
