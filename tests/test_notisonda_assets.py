"""Validate public raster exports without external requests or image libraries."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'

class HeadTags(HTMLParser):
    def __init__(self,text):
        super().__init__();self.tags=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        self.tags.append((tag,dict(attrs)))

def png_size(path):
    data=path.read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR':
        raise ValueError('Se esperaba un PNG exportado')
    return struct.unpack('>II',data[16:24])

class NotisondaAssetsTests(unittest.TestCase):
    def setUp(self):
        self.tags=HeadTags((WEB/'index.html').read_text()).tags

    def test_public_html_has_no_previous_product_name(self):
        self.assertNotRegex((WEB/'index.html').read_text(), r'(?i)notisonda')

    def test_calendar_script_version_advances_past_previous_identity(self):
        scripts = [urlsplit(a['src']) for tag, a in self.tags if tag == 'script' and 'src' in a]
        script = next(url for url in scripts if url.path.endswith('/agenda.js'))
        version = parse_qs(script.query)['v'][0]
        self.assertGreater(tuple(map(int, version.split('.'))), (1, 1, 1))

    def test_apple_touch_icon_is_a_real_png_with_its_advertised_size(self):
        attrs=next(attrs for tag,attrs in self.tags if tag=='link' and attrs.get('rel')=='apple-touch-icon')
        path=urlsplit(attrs['href']).path
        self.assertEqual(Path(path).suffix,'.png')
        self.assertEqual(attrs['sizes'], '180x180')
        self.assertEqual(png_size(WEB/path.removeprefix('./')),(180,180))

    def test_open_graph_and_twitter_share_the_same_real_1200x630_png(self):
        meta={a.get('property') or a.get('name'):a.get('content') for t,a in self.tags if t=='meta'}
        url=meta['og:image']
        self.assertEqual(meta['twitter:image'],url)
        self.assertEqual(urlsplit(url).netloc,'medinacaj.github.io')
        self.assertTrue(urlsplit(url).path.startswith('/radar-rss/'))
        self.assertEqual(Path(urlsplit(url).path).suffix,'.png')
        self.assertEqual(meta.get('og:image:type'),'image/png')
        self.assertEqual(png_size(WEB/Path(urlsplit(url).path).name),(1200,630))

    def test_installable_icons_include_real_png_sizes_and_maskable(self):
        manifest=json.loads((WEB/'manifest.webmanifest').read_text())
        self.assertEqual(manifest['short_name'], 'Radar-RSS')
        self.assertTrue(manifest['name'].startswith('Radar-RSS'))
        self.assertEqual(manifest['start_url'], './#inicio')
        icons=[i for i in manifest['icons'] if i.get('type')=='image/png']
        self.assertTrue(any(i['sizes']=='192x192' and i['purpose']=='any' for i in icons))
        self.assertTrue(any(i['sizes']=='512x512' and i['purpose']=='any' for i in icons))
        self.assertTrue(any(i['sizes']=='512x512' and i['purpose']=='maskable' for i in icons))
        for icon in icons:
            self.assertEqual(png_size(WEB/urlsplit(icon['src']).path.removeprefix('./')),tuple(map(int,icon['sizes'].split('x'))))

    def test_historical_pngs_and_original_user_vector_design_are_preserved(self):
        historical={
            'radar-logo.png':'2ee133b904b145f77a039636d1cfc85b9b9e361e5d3bc4853621fdc4ef8fce89',
            'icon-192.png':'4af8318bada8df5201b98f8c7f4e1011c5d11f66925ca8f3f79370cedd165d7d',
            'icon-512.png':'81502540c280c5b9a24986830ec992705509ed45559f3b339dea3f979f546099',
            'icon-maskable-512.png':'775daa7e773eb6091f7ed05e418cf8950718e3cbdbd7d08cc32070e99fe578bb',
            'social-card.png':'567d8f8166000c0fcf1ced818a48aaa1121b7d20c1eed7c44ef30b2d2b2e778e'}
        vectors={'favicon.svg':'90f5478438eb3d8e317fdea5506d77b76af65813b420bf45ec5e411061bbb0fb',
                 'icon-maskable.svg':'5f4c3e159675b6297c0df9c0c51ff1864f3460ef432b09e4c9cb1f0aca3dc57e',
                 'social-card.svg':'40d6a8c4833028c83437c5926893ffa8621ca05b55148052f35f63774a45dbb1'}
        for filename,digest in historical.items():
            self.assertEqual(hashlib.sha256((WEB/filename).read_bytes()).hexdigest(),digest)
        for filename,digest in vectors.items():
            self.assertEqual(hashlib.sha256((WEB/filename).read_bytes().rstrip()).hexdigest(),digest)
