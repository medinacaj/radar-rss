"""Regression contracts for the approved editorial + technology theme (issue #129).

These offline checks guard the design tokens, responsive and motion hooks.
Real browser alignment and contrast checks are in browser_tests/dimension_regressions.py.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "web" / "dimension.css").read_text(encoding="utf-8")
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
SW = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")


class EditorialTechDesignTests(unittest.TestCase):
    def test_single_active_theme_in_the_existing_stylesheet(self):
        self.assertEqual(HTML.count('href="./dimension.css?v=4.0.0"'), 1)
        self.assertNotIn('href="./editorial-tech.css"', HTML)
        self.assertEqual(CSS.count("Editorial + tecnológico — capa de diseño principal"), 1)
        self.assertIn("--radar-content-width:1450px", CSS)
        self.assertIn("--radar-page-gutter:clamp(16px,2.6vw,44px)", CSS)

    def test_dark_and_light_contrast_families(self):
        for token in ("--bg:#10151d", "--surface:#202a36",
                      "--accent:#ff8968", "--action-ink:#171d27",
                      "--bg:#edf1f5", "--surface:#ffffff",
                      "--accent:#b5422a", "--action-ink:#ffffff"):
            with self.subTest(token=token):
                self.assertIn(token, CSS)

    def test_routes_share_design_tokens_and_responsive_structure(self):
        selectors = (
            "#dashboardFeature>.article-card",
            "#dashboardRecent",
            "#articleGrid",
            "#coverageTools",
            ".agenda-section",
            ".briefing-section",
            ".settings-dialog",
            ".reader-title",
            ".sidebar",
            ".topbar",
        )
        for selector in selectors:
            with self.subTest(selector=selector):
                self.assertIn(selector, CSS)
        for breakpoint in ("max-width:1200px", "max-width:950px",
                           "max-width:710px", "max-width:420px"):
            self.assertIn(breakpoint, CSS)
        self.assertIn("prefers-reduced-motion:reduce", CSS)
        self.assertIn("forced-colors:active", CSS)
        self.assertIn(":focus-visible", CSS)

    def test_saved_card_title_preferences_remain_effective(self):
        self.assertIn("--radar-card-title-size", CSS)
        self.assertIn("--radar-title-scale", CSS)
        self.assertRegex(CSS, r"font-size:var\(--radar-reading-title-size\)!important")

    def test_pwa_cache_changes_atomically_with_theme(self):
        self.assertIn("const CACHE = 'radar-rss-v58'", SW)
        self.assertIn("'./dimension.css'", SW)
        self.assertIn('<meta name="theme-color" content="#10151d">', HTML)


if __name__ == "__main__":
    unittest.main()
