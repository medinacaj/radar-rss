"""Offline browser regressions for overlapping selections and saved searches.

Run with the same Playwright dependency as responsive_smoke.py.
Set RADAR_CHROMIUM_EXECUTABLE to use an installed Chromium.
"""
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
import responsive_smoke as fixtures


class ConcepcionRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.playwright = sync_playwright().start()
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
        cls.browser = cls.playwright.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(service_workers='block')
        self.context.route('**/*', lambda route: route.continue_()
                           if urlsplit(route.request.url).hostname == '127.0.0.1'
                           else route.abort())
        self.page = self.context.new_page()
        self.page.route('**/data/**', fixtures.make_route)
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.wait_for_function('() => state.ready && document.querySelector(".article-card")')

    def tearDown(self):
        self.context.close()

    def test_partial_latam_selection_is_completed_without_removing_concepcion(self):
        self.page.evaluate("""() => {
            localStorage.setItem('radar-v12-preferences', JSON.stringify({mine:true,
                categories:['01 - Inteligencia Artificial','07 - Concepción'],briefing:'mine'}));
        }""")
        self.page.reload()
        self.page.wait_for_function('() => state.ready && document.querySelector(".article-card")')
        latam = self.page.locator('#v12MineCategories button').filter(has_text='Latinoamérica')
        self.assertEqual(latam.get_attribute('aria-pressed'), 'false')
        latam.evaluate('(button) => button.click()')
        selected = self.page.evaluate("JSON.parse(localStorage.getItem('radar-v12-preferences')).categories")
        self.assertEqual(set(selected), set(fixtures.CATEGORIES) - {'02 - Tecnología', '03 - Internacionales'})
        latam.evaluate('(button) => button.click()')
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('radar-v12-preferences')).categories"),
                         ['01 - Inteligencia Artificial'])

    def test_new_chile_saved_search_preserves_geographic_scope(self):
        self.page.evaluate("location.hash='#region/chile'")
        self.page.wait_for_function("() => document.querySelectorAll('#articleGrid>.article-card').length===5")
        before = self.page.locator('#articleGrid>.article-card').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)')
        self.page.evaluate("document.getElementById('v12SaveSearch').click()")
        self.page.locator('.v12-saved-open').evaluate('(button)=>button.click()')
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.evaluate('location.hash'), '#region/chile')
        self.assertEqual(self.page.locator('#articleGrid>.article-card').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)'), before)

    def test_import_event_refreshes_selection_and_saved_searches_without_reload(self):
        self.page.evaluate("""() => {
            localStorage.setItem('radar-v12-preferences', JSON.stringify({mine:true,
                categories:['07 - Concepción'],briefing:'cat:07 - Concepción'}));
            localStorage.setItem('radar-v12-saved-searches',JSON.stringify([
                {label:'Mi búsqueda restaurada',query:'',geo:'chile',age:0,category:'all',feed:''}]));
            localStorage.setItem('radar-lite','true');
            window.dispatchEvent(new Event('radar-preferences-imported'));
        }""")
        self.assertEqual(self.page.evaluate('window.RadarV12.briefingCategories()'), ['07 - Concepción'])
        self.assertEqual(self.page.locator('.v12-saved-open').all_text_contents(), ['Mi búsqueda restaurada'])
        self.assertTrue(self.page.evaluate('state.lite && document.body.classList.contains("lite")'))

    def test_restoring_chile_search_from_another_route_preserves_source(self):
        self.page.evaluate("location.hash='#region/chile'")
        self.page.wait_for_function("() => document.querySelectorAll('#articleGrid>.article-card').length===5")
        self.page.locator('#sidebarFeedOptions > summary').click()
        self.page.locator('#sourceSelect').select_option('medio-3')
        self.page.evaluate("document.getElementById('v12SaveSearch').click()")
        self.page.evaluate("location.hash='#noticias'")
        self.page.wait_for_function("() => document.getElementById('feedHeading').textContent==='Todas las noticias'")
        self.page.locator('.v12-saved-open').evaluate('(button)=>button.click()')
        self.page.wait_for_function("() => document.getElementById('feedHeading').textContent==='Chile'")
        self.assertEqual(self.page.locator('#sourceSelect').input_value(), 'medio-3')
        self.assertEqual(self.page.locator('#articleGrid>.article-card').count(), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
