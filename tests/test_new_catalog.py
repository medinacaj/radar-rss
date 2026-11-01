"""Offline integrity and geography contracts for the expanded public catalog."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import parse_qs, urlsplit
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from collect import parse_opml
from audit_feeds import audit


class ExpandedCatalogTests(unittest.TestCase):
    def setUp(self):
        self.sources = parse_opml(ROOT / 'sources/feeds.opml')
        path = ROOT / 'sources/reliable-expansion-verification.json'
        self.expansion = json.loads(path.read_text()) if path.exists() else {'sources': []}
        self.additions = [r for r in self.expansion['sources'] if r.get('included')]
        self.ai_additions = json.loads((ROOT/'sources/spanish-ai-verification.json').read_text())['sources']
        self.world_additions = json.loads((ROOT/'sources/world-coverage-verification.json').read_text())['sources']

    def test_new_folders_have_local_and_international_channels(self):
        self.assertEqual(len(self.sources), 312)
        self.assertEqual(sum(s['category'] == '08 - Maturín / Monagas' for s in self.sources), 8)
        self.assertEqual(sum(s['category'].startswith('09 -') for s in self.sources), 0)
        self.assertEqual(audit(ROOT / 'sources/feeds.opml')['problem_count'], 0)

    def test_spanish_ai_and_technology_expansion_preserves_categories(self):
        urls = {item['url']: item for item in self.sources}
        spanish_feeds = [
            'https://www.agenciasinc.es/feed/Tecnologia',
            'https://planetachatbot.com/feed/',
            'https://www.microsiervos.com/index.xml',
            'https://computerhoy.20minutos.es/rss',
            'https://www.profesionalreview.com/feed/',
        ]
        for url in spanish_feeds:
            self.assertIn(url, urls)
            self.assertIn(urls[url]['category'], ('01 - Inteligencia Artificial', '02 - Tecnología'))
        self.assertEqual(len(set(item['id'] for item in self.sources)), 312)
        expansion = json.loads((ROOT / 'sources/ia-technology-verification.json').read_text())['sources']
        self.assertEqual(len(expansion), 27)
        self.assertEqual(len({item['feed'] for item in expansion}), 27)
        for item in expansion:
            self.assertIn(item['feed'], urls)
            self.assertEqual(urls[item['feed']]['name'], item['name'])
            self.assertEqual(urls[item['feed']]['category'], item['category'])
            self.assertEqual(urls[item['feed']]['id'], hashlib.sha256(item['feed'].encode()).hexdigest()[:16])
            self.assertEqual(item['status'], 'pendiente_validacion_operativa')
            self.assertIsNone(item['entries_observed'])

    def test_original_211_entries_are_unchanged(self):
        records = json.loads((ROOT / 'sources/discovery-verification.json').read_text())['sources']
        additions = {record['feed'] for record in records + self.additions + self.ai_additions + self.world_additions}
        expanded = json.loads((ROOT / 'sources/ia-technology-verification.json').read_text())['sources']
        additions.update(record['feed'] for record in expanded)
        originals = [s for s in self.sources if s['url'] not in additions and s['name'] != 'RADAR — ElevenLabs | video y herramientas IA']
        digest = hashlib.sha256(json.dumps(originals, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, '2e34363f0a62c2e6d348850216a19bf1921db26eb7c4b1ec83b513093b6f303c')

    def test_source_expansion_preserves_all_original_221_records(self):
        additions = {r['feed'] for r in self.additions + self.ai_additions + self.world_additions}
        additions.update(r['feed'] for r in json.loads((ROOT/'sources/ia-technology-verification.json').read_text())['sources'])
        originals = [s for s in self.sources if s['url'] not in additions and s['name'] != 'RADAR — ElevenLabs | video y herramientas IA']
        digest = hashlib.sha256(json.dumps(originals, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, 'b83e08b187155adc406677267109f4ca4f0618f2060c0c46e06752fdf7054683')

    def test_added_sources_have_dated_observations_and_match_catalog(self):
        self.assertEqual(len(self.additions), 23)
        catalog = {s['url']:s for s in self.sources}
        for record in self.additions:
            self.assertIn(record['feed'], catalog)
            source = catalog[record['feed']]
            self.assertEqual((source['name'],source['category'],source['website']),
                             (record['name'],record['category'],record['website']))
            self.assertEqual(record['http_status'],200)
            self.assertEqual(record['status'],'rss_observed')
            self.assertGreater(record['recent_dated_entries'],0)
            verified = datetime.fromisoformat(record['verified_at'].replace('Z','+00:00'))
            published = datetime.fromisoformat(record['last_published_at'].replace('Z','+00:00'))
            self.assertTrue(verified-timedelta(days=45)<=published<=verified+timedelta(days=1))
            self.assertEqual(len(record['response_sha256']),64)
            if source['is_radar']:
                self.assertTrue(source['name'].startswith('RADAR — '))
                query = parse_qs(urlsplit(source['url']).query)
                self.assertEqual(query['q'],[record['query']])
                self.assertIn(query['hl'][0],('es','es-419'))
                if source['category'].startswith('08 -'):
                    self.assertIn('intitle:Monagas',query['q'][0])
                    self.assertIn('intitle:Maturín',query['q'][0])
            else:
                self.assertEqual(record['feed_language'],'es-ES')
                self.assertEqual(urlsplit(source['url']).hostname,'www.billboard.com')

    def test_current_revalidation_does_not_overwrite_historical_observations(self):
        previous = {r['feed'] for r in json.loads((ROOT/'sources/discovery-verification.json').read_text())['sources']}
        records = self.expansion.get('revalidated_sources',[])
        self.assertEqual({r['feed'] for r in records},previous)
        for record in records:
            self.assertEqual(record['status'],'rss_observed')
            self.assertEqual(record['http_status'],200)
            self.assertGreater(record['recent_dated_entries'],0)

    def test_discovery_records_are_explicitly_unverified_and_match_catalog(self):
        records = json.loads((ROOT / 'sources/discovery-verification.json').read_text())['sources']
        recorded = {record['feed'] for record in records}
        new = [s for s in self.sources if s['url'] in recorded]
        self.assertEqual({s['url'] for s in new}, {r['feed'] for r in records})
        self.assertEqual(len(records), 10)
        for record in records:
            self.assertEqual(record['status'], 'pendiente_conectividad')
            self.assertIsNone(record['entries_observed'])
            self.assertIsNone(record['last_published_at'])
            url = urlsplit(record['feed'])
            self.assertEqual(url.hostname, 'news.google.com')
            query = parse_qs(url.query)['q'][0]
            self.assertEqual(query, record['query'])
            self.assertNotIn('gl=CL', record['feed'])

    def test_spanish_cultural_channels_are_in_international_and_keep_ids(self):
        records = json.loads((ROOT / 'sources/discovery-verification.json').read_text())['sources']
        culture = [record for record in records if record['category'] == '03 - Internacionales']
        self.assertEqual(len(culture), 4)
        self.assertEqual({urlsplit(record['website']).hostname for record in culture},
                         {'www.bbc.com', 'efe.com', 'elpais.com', 'es.euronews.com'})
        by_url = {source['url']: source for source in self.sources}
        for record in culture:
            source = by_url[record['feed']]
            self.assertEqual(source['category'], '03 - Internacionales')
            self.assertEqual(source['id'], hashlib.sha256(record['feed'].encode()).hexdigest()[:16])
            self.assertEqual(parse_qs(urlsplit(source['url']).query)['hl'], ['es'])
        self.assertFalse(any(parse_qs(urlsplit(source['url']).query).get('hl') == ['en-US']
                             for source in by_url.values() if source['url'] in {r['feed'] for r in records}))

    def test_generated_catalog_matches_opml(self):
        data = json.loads((ROOT / 'web/data/sources.json').read_text())
        self.assertEqual(data['sources'], self.sources)
        self.assertEqual(len(data['categories']), 8)

    def test_monagas_is_venezuelan_and_culture_is_not_a_geographic_subset(self):
        script = """
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/v12.js','utf8');
const categories=JSON.parse(fs.readFileSync('web/data/sources.json')).categories;
const context=vm.createContext({state:{categories},window:{},localStorage:{getItem:()=>null}});
vm.runInContext(source.slice(0,source.indexOf('  const display ='))+
 '\\nwindow.inGeo=inGeo;window.geoCats=geoCats;})();',context);
console.log(JSON.stringify({venezuela:context.window.geoCats('venezuela'),latam:context.window.geoCats('latam'),
 local:context.window.inGeo({categories:['08 - Maturín / Monagas']},'venezuela'),
 culture:context.window.inGeo({categories:['09 - Cultura y entretenimiento internacional']},'latam')}));
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data['venezuela'], ['05 - Venezuela', '08 - Maturín / Monagas'])
        self.assertIn('08 - Maturín / Monagas', data['latam'])
        self.assertNotIn('09 - Cultura y entretenimiento internacional', data['latam'])
        self.assertTrue(data['local'])
        self.assertFalse(data['culture'])
