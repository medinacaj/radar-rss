"""Public identity regression checks for Radar RSS (issue #181)."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class PublicBrandIdentityTests(unittest.TestCase):
    def test_legacy_svg_urls_show_current_radar_brand(self):
        # Keep the old URLs for bookmarks while never serving the obsolete N mark.
        aliases = {
            "favicon.svg": "radar-favicon.svg",
            "icon-maskable.svg": "radar-icon-maskable.svg",
        }
        for alias, canonical in aliases.items():
            with self.subTest(alias=alias):
                self.assertEqual(
                    (WEB / alias).read_bytes(),
                    (WEB / canonical).read_bytes(),
                )

    def test_old_public_png_urls_show_current_radar_brand(self):
        aliases = {
            "radar-logo.png": "radar-rss-mark.png",
            "icon-192.png": "radar-rss-icon-192.png",
            "icon-512.png": "radar-rss-icon-512.png",
            "icon-maskable-512.png": "radar-rss-maskable-512.png",
            "social-card.png": "radar-rss-social-card.png",
        }
        for alias, canonical in aliases.items():
            with self.subTest(alias=alias):
                self.assertEqual((WEB / alias).read_bytes(), (WEB / canonical).read_bytes())

    def test_public_assets_do_not_display_previous_name(self):
        # Historical Markdown and cache migration are intentionally retained.
        extensions = {".css", ".js", ".svg", ".html", ".json", ".webmanifest", ".txt"}
        for path in WEB.rglob("*"):
            if not path.is_file() or path.suffix not in extensions:
                continue
            with self.subTest(path=path.relative_to(WEB)):
                content = path.read_text(encoding="utf-8")
                if path.name == "sw.js":
                    # This is an intentional deletion key for prior PWA installs.
                    self.assertIn("key.startsWith('notisonda-')", content)
                    content = content.replace("key.startsWith('notisonda-')", "")
                self.assertNotIn("notisonda", content.lower())

    def test_index_and_manifest_reference_radar_assets(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        manifest = (WEB / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn("radar-rss-favicon-64.png", index)
        self.assertIn("radar-rss-apple-touch-icon.png", index)
        self.assertIn("radar-rss-icon-192.png", manifest)
        self.assertIn("radar-rss-maskable-512.png", manifest)


if __name__ == "__main__":
    unittest.main()
