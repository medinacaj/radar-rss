"""Visual refresh contracts: eight areas without duplicating controls or data."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "web/visual-refresh.css").read_text(encoding="utf-8")
SW = (ROOT / "web/sw.js").read_text(encoding="utf-8")
FEED = (ROOT / "web/feed-ux.js").read_text(encoding="utf-8")
APP = (ROOT / "web/app.js").read_text(encoding="utf-8")


class VisualRefreshTests(unittest.TestCase):
    def test_last_stylesheet_and_offline_copy(self):
        styles = re.findall(r'href="\./([^"?]+\.css)\?', HTML)
        self.assertEqual(styles[-1], "visual-refresh.css")
        self.assertIn("'./visual-refresh.css'", SW)
        self.assertNotIn("@import", CSS)
        self.assertNotIn("url(https:", CSS)

    def test_featured_story_is_compact_and_preserves_links(self):
        self.assertIn("#dashboardFeature>.article-card", CSS)
        self.assertIn("min-height:0;height:auto;max-height:none", CSS)
        self.assertIn("#dashboardFeature>.article-card .article-actions", CSS)
        self.assertIn("titleLink.addEventListener('click',event=>visitArticle(item,event))", APP)
        self.assertIn("cover.addEventListener('click',event=>visitArticle(item,event))", APP)

    def test_topbar_and_filter_count_are_single_access(self):
        self.assertIn('id="topbarTools"', HTML)
        self.assertIn("#topbarTools>details>summary", CSS)
        self.assertIn("topbarFilterCount.id='topbarFilterCount'", FEED)
        self.assertIn("const activeCount=active.filter(item=>!item.preference).length", FEED)
        self.assertNotIn("sidebar-reading sidebar-tools", FEED)

    def test_sidebar_and_carousel_cards_are_balanced(self):
        self.assertIn("#libraryFolderNav) .nav-count", CSS)
        self.assertIn("#dashboardRecent", CSS)
        self.assertIn("align-items:stretch;gap:14px", CSS)
        self.assertIn("scrollbar-width:thin", CSS)
        self.assertIn(".dashboard-recent-title", CSS)

    def test_typography_and_reader_preferences_are_preserved(self):
        self.assertIn(".article-title", CSS)
        self.assertIn("line-height:1.38", CSS)
        self.assertIn("var(--radar-reading-title-size)", (ROOT / "web/experience.css").read_text(encoding="utf-8"))
        self.assertIn("body.radar-hybrid.dimension.font-large", CSS)

    def test_accessible_panels_and_responsive_breakpoints(self):
        for breakpoint in ("1200px", "950px", "710px", "440px"):
            self.assertIn(f"max-width:{breakpoint}", CSS)
        self.assertIn("focus-visible", CSS)
        self.assertIn("#topbarTools #sidebarFeedOptions", CSS)
        self.assertIn("#topbarTools #presentationControl", CSS)
        self.assertIn("prefers-reduced-motion:reduce", CSS)
        self.assertIn("forced-colors:active", CSS)

    def test_genuine_loading_and_feedback_are_styled(self):
        self.assertIn("#dashboardFeature:empty::before", CSS)
        self.assertIn("#dashboardRecent:empty::before", CSS)
        self.assertIn("#articleGrid:empty::before", CSS)
        self.assertIn(".action-toast", CSS)
        self.assertIn("function actionToast(message,{undo}={})", APP)
        self.assertIn(".refresh-now[aria-busy='true']", CSS)


if __name__ == "__main__":
    unittest.main()
