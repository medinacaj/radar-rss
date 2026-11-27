"""Contratos de publicación: marca vigente y actualización PWA sin red externa."""
import json
import re
from pathlib import Path
import unittest

WEB = Path(__file__).resolve().parents[1] / "web"


class CurrentBrandTests(unittest.TestCase):
    def test_previous_brand_files_are_not_shipped_to_pages(self):
        obsolete = sorted(path.name for path in WEB.iterdir()
                          if path.is_file() and path.name.lower().startswith("notisonda-"))
        self.assertEqual(obsolete, [], "No se deben distribuir PNG históricos de la marca anterior")

    def test_entrypoint_and_manifest_only_advertise_radar_rss(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        manifest = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertNotIn("notisonda", page.lower())
        self.assertNotIn("notisonda", json.dumps(manifest).lower())
        self.assertIn("<title>Radar-RSS — Noticias con perspectiva</title>", page)
        self.assertEqual(manifest["short_name"], "Radar-RSS")
        self.assertIn("manifest.webmanifest?v=4", page)
        for icon in manifest["icons"]:
            self.assertRegex(icon["src"], r"^\./radar-rss-[\w-]+\.png\?v=2$")
        for label in ("radar-rss-favicon-64.png?v=2", "radar-rss-apple-touch-icon.png?v=2",
                      "radar-rss-social-card.png?v=2"):
            self.assertIn(label, page)

    def test_service_worker_version_matches_registration(self):
        worker = (WEB / "sw.js").read_text(encoding="utf-8")
        features = (WEB / "features.js").read_text(encoding="utf-8")
        page = (WEB / "index.html").read_text(encoding="utf-8")
        match = re.search(r"const CACHE = 'radar-rss-v(\d+)'", worker)
        self.assertIsNotNone(match)
        version = int(match.group(1))
        self.assertGreaterEqual(version, 82)
        self.assertIn(f"serviceWorker.register('./sw.js?v={version}'", features)
        self.assertIn("updateViaCache: 'none'", features)
        self.assertIn("features.js?v=1.4.2", page)
        # Migración: limpia cachés históricas sin borrar las de otras aplicaciones del origen.
        self.assertIn("key.startsWith('notisonda-')", worker)
        self.assertIn("key.startsWith('radar-rss-')", worker)


if __name__ == "__main__":
    unittest.main()
