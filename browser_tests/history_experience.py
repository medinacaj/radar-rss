"""Latest is usable while archive downloads; failures are reversible with real UI."""
import unittest
from playwright.sync_api import expect
from count_regressions import CountRegressions

class HistoryExperience(CountRegressions):
    def test_refresh_explains_server_delay_then_loads_a_recent_publication(self):
        self.payloads=self.dataset(300,generation=-6*3600)
        old=self.payloads['meta.json']['generated_at']
        self.open()
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_have_attribute('data-state','warning')
        expect(self.page.locator('#refreshStatus')).to_contain_text('pendiente una publicación reciente')
        expect(self.page.locator('#lastUpdate')).to_contain_text('Recopilación pendiente')
        self.assertEqual(self.page.evaluate('state.generated'),old)
        self.payloads=self.dataset(300,offset=6000)
        recent=self.payloads['meta.json']['generated_at']
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_contain_text('Noticias actualizadas')
        expect(self.page.locator('#lastUpdate')).not_to_contain_text('Recopilación pendiente')
        self.assertEqual(self.page.evaluate('state.generated'),recent)
        self.assertFalse(self.errors)

    def test_latest_can_be_read_before_archive_completes(self):
        self.hold=True;self.open()
        self.page.wait_for_function('()=>state.historyLoading')
        self.assertEqual(self.page.evaluate('state.items.length'),300)
        expect(self.page.locator('#historyProgress')).to_be_visible()
        expect(self.page.locator('#historyProgressText')).to_contain_text('300 noticias disponibles')
        row=self.page.locator('#articleGrid .article-card').first
        with self.page.expect_popup() as opened:
            row.locator('.article-title a').click()
        opened.value.close()
        expect(self.page.locator('#articleReaderDialog')).to_be_hidden()
        self.release();self.page.wait_for_function('()=>state.historyLoaded')
        self.assertEqual(self.page.evaluate('state.items.length'),5000)
        expect(self.page.locator('#historyProgress')).to_be_hidden()
        self.assertFalse(self.errors)

    def test_abort_keeps_latest_and_retry_recovers_the_complete_archive(self):
        self.hold=True;self.open();self.page.wait_for_function('()=>state.historyLoading')
        self.page.evaluate('historyAbort.abort()');self.page.wait_for_function('()=>state.historyFailed&&!state.historyLoading')
        self.assertEqual(self.page.evaluate('state.items.length'),300)
        expect(self.page.locator('#historyRetry')).to_be_visible()
        expect(self.page.locator('#articleGrid .article-card').first).to_be_visible()
        self.pending.clear();self.hold=False
        self.page.locator('#historyRetry').click();self.page.wait_for_function('()=>state.historyLoaded')
        self.assertEqual(self.page.evaluate('state.items.length'),5000)
        expect(self.page.locator('#historyProgress')).to_be_hidden()
        self.assertFalse(self.errors)

if __name__=='__main__':
    suite=unittest.TestSuite(HistoryExperience(name) for name in ('test_refresh_explains_server_delay_then_loads_a_recent_publication','test_latest_can_be_read_before_archive_completes','test_abort_keeps_latest_and_retry_recovers_the_complete_archive'))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
