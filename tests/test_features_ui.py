"""Funciones editoriales de la interfaz: estructura y conexiones con app.js."""
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class FeaturesUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        cls.app = (ROOT / 'web/app.js').read_text(encoding='utf-8')
        cls.js = (ROOT / 'web/features.js').read_text(encoding='utf-8')
        cls.sw = (ROOT / 'web/sw.js').read_text(encoding='utf-8')

    def test_home_sections(self):
        for token in ['id="sinceVisit"', 'id="radarStage"', 'id="coveredList"', 'id="trendChips"', 'id="followedChips"']:
            self.assertIn(token, self.html)

    def test_briefing_view_and_routing(self):
        self.assertIn('id="briefingView"', self.html)
        self.assertIn("hash==='resumen'?'briefing'", self.app)
        self.assertIn("target==='briefing'?'#resumen'", self.app)
        self.assertIn('window.renderBriefing', self.js)
        self.assertIn("https://wa.me/?text=", self.js)
        self.assertIn('speechSynthesis', self.js)

    def test_extensions_are_resolved_at_event_time(self):
        # library.js y features.js amplían navigateFromHash después de que app.js registra el evento.
        self.assertIn("window.addEventListener('hashchange',()=>navigateFromHash());", self.app)
        self.assertNotIn("window.addEventListener('hashchange',navigateFromHash);", self.app)

    def test_reader_compare_and_thread(self):
        self.assertIn('function compareSection(item)', self.app)
        self.assertIn("'Cómo lo cuenta cada medio'", self.app)
        self.assertIn("'Seguimiento de esta historia'", self.js)

    def test_keyboard_shortcuts_documented(self):
        self.assertIn('id="shortcutsDialog"', self.html)
        for key in ["'j'", "'k'", "'o'", "'s'", "'m'"]:
            self.assertIn(key, self.js)

    def test_lite_mode_and_offline(self):
        self.assertIn('id="settingLite"', self.html)
        self.assertIn("&&!state.lite", self.app)
        worker_version = re.search(r"const CACHE = 'radar-rss-v(\d+)'", self.sw)
        self.assertIsNotNone(worker_version)
        self.assertIn("navigator.serviceWorker.register('./sw.js?v=" + worker_version.group(1) + "'", self.js)
        self.assertIn('url.origin !== self.location.origin', self.sw)
        self.assertIn('url.origin + url.pathname', self.sw)  # sin parámetros: caché acotada
        for asset in re.findall(r"'\./([^']+)'", self.sw):
            if asset and not asset.startswith('data/'):
                self.assertTrue((ROOT / 'web' / asset).exists(), asset)

    def test_manifest_icons_exist(self):
        manifest = json.loads((ROOT / 'web/manifest.webmanifest').read_text(encoding='utf-8'))
        purposes = {icon['purpose'] for icon in manifest['icons']}
        self.assertIn('maskable', purposes)
        for icon in manifest['icons']:
            self.assertTrue((ROOT / 'web' / urlsplit(icon['src']).path).exists(), icon['src'])

    def test_followed_topics_live_outside_category_nav(self):
        # library.js cuenta los botones de #categoryNav por posición: no agregar ahí.
        self.assertIn("$('categoryNav').after(briefingLink)", self.js)
        self.assertNotIn("$('categoryNav').append", self.js)


if __name__ == '__main__':
    unittest.main()
