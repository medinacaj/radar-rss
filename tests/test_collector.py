import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import collect

class ReaderTests(unittest.TestCase):
    def test_opml_has_enough_unique_feeds(self):
        # Sin número fijo: agregar o retirar una fuente no debe romper el despliegue.
        feeds = collect.parse_opml(ROOT / 'sources' / 'feeds.opml')
        self.assertGreaterEqual(len(feeds), 100)
        self.assertEqual(len(set(x['url'] for x in feeds)), len(feeds))
        self.assertEqual(len(set(x['id'] for x in feeds)), len(feeds))
        original_categories = {
            '01 - Inteligencia Artificial', '02 - Tecnología', '03 - Internacionales',
            '04 - Chile', '05 - Venezuela', '06 - Latinoamérica',
        }
        self.assertTrue(original_categories.issubset({x['category'] for x in feeds}))

    def test_display_name_keeps_informative_prefixes(self):
        self.assertEqual(collect.display_name('MEDIO — El Pitazo'), 'El Pitazo')
        self.assertEqual(collect.display_name('REGIONAL — La Prensa de Monagas'), 'La Prensa de Monagas')
        self.assertEqual(collect.display_name('SÁTIRA — El Chigüire Bipolar'), 'SÁTIRA — El Chigüire Bipolar')
        self.assertEqual(collect.display_name('MEDIO —'), 'MEDIO —')

    def test_get_feed_retries_transient_errors_only(self):
        calls = []
        def flaky(url):
            calls.append(url)
            if len(calls) == 1:
                raise collect.requests.ConnectionError('reset')
            return b'<rss/>'
        original, wait = collect._get_feed_once, collect.RETRY_WAIT_SECONDS
        collect._get_feed_once, collect.RETRY_WAIT_SECONDS = flaky, 0
        try:
            self.assertEqual(collect.get_feed('https://example.com/feed'), b'<rss/>')
            self.assertEqual(len(calls), 2)
            calls.clear()
            def forbidden(url):
                calls.append(url)
                response = SimpleNamespace(status_code=403)
                raise collect.requests.HTTPError('403', response=response)
            collect._get_feed_once = forbidden
            with self.assertRaises(collect.requests.HTTPError):
                collect.get_feed('https://example.com/feed')
            self.assertEqual(len(calls), 1)  # Un bloqueo deliberado no se reintenta.
        finally:
            collect._get_feed_once, collect.RETRY_WAIT_SECONDS = original, wait

    def test_retry_uses_bounded_jitter(self):
        calls = []
        def fail_once(url):
            calls.append(url)
            if len(calls) == 1:
                raise collect.requests.Timeout('timeout')
            return b'<rss/>'
        with patch.object(collect, '_get_feed_once', side_effect=fail_once), \
             patch.object(collect.random, 'random', return_value=0.5), \
             patch.object(collect.time, 'sleep') as sleep:
            self.assertEqual(collect.get_feed('https://example.com/feed'), b'<rss/>')
            self.assertEqual(len(calls), 2)
            sleep.assert_called_once_with(6)

    def test_reject_unsafe_article_links(self):
        self.assertIsNone(collect.safe_web_url('javascript:alert(1)'))
        self.assertIsNone(collect.safe_web_url('file:///etc/passwd'))
        self.assertIsNone(collect.safe_web_url('https://user:pass@website.com/'))

    def test_opml_excludes_private_or_executable_feed_destinations(self):
        import tempfile
        invalid = [
            'javascript:alert(1)', 'https://admin:pass@example.com/rss',
            'https://127.0.0.1/rss', 'http://localhost:8080/rss',
            'https://[::1]/rss', 'https://internal.local/rss',
            'https:///missing-host', 'https://example.org:bad/rss',
            'https://example.org/\\\\secret',
        ]
        for url in invalid:
            with self.subTest(url=url):
                self.assertIsNone(collect.safe_web_url(url))
        self.assertEqual(collect.safe_web_url(' https://example.com/rss?a=1 '), 'https://example.com/rss?a=1')
        xml = ("<opml><body><outline text='Seguridad'>"
               "<outline xmlUrl='https://example.org/rss' title='Buena'/>"
               "<outline xmlUrl='http://localhost/private' title='Local'/>"
               "<outline xmlUrl='https://admin:secret@example.org/rss' title='Credenciales'/>"
               "<outline xmlUrl='javascript:alert(1)' title='Script'/>"
               "</outline></body></opml>")
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / 'feeds.opml'
            file.write_text(xml, encoding='utf-8')
            entries = collect.parse_opml(file)
        self.assertEqual([entry['name'] for entry in entries], ['Buena'])
        self.assertEqual(entries[0]['url'], 'https://example.org/rss')

    def test_preview_sanitizes_markup_and_script(self):
        text, image = collect.extract_html('<script>bad()</script><p>Hola <b>mundo</b></p><img src="https://example.com/a.jpg">')
        self.assertEqual(text, 'Hola mundo')
        self.assertEqual(image, 'https://example.com/a.jpg')

    def test_article_entry_data(self):
        source = {'id':'abc', 'name':'Fuente', 'category':'01 - Inteligencia Artificial', 'is_radar':False}
        entry = {'link':'https://example.com/item?utm_source=example','title':'Titular','summary':'Resumen'}
        result = collect.make_item(entry, source, datetime(2026,10,17,tzinfo=timezone.utc))
        self.assertEqual(result['title'], 'Titular')
        self.assertEqual(result['categories'], ['01 - Inteligencia Artificial'])
        self.assertIsNone(result['published_at'])


    def test_fallback_excerpt_from_atom_body_without_invention(self):
        article={'summary':'<img src="https://medio.test/a.jpg">',
                 'content':[{'value':'<p>La noticia incluye datos públicos del evento.</p>'}]}
        self.assertEqual(collect.readable_summary(article,'Titular'),
                         'La noticia incluye datos públicos del evento.')
        title_only={'summary':'<p>Titular</p>'}
        self.assertEqual(collect.readable_summary(title_only,'Titular'),'')
        self.assertEqual(collect.readable_summary({},'Titular'),'')
        self.assertEqual(collect.readable_summary({'subtitle':'Dato breve'},'Titular'),'Dato breve')

    def test_make_item_uses_content_when_rss_summary_missing(self):
        source={'id':'a','name':'Medio','category':'03 - Internacionales','is_radar':False}
        entry={'link':'https://medio.test/original','title':'Titular',
               'content':[{'value':'<section>Extracto publicado en el contenido Atom.</section>'}]}
        item=collect.make_item(entry,source,datetime(2026,10,19,tzinfo=timezone.utc))
        self.assertEqual(item['summary'],'Extracto publicado en el contenido Atom.')

    def test_rss_xml_parser_without_network(self):
        xml = b"""<?xml version='1.0'?><rss version='2.0'><channel><title>Test</title>
        <item><title>Ultima noticia</title><link>https://example.net/post</link>
        <description>Breve resumen</description><pubDate>Sat, 17 Oct 2026 13:00:00 GMT</pubDate>
        </item></channel></rss>"""
        parsed = collect.feedparser.parse(xml)
        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.entries[0]['title'], 'Ultima noticia')
        self.assertIsNotNone(collect.entry_date(parsed.entries[0]))

    def test_atom_xml_parser_without_network(self):
        xml = b"""<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'>
        <title>Prueba</title><entry><title>Evento</title>
        <link rel='alternate' href='https://example.net/atom-item' />
        <updated>2026-10-17T10:00:00Z</updated><summary>Texto de prueba</summary>
        </entry></feed>"""
        parsed = collect.feedparser.parse(xml)
        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.entries[0]['link'], 'https://example.net/atom-item')


    def test_collect_generates_deduplicated_static_data(self):
        import json
        import tempfile
        from unittest.mock import patch
        sample = b"""<rss version='2.0'><channel><title>Test</title><item>
        <title>Noticia compartida</title><link>https://example.net/item</link>
        <description>Contenido breve</description>
        <pubDate>Sat, 17 Oct 2026 13:00:00 GMT</pubDate>
        </item></channel></rss>"""
        opml = """<opml version='1.0'><body><outline text='01 - IA'>
        <outline type='rss' title='A' xmlUrl='https://a.example.net/rss' />
        <outline type='rss' title='B' xmlUrl='https://b.example.net/rss' />
        </outline></body></opml>"""
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            src = base / 'feeds.opml'; src.write_text(opml, encoding='utf-8')
            with patch.object(collect, 'get_feed', return_value=sample):
                result = collect.collect(src, base / 'webdata', days=45, workers=2, max_per_feed=5)
            self.assertEqual(result['sources'], 2)
            self.assertEqual(result['articles'], 1)
            items = json.loads((base / 'webdata' / 'articles.json').read_text())['items']
            self.assertEqual(len(items[0]['source_ids']), 2)


