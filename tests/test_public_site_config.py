"""Regression tests for the public Pages URL used by monitoring."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from site_config import DATA_URL, SITE_URL


class PublicSiteConfigTests(unittest.TestCase):
    def test_health_data_uses_repository_pages_url(self):
        self.assertEqual(SITE_URL, "https://medinacaj.github.io/radar-rss/")
        self.assertEqual(DATA_URL, SITE_URL + "data/")


if __name__ == "__main__":
    unittest.main()
