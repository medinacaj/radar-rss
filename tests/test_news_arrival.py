"""Only newly published RSS items can trigger arrival effects."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class RSSArrivalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=(ROOT/'web/app.js').read_text(encoding='utf-8')
        cls.lib=(ROOT/'web/library.js').read_text(encoding='utf-8')
        cls.html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        cls.effects=(ROOT/'web/news-effects.js').read_text(encoding='utf-8')
        cls.style=(ROOT/'web/news-effects.css').read_text(encoding='utf-8')

    def test_published_and_first_boot_only(self):
        self.assertIn("const NEWS_SNAPSHOT_KEY='radar-last-visible-news-v1'",self.app)
        self.assertIn("window.dispatchEvent(new CustomEvent(",self.app)
        self.assertIn("publishNewRSSNews(previousIds)",self.app)
        self.assertIn("if(state.ready)publishNewRSSNews()",self.app)
        self.assertIn("if(!added.length)return",self.app)
        self.assertIn("window.requestAnimationFrame(",self.app)
        self.assertIn("previousIds=new Set(state.items.map",self.app)

    def test_folder_associations(self):
        self.assertIn('row.dataset.radarSourceIds=JSON.stringify(folderSources(kind,id))',self.lib)
        self.assertIn("folderSources(kind,id)",self.lib)
        self.assertIn("findCounts(items)",self.effects)
        self.assertIn("some(id=>sources.has(id))",self.effects)

    def test_only_real_new_items_and_accessibility(self):
        self.assertIn("radar:news-added",self.effects)
        self.assertIn("prefers-reduced-motion: reduce",self.effects)
        self.assertIn('if(prefersReducedMotion)return',self.effects)
        self.assertIn("radar-folder-arrived",self.effects)
        self.assertIn("radar-news-arrived",self.effects)
        self.assertIn("radar-rss-float-new",self.style)
        self.assertIn('@media(prefers-reduced-motion:reduce)',self.style)

    def test_assets_load_after_library(self):
        self.assertIn('news-effects.css?v=5.0.0',self.html)
        self.assertIn('news-effects.js?v=1.0.0',self.html)
        self.assertLess(self.html.index('library.js?v='),self.html.index('news-effects.js?v='))
