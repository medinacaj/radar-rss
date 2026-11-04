"""Reader navigation and appearance checks with deterministic local RSS fixtures."""
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
import responsive_smoke as fixtures


class LayoutRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/'
        cls.driver = sync_playwright().start()
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
        cls.browser = cls.driver.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def open_page(self, width, scheme='light', mobile=False):
        context = self.browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=scheme,
                                           is_mobile=mobile, has_touch=mobile, service_workers='block')
        self.addCleanup(context.close)
        page = context.new_page()
        page.route('**/data/**', fixtures.make_route)
        page.route('https://example.com/**', lambda route: route.abort())
        page.goto(self.base)
        page.wait_for_function('() => state.ready && document.querySelector(".article-card")')
        return page

    def test_desktop_sidebar_persists_and_does_not_block_reader(self):
        page = self.open_page(1440)
        sidebar = page.locator('#appSidebar')
        self.assertTrue(sidebar.is_visible())
        self.assertEqual(page.locator('#menuToggle').get_attribute('aria-expanded'), 'true')
        self.assertFalse(page.locator('.page').evaluate('node => node.inert'))
        self.assertFalse(page.locator('#sidebarBackdrop').is_visible())
        bounds = sidebar.bounding_box()
        self.assertGreaterEqual(page.locator('.page').bounding_box()['x'], bounds['x'] + bounds['width'] - 1)
        page.evaluate("goTo('all')")
        page.wait_for_function("() => state.pageView==='feed'")
        self.assertTrue(sidebar.is_visible())
        page.locator('#menuToggle').click()
        self.assertFalse(sidebar.is_visible())
        self.assertEqual(page.evaluate("localStorage.getItem('radar-sidebar-collapsed')"), 'true')
        page.reload()
        page.wait_for_function('() => state.ready')
        self.assertFalse(sidebar.is_visible())
        page.locator('#menuToggle').click()
        self.assertTrue(sidebar.is_visible())
        self.assertEqual(page.locator('#sidebarResizeHandle').get_attribute('tabindex'), '0')
        page.locator('#sidebarResizeHandle').focus()
        page.keyboard.press('ArrowRight')
        self.assertEqual(page.evaluate("localStorage.getItem('radar-sidebar-width')"), '326')
        page.set_viewport_size({'width': 390, 'height': 844})
        self.assertFalse(sidebar.is_visible())
        page.set_viewport_size({'width': 1440, 'height': 900})
        self.assertTrue(sidebar.is_visible())

    def test_mobile_drawer_focus_escape_and_no_initial_overlay(self):
        page = self.open_page(390, mobile=True)
        self.assertFalse(page.locator('#appSidebar').is_visible())
        self.assertFalse(page.locator('.page').evaluate('node => node.inert'))
        self.assertFalse(page.locator('#sidebarBackdrop').is_visible())
        self.assertEqual(page.locator('.page').bounding_box()['x'], 0)
        page.locator('#menuToggle').click()
        self.assertTrue(page.locator('#appSidebar').is_visible())
        self.assertTrue(page.locator('.page').evaluate('node => node.inert'))
        self.assertTrue(page.evaluate("document.getElementById('appSidebar').contains(document.activeElement)"))
        page.locator('#sidebarNavigationToggle').focus()
        page.keyboard.press('Tab')
        self.assertTrue(page.evaluate("document.getElementById('appSidebar').contains(document.activeElement)"))
        page.keyboard.press('Escape')
        self.assertFalse(page.locator('#appSidebar').is_visible())
        self.assertEqual(page.evaluate('document.activeElement.id'), 'menuToggle')
        self.assertIsNone(page.evaluate("localStorage.getItem('radar-sidebar-collapsed')"))

    def test_system_theme_and_explicit_override_on_phone(self):
        page = self.open_page(390, 'dark', mobile=True)
        self.assertEqual(page.evaluate('state.theme'), 'system')
        self.assertFalse(page.locator('body').evaluate("node => node.classList.contains('light')"))
        page.emulate_media(color_scheme='light')
        page.wait_for_function("() => document.body.classList.contains('light')")
        page.locator('#themeToggle').click()
        self.assertEqual(page.evaluate('state.theme'), 'dark')
        page.reload()
        page.wait_for_function('() => state.ready')
        self.assertEqual(page.evaluate('state.theme'), 'dark')
        self.assertFalse(page.locator('body').evaluate("node => node.classList.contains('light')"))

    def test_compact_chrome_and_linkedin_capsule(self):
        for width in (375, 390, 768, 1024, 1440):
            with self.subTest(width=width):
                page = self.open_page(width)
                self.assertFalse(page.locator('#topicRail').is_visible())
                self.assertLessEqual(page.locator('.topbar').bounding_box()['height'], 68)
                self.assertTrue(page.locator('#settingsButton').is_visible())
                self.assertTrue(page.locator('#brandHome .brand-mark img').evaluate('img => img.complete && img.naturalWidth > 0'))
                capsule = page.locator('.footer-profile')
                self.assertEqual(capsule.get_attribute('href'), 'https://www.linkedin.com/in/medinacaj/')
                self.assertEqual(capsule.get_attribute('target'), '_blank')
                self.assertIn('noopener', capsule.get_attribute('rel'))
                self.assertEqual(' '.join(capsule.text_content().split()), 'Diseñado por @medinacaj ✨')
                self.assertIn('✨', capsule.text_content())
                self.assertEqual(capsule.locator('svg[aria-hidden="true"]').count(), 1)
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                if not page.locator('#searchInput').is_visible():
                    page.locator('#searchToggle').click()
                    self.assertTrue(page.locator('#searchInput').is_visible())
                    page.locator('#searchInput').fill('referencia')
                    self.assertEqual(page.evaluate('state.search'), 'referencia')


if __name__ == '__main__':
    unittest.main(verbosity=2)
