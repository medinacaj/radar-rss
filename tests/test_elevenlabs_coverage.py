"""Offline regression for ElevenLabs coverage in the AI category.

This does not assert that Google News currently returns a particular article.
"""
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collect import parse_opml

SOURCE_NAME = "RADAR — ElevenLabs | video y herramientas IA"


class ElevenLabsCoverageTests(unittest.TestCase):
    def test_elevenlabs_video_radar_is_unique_and_in_ai(self):
        sources = parse_opml(ROOT / "sources/feeds.opml")
        matches = [source for source in sources if source["name"] == SOURCE_NAME]
        self.assertEqual(len(matches), 1)
        source = matches[0]
        self.assertEqual(source["category"], "01 - Inteligencia Artificial")
        self.assertTrue(source["is_radar"])
        self.assertEqual(source["website"], "https://elevenlabs.io/blog")

        parsed = urlsplit(source["url"])
        self.assertEqual((parsed.scheme, parsed.hostname), ("https", "news.google.com"))
        params = parse_qs(parsed.query)
        query = params["q"][0]
        self.assertIn("ElevenLabs", query)
        self.assertIn("video", query)
        self.assertIn("ElevenCreative", query)
        self.assertIn("MCP", query)
        self.assertIn("when:45d", query)
        self.assertEqual(params["hl"], ["es-419"])
        self.assertEqual(params["gl"], ["CL"])


if __name__ == "__main__":
    unittest.main()
