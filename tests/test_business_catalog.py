"""Offline preservation and traceability for the requested business sources."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit
from datetime import datetime, timedelta

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collect import parse_opml
from pending_catalog_history import before_pending_expansions


class BusinessCatalogTests(unittest.TestCase):
    def setUp(self):
        self.sources=before_pending_expansions(parse_opml(ROOT/'sources/feeds.opml'), keep='business')
        path=ROOT/'sources/business-sources-verification.json'
        self.record=json.loads(path.read_text()) if path.exists() else {'sources':[],'requests':[]}

    def test_the_311_existing_subscriptions_keep_their_ids_urls_names_and_folders(self):
        added={row['feed'] for row in self.record['sources']}
        original=[source for source in self.sources if source['url'] not in added]
        self.assertEqual(len(original),311)
        digest=hashlib.sha256(json.dumps(original,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest,'4e66c2aff0543cd680543ee5109c3c438f0657b814fb71713f927b21d1bfbe5b')

    def test_every_requested_publication_has_an_explicit_traceable_result(self):
        requested=self.record['requests']
        self.assertEqual({row['number'] for row in requested},set(range(1,101)))
        self.assertEqual(len(requested),100)
        by_id={s['id']:s for s in self.sources}
        for row in requested:
            self.assertTrue(row['requested_name'])
            self.assertTrue(row['reason'])
            self.assertTrue(row['status'])
            for source_id in row['catalog_source_ids']:
                self.assertIn(source_id,by_id)
            if row['status'].startswith('added_') or row['status']=='already_present':
                self.assertTrue(row['catalog_source_ids'])
                self.assertEqual(row['feed_urls'],[by_id[i]['url'] for i in row['catalog_source_ids']])

    def test_new_channels_match_the_catalog_and_observed_provider(self):
        added=self.record['sources']
        self.assertGreater(len(added),0)
        by_url={s['url']:s for s in self.sources}
        self.assertEqual(len(self.sources),len(by_url))
        self.assertEqual(len(self.sources),len({s['id'] for s in self.sources}))
        self.assertEqual(len(self.sources),311+len(added))
        for row in added:
            source=by_url[row['feed']]
            self.assertEqual((source['name'],source['category'],source['website']),(row['name'],row['category'],row['website']))
            self.assertEqual(source['id'],hashlib.sha256(row['feed'].encode()).hexdigest()[:16])
            self.assertEqual(row['status'],'rss_observed')
            self.assertEqual(row['http_status'],200)
            self.assertGreater(row['entries_observed'],0)
            self.assertGreater(row['recent_dated_entries'],0)
            self.assertEqual(len(row['response_sha256']),64)
            checked=datetime.fromisoformat(row['verified_at'].replace('Z','+00:00'))
            published=datetime.fromisoformat(row['last_published_at'].replace('Z','+00:00'))
            self.assertTrue(checked-timedelta(days=row['recency_days'])<=published<=checked+timedelta(days=1))
            if row['provider']=='google_news':
                self.assertTrue(source['is_radar'])
                self.assertTrue(source['name'].startswith('RADAR — '))
                self.assertEqual(urlsplit(row['feed']).hostname,'news.google.com')
                self.assertEqual(parse_qs(urlsplit(row['feed']).query)['q'],[row['query']])
            else:
                self.assertFalse(source['is_radar'])

    def test_verified_native_feeds_take_priority_without_duplicating_existing_publishers(self):
        results={row['number']:row for row in self.record['requests']}
        for number,url in {2:'https://tekiosmag.com/feed/',3:'https://contxto.com/es/feed/',
                           7:'https://elreferente.es/feed/'}.items():
            self.assertEqual(results[number]['status'],'added_native')
            self.assertEqual(results[number]['feed_urls'],[url])
        self.assertEqual(results[79]['status'],'already_present')
        self.assertEqual(results[79]['catalog_source_ids'],['8c1929e1bc86c3d9'])


if __name__=='__main__':unittest.main()
