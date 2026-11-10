"""Offline preservation, coverage and honest discovery evidence for new channels."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from collect import parse_opml
from audit_feeds import audit
from pending_catalog_history import before_pending_expansions


class AllCategoriesCatalogTests(unittest.TestCase):
    def setUp(self):
        self.sources = parse_opml(ROOT / 'sources/feeds.opml')
        path = ROOT / 'sources/all-categories-discovery-2026-11-10.json'
        self.record = json.loads(path.read_text()) if path.exists() else {'sources': []}
        self.additions = self.record['sources']

    def test_existing_409_source_identities_and_order_are_preserved(self):
        new = {s['feed'] for s in self.additions}
        original = [s for s in self.sources if s['url'] not in new]
        self.assertEqual(len(original), 409)
        digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, 'a23c1dd0510a7800da1b5a55c1b773c1300a23ba46fb771bb133d095181ffbbc')

    def test_each_existing_folder_gains_at_least_two_channels(self):
        counts = Counter(s['category'] for s in self.additions)
        self.assertEqual(len(counts), 11)
        self.assertEqual(set(counts), {s['category'] for s in self.sources})
        self.assertTrue(all(count >= 2 for count in counts.values()))
        self.assertEqual(len(self.sources), 409 + len(self.additions))

    def test_discovery_evidence_matches_catalog_without_invented_observations(self):
        self.assertTrue(self.additions)
        self.assertEqual(audit(ROOT / 'sources/feeds.opml')['problem_count'], 0)
        by_url = {s['url']: s for s in self.sources}
        self.assertEqual(len(by_url), len(self.sources))
        self.assertEqual(len({s['id'] for s in self.sources}), len(self.sources))
        checked = datetime.fromisoformat(self.record['checked_at'].replace('Z', '+00:00'))
        for row in self.additions:
            with self.subTest(source=row['name']):
                source = by_url[row['feed']]
                self.assertEqual((source['name'], source['category'], source['website']),
                                 (row['name'], row['category'], row['website']))
                self.assertEqual(source['id'], hashlib.sha256(row['feed'].encode()).hexdigest()[:16])
                self.assertEqual(source['id'], row['id'])
                self.assertEqual(urlsplit(row['feed']).scheme, 'https')
                self.assertEqual(urlsplit(row['website']).scheme, 'https')
                self.assertTrue(row['publisher_country'])
                self.assertTrue(row['rationale'])
                self.assertTrue(row['evidence_urls'])
                host = urlsplit(row['website']).hostname.removeprefix('www.')
                self.assertTrue(any(urlsplit(url).hostname.removeprefix('www.') == host for url in row['evidence_urls']))
                sample = row['sample_article']
                published = datetime.fromisoformat(sample['date']).replace(tzinfo=timezone.utc)
                self.assertTrue(sample['url'] and sample['title_short'])
                window = 730 if row['category'].startswith('11 -') else 45
                self.assertTrue(checked - timedelta(days=window) <= published <= checked + timedelta(days=1))
                evidence = row['verification']
                self.assertIn(evidence['method'], ('publisher_declared', 'rss_content_type_observed', 'primary_editorial_evidence'))
                self.assertFalse(evidence['feed_xml_parsed'])
                for key in ('http_status', 'entries_observed', 'response_sha256'):
                    self.assertIsNone(evidence[key])
                self.assertTrue(evidence['details'])

    def test_radar_channels_are_explicit_and_restrict_publisher_window_and_geography(self):
        self.assertTrue(self.additions)
        for row in self.additions:
            if row['provider'] == 'publisher':
                self.assertNotEqual(urlsplit(row['feed']).hostname, 'news.google.com')
                self.assertFalse(row['name'].startswith('RADAR — '))
                continue
            self.assertEqual(row['provider'], 'google-news-search')
            self.assertTrue(row['name'].startswith('RADAR — '))
            self.assertEqual(urlsplit(row['feed']).hostname, 'news.google.com')
            query = parse_qs(urlsplit(row['feed']).query)
            text = query['q'][0]
            domains = re.findall(r'site:([^\s()]+)', text)
            self.assertEqual(len(domains), 1)
            self.assertEqual(domains[0].split('/')[0].removeprefix('www.'),
                             urlsplit(row['website']).hostname.removeprefix('www.'))
            self.assertIn('when:730d' if row['category'].startswith('11 -') else 'when:45d', text)
            self.assertIn(query['hl'][0], ('es', 'es-419'))
            if row['category'].startswith(('07 -', '08 -')):
                if row['territorial_scope'] == 'municipality':
                    self.assertEqual(row['category'], '07 - Concepción')
                    self.assertIn(urlsplit(row['website']).hostname.removeprefix('www.'),
                                  ('santajuana.cl', 'munihualqui.cl'))
                else:
                    self.assertEqual(row['territorial_scope'], 'title_filter')
                    self.assertIn('intitle:', text)
                    self.assertRegex(text, r'Concepción|Biobío|Santa Juana|Maturín|Maturin|Monagas')

    def test_historical_snapshots_exclude_only_documented_new_channels(self):
        self.assertTrue(self.additions)
        unknown = {'url': 'https://future.example/feed', 'name': 'Future channel'}
        old = before_pending_expansions([*self.sources, unknown])
        self.assertIn(unknown, old)
        added = {s['feed'] for s in self.additions}
        self.assertFalse(any(s['url'] in added for s in old))


if __name__ == '__main__':
    unittest.main()
