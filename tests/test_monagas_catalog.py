"""Preservation and provenance of the six requested Monagas publishers."""
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


class MonagasCatalogTests(unittest.TestCase):
    def setUp(self):
        self.sources = before_pending_expansions(parse_opml(ROOT / 'sources/feeds.opml'), keep='monagas')
        self.record = json.loads((ROOT / 'sources/monagas-verification.json').read_text())

    def test_all_311_original_subscriptions_remain_identical(self):
        added = {row['feed'] for row in self.record['sources']}
        originals = [source for source in self.sources if source['url'] not in added]
        digest = hashlib.sha256(json.dumps(originals, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(len(originals), 311)
        self.assertEqual(digest, '4e66c2aff0543cd680543ee5109c3c438f0657b814fb71713f927b21d1bfbe5b')

    def test_local_additions_have_recent_observations_and_six_traceable_results(self):
        self.assertEqual({r['key'] for r in self.record['requests']},
                         {'laverdad', 'periodico', 'prensa', 'maturinnews', 'pitazo', 'cronica'})
        catalog = {s['url']: s for s in self.sources}
        self.assertEqual(len(catalog), len(self.sources))
        ids = {s['id'] for s in self.sources}
        for request in self.record['requests']:
            self.assertTrue(request['reason'])
            if request['status'] != 'pending_local_verification':
                self.assertTrue(request['catalog_source_ids'])
            self.assertTrue(set(request['catalog_source_ids']) <= ids)
        for row in self.record['sources']:
            source = catalog[row['feed']]
            self.assertEqual(source['category'], '08 - Maturín / Monagas')
            self.assertEqual(source['name'], row['name'])
            self.assertEqual(source['id'], hashlib.sha256(row['feed'].encode()).hexdigest()[:16])
            self.assertEqual(row['http_status'], 200)
            self.assertIn(row['feed_version'], ('rss20', 'rss10', 'atom10'))
            self.assertGreater(row['recent_dated_entries'], 0)
            self.assertEqual(len(row['response_sha256']), 64)
            checked = datetime.fromisoformat(row['verified_at'])
            published = datetime.fromisoformat(row['last_published_at'])
            self.assertTrue(checked-timedelta(days=45) <= published <= checked+timedelta(days=1))
            if row['provider'] == 'google_news':
                self.assertTrue(source['is_radar'])
                self.assertTrue(source['name'].startswith('RADAR — '))
                self.assertEqual(urlsplit(source['url']).hostname, 'news.google.com')
                self.assertEqual(parse_qs(urlsplit(source['url']).query)['q'], [row['query']])
                self.assertIn('Monagas', row['query'])
                self.assertIn('when:45d', row['query'])
            else:
                self.assertFalse(source['is_radar'])
                self.assertEqual(urlsplit(source['url']).path, '/maturin/feed/')

    def test_unconfirmed_cronica_result_does_not_become_a_local_subscription(self):
        request = next(r for r in self.record['requests'] if r['key'] == 'cronica')
        self.assertEqual(request['status'], 'pending_local_verification')
        self.assertEqual(request['catalog_source_ids'], [])
        self.assertFalse(any(r['key'] == 'cronica' for r in self.record['sources']))
        # The national subscription remains available in its original folder.
        source = next(s for s in self.sources if s['id'] == 'ec0a03cccfad36cf')
        self.assertEqual(source['category'], '05 - Venezuela')


if __name__ == '__main__':
    unittest.main()
