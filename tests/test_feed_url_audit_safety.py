"""The public OPML auditor must reject unsafe URLs the collector refuses."""
from pathlib import Path
import importlib.util
import tempfile
import unittest


def audit_module():
    import sys
    path = Path(__file__).resolve().parents[1] / "scripts" / "audit_feeds.py"
    spec = importlib.util.spec_from_file_location("radar_audit_feeds", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FeedUrlAuditSafety(unittest.TestCase):
    def test_rejects_private_url_credentials_invalid_port_and_backslashes(self):
        audit = audit_module()
        for url in [
            "http://localhost/rss",
            "https://127.0.0.1/feed.xml",
            "http://169.254.169.254/latest/meta-data",
            "https://[::1]/feed",
            "https://internal.local/rss",
            "https://user:pass@example.org/rss",
            "https://example.org:bad/rss",
            "https://example.org/\\private",
            "javascript:alert(1)",
            "https:///no-host",
            "https://example.org/feed\nHeader: injected",
        ]:
            with self.subTest(url=url):
                self.assertFalse(audit.safe_public_url(url), url)
        self.assertTrue(audit.safe_public_url("https://example.org/feed?topic=ai"))

    def test_auditor_flags_unsafe_feed_and_website_without_network(self):
        audit = audit_module()
        with tempfile.TemporaryDirectory() as folder:
            opml = Path(folder) / "sources.opml"
            opml.write_text(
                '<opml><body><outline text="Prueba">'
                '<outline title="Privada" xmlUrl="http://127.0.0.1/rss" />'
                '<outline title="Enlace no seguro" xmlUrl="https://example.org/rss" '
                'htmlUrl="https://user:password@example.org/" />'
                '<outline title="Pública" xmlUrl="https://good.example.org/feed" />'
                '</outline></body></opml>',
                encoding="utf-8",
            )
            report = audit.audit(opml)
        self.assertEqual(report["feed_count"], 3)
        self.assertEqual(
            sorted(issue["issue"] for issue in report["problems"]),
            ["invalid-feed-url", "invalid-website"],
        )


if __name__ == "__main__":
    unittest.main()
