"""Keep the advertised refresh cadence aligned with the actual scheduler.

The browser checks published snapshots; it does not fetch external RSS feeds.
No live network calls or credentials are necessary for these tests.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RefreshContractTests(unittest.TestCase):
    def test_hourly_collector_cadence_is_consistent(self):
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        app = (ROOT / "web/app.js").read_text(encoding="utf-8")
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        crons = re.findall(r"(?m)^\s*- cron:\s*[\"']([^\"']+)[\"']", workflow)
        self.assertEqual(crons, ["17 * * * *"], "Review any scheduling change with the UI and README")
        self.assertIn("cada hora", app)
        self.assertIn("cada hora", html)
        self.assertIn("cada hora", readme)
        self.assertNotIn("cada tres horas", readme)

    def test_refresh_checks_published_snapshot_not_feed_sources(self):
        app = (ROOT / "web/app.js").read_text(encoding="utf-8")
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        self.assertIn("dataFetch('./data/meta.json?check='+Date.now()", app)
        self.assertIn("no inicia una nueva recopilación RSS", html)
        self.assertIn("Última recopilación:", app)


if __name__ == "__main__":
    unittest.main()