class PublishGuardTests(unittest.TestCase):
    def build(self, root, failed, total=10):
        import json, tempfile
        items=[{'id':f'a{i}','title':f'T{i}','url':f'https://example.com/{i}'} for i in range(60)]
        collect.publish_partitioned(root, items, '2026-10-17T00:00:00Z')
        collect.write_json(root/'articles.json', {'version':2,'generated_at':'2026-10-17T00:00:00Z','items':items})
        collect.write_json(root/'sources.json', {'sources':[{'id':'s'}]})
        feeds=[{'id':str(i),'state':'error' if i<failed else 'ok'} for i in range(total)]
        collect.write_json(root/'status.json', {'feeds':feeds})
        collect.write_json(root/'trends.json', {'topics':[]})
        meta = json.loads((root/'meta.json').read_text())
        meta['events_version'] = 1
        collect.write_json(root/'meta.json', meta)
        collect.write_json(root/'events.json', {'version':1,'generated_at':meta['generated_at'], 'horizon_days':90, 'items':[], 'pending':[], 'sources':[]})
        (root.parent/'feeds').mkdir(exist_ok=True)
        (root.parent/'feeds'/'mas-cubierto.xml').write_text('<rss/>')

    def test_5000_article_archive_and_validator(self):
        import json
        import tempfile
        import validate_data
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'data'; root.mkdir()
            self.build(root, failed=0)
            articles = [{'id': f'item-{i}', 'title': f'Noticia {i}',
                         'url': f'https://example.com/{i}'} for i in range(5000)]
            collect.publish_partitioned(root, articles, '2026-10-17T00:00:00Z')
            collect.write_json(root / 'articles.json',
                               {'version': 2, 'generated_at': '2026-10-17T00:00:00Z',
                                'items': articles})
            metadata = json.loads((root / 'meta.json').read_text(encoding='utf-8'))
            metadata['events_version'] = 1
            collect.write_json(root / 'meta.json', metadata)
            self.assertEqual(len(metadata['archive_files']), 16)
            self.assertEqual(metadata['total_articles'], 5000)
            last = json.loads((root / 'archive-16.json').read_text())['items'][-1]
            self.assertEqual(last['id'], 'item-4999')
            validate_data.check(root)

    def test_blocks_publication_when_many_feeds_fail(self):
        import tempfile
        sys.path.insert(0, str(ROOT / 'scripts'))
        import validate_data
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; root.mkdir()
            self.build(root, failed=3)
            validate_data.check(root)
            self.build(root, failed=5)
            with self.assertRaises(ValueError):
                validate_data.check(root)

if __name__ == '__main__':
    unittest.main()