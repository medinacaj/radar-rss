"""Offline feed fallback regressions: source identity and failures stay transparent."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect
from audit_feeds import audit

NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)
RSS = b"""<rss version="2.0"><channel><title>Publisher</title>
<item><title>Noticia verificada</title><link>https://publisher.example/item</link>
<description>Breve sin inventar contenido.</description>
<pubDate>Wed, 11 Nov 2026 05:00:00 GMT</pubDate></item>
</channel></rss>"""


class FeedFallbackTests(TestCase):
    def test_catalog_keeps_original_source_ids(self):
        sources = collect.parse_opml(ROOT / "sources/feeds.opml")
        by_name = {s["name"]: s for s in sources}
        expected = {
            "MEDIO — El Androide Libre": (
                "https://www.elespanol.com/rss/elandroidelibre/",
                "https://feeds.feedburner.com/elandroidelibre",
            ),
            "MEDIO — Revista Emprendedores": (
                "https://emprendedores.es/feed/",
                "https://www.emprendedores.es/feed/",
            ),
            "MEDIO — Revista Venezolana de Gerencia": (
                "https://produccioncientificaluz.org/index.php/rvg/gateway/plugin/WebFeedGatewayPlugin/atom",
                "https://produccioncientifica.luz.edu.ve/index.php/rvg/gateway/plugin/WebFeedGatewayPlugin/rss",
            ),
        }
        for name, (primary, alternate) in expected.items():
            with self.subTest(name=name):
                source = by_name[name]
                self.assertEqual(source["url"], primary)
                self.assertNotIn("fallback_url", source)
                self.assertEqual(collect.FEED_FALLBACKS[primary], alternate)
                self.assertEqual(source["id"], sha256(primary.encode()).hexdigest()[:16])
        self.assertEqual(audit(ROOT / "sources/feeds.opml")["problem_count"], 0)

    def test_primary_success_does_not_request_alternate(self):
        source = {"id": "stable", "name": "Publisher", "category": "Technology",
                  "url": "https://www.elespanol.com/rss/elandroidelibre/",
                  "is_radar": False}
        with patch.object(collect, "get_feed", return_value=RSS) as get:
            items, status = collect.get_one(source, NOW, 10)
        self.assertEqual(status["state"], "ok")
        self.assertNotIn("fallback_used", status)
        self.assertEqual(items[0]["source_ids"], ["stable"])
        get.assert_called_once_with(source["url"])

    def test_fallback_works_without_changing_identity_or_hiding_primary_error(self):
        source = {"id": "stable", "name": "Publisher", "category": "Technology",
                  "url": "https://www.elespanol.com/rss/elandroidelibre/",
                  "is_radar": False}
        with patch.object(collect, "get_feed", side_effect=[
            collect.requests.HTTPError("404 Not Found"), RSS
        ]) as get:
            items, status = collect.get_one(source, NOW, 10)
        self.assertEqual(status["state"], "ok")
        self.assertTrue(status["fallback_used"])
        self.assertIn("404", status["primary_error"])
        self.assertEqual(items[0]["source_ids"], ["stable"])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.args[0], collect.FEED_FALLBACKS[source["url"]])

    def test_both_failures_remain_visible_and_trigger_alert(self):
        source = {"id": "stable", "name": "Publisher", "category": "Technology",
                  "url": "https://www.elespanol.com/rss/elandroidelibre/",
                  "is_radar": False}
        with patch.object(collect, "get_feed", side_effect=[
            collect.requests.HTTPError("404 Not Found"),
            collect.requests.HTTPError("403 Forbidden")
        ]):
            items, status = collect.get_one(source, NOW, 10)
        self.assertEqual(items, [])
        self.assertEqual(status["state"], "error")
        self.assertIn("404", status["error"])
        self.assertIn("403", status["error"])
        self.assertNotIn("fallback_used", status)

    def test_unlisted_source_still_reports_error_without_fetching_another_host(self):
        source = {"id": "stable", "name": "Publisher", "category": "Technology",
                  "url": "https://publisher.example/rss", "is_radar": False}
        with patch.object(collect, "get_feed", side_effect=collect.requests.HTTPError("403 Forbidden")) as get:
            items, status = collect.get_one(source, NOW, 10)
        self.assertEqual(items, [])
        self.assertEqual(status["state"], "error")
        get.assert_called_once_with(source["url"])


if __name__ == "__main__":
    import unittest
    unittest.main()
