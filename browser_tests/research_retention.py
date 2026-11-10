"""Old academic articles remain reachable from partitioned history and open publishers."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from playwright.sync_api import expect
from count_regressions import CountRegressions
from responsive_smoke import ensure_navigation


RESEARCH = '11 - Investigación y Gestión'


class ResearchRetention(CountRegressions):
    @staticmethod
    def dataset(total, offset=0, generation=0):
        docs = CountRegressions.dataset(total, offset, generation)
        opml = ET.parse(Path(__file__).resolve().parents[1] / 'sources/feeds.opml')
        docs['sources.json']['categories'] = [node.get('text') for node in opml.findall('./body/outline')]
        source = {'id':'research-journal', 'name':'MEDIO — Revista académica', 'category':RESEARCH,
                  'url':'https://journal.example/rss', 'website':'https://journal.example', 'is_radar':False}
        docs['sources.json']['sources'].append(source)
        stamp = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(timespec='milliseconds').replace('+00:00','Z')
        # These entries are absent from latest.json and arrive only in the final shard.
        for index, item in enumerate(docs[docs['meta.json']['archive_files'][-1]]['items'][-3:]):
            item.update(id=f'research-{index}', title=f'Estudio académico de gestión empresarial {index}',
                        url=f'https://journal.example/paper/{index}', source_ids=[source['id']],
                        source=source['name'], publisher='Revista académica', categories=[RESEARCH],
                        published_at=stamp, first_seen_at=stamp, image=None, summary='Resumen del editor')
        return docs

    def check_folder(self, width):
        self.page.set_viewport_size({'width':width, 'height':900})
        self.open()
        self.page.wait_for_function('() => state.historyLoaded')
        self.assertEqual(self.page.evaluate('state.items.length'),5000)
        ensure_navigation(self.page)
        folder = self.page.locator('#libraryFolderNav .system-folder-link').filter(has_text='Investigación y Gestión')
        expect(folder.locator('.nav-count')).to_have_text('3')
        folder.click()
        cards = self.page.locator('#articleGrid .article-card')
        expect(cards).to_have_count(3)
        expect(self.page.locator('#feedHeading')).to_have_text('Investigación y Gestión')
        first = cards.first
        link = first.locator('.article-title a')
        expect(link).to_have_attribute('href','https://journal.example/paper/0')
        original_date = self.payloads[self.payloads['meta.json']['archive_files'][-1]]['items'][-3]['published_at']
        expect(first.locator('time').first).to_have_attribute('datetime',original_date)
        with self.page.expect_popup() as opened:
            link.click()
        opened.value.close()
        expect(self.page.locator('#articleReaderDialog')).to_be_hidden()
        # Explicit reader preferences still apply to the expanded archive.
        self.page.locator('#settingsButton').click()
        self.page.locator('[data-settings-tab="reading"]').click()
        self.page.locator('#settingAge').select_option('90')
        self.page.locator('#closeSettings').click()
        expect(cards).to_have_count(0)
        self.page.locator('#settingsButton').click()
        self.page.locator('[data-settings-tab="reading"]').click()
        self.page.locator('#settingAge').select_option('0')
        self.page.locator('#closeSettings').click()
        expect(cards).to_have_count(3)
        self.assertFalse(self.errors)

    def test_mobile_folder(self):
        self.check_folder(375)

    def test_desktop_folder(self):
        self.check_folder(1440)


if __name__ == '__main__':
    suite = unittest.TestSuite(ResearchRetention(name) for name in ('test_mobile_folder','test_desktop_folder'))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
