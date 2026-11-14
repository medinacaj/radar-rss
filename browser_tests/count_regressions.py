"""Real archive counters with deterministic local data and network failures."""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect
import responsive_smoke as fixtures


class CountRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Match Pages and the existing smoke server: WebKit upgrades scripts to
        # HTTPS under the site's CSP, even when the test page uses plain HTTP.
        cls.tls = tempfile.TemporaryDirectory()
        cert_dir = Path(cls.tls.name)
        cert, key = cert_dir / 'cert.pem', cert_dir / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-keyout', str(key), '-out', str(cert), '-subj', '/CN=localhost',
                        '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'], check=True, capture_output=True)
        cls.server = fixtures.ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.load_cert_chain(certfile=str(cert), keyfile=str(key))
        cls.server.socket = tls_context.wrap_socket(cls.server.socket, server_side=True)
        cls.base = f'https://127.0.0.1:{cls.server.server_port}/'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.driver = sync_playwright().start()
        engine = os.environ.get('RADAR_TEST_ENGINE', 'chromium')
        options = {'headless': True}
        if engine == 'chromium' and os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
        cls.browser = getattr(cls.driver, engine).launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.tls.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block', ignore_https_errors=True)
        self.context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(self.base) else r.abort())
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.payloads = self.dataset(5000)
        self.hold = False
        self.archive_failure = False
        self.pending = []
        self.archive_requests = 0
        self.page.route('**/data/**', self.route)

    def tearDown(self):
        self.context.close()

    @staticmethod
    def dataset(total, offset=0, generation=0):
        stamp = (datetime.now(timezone.utc) + timedelta(seconds=generation)).isoformat().replace('+00:00', 'Z')
        categories = list(fixtures.CATEGORIES) + ['08 - Monagas']
        sources = copy.deepcopy(fixtures.SOURCES) + [{
            'id': 'medio-7', 'name': 'Medio de Monagas', 'category': categories[7],
            'url': 'https://example.com/rss', 'website': 'https://example.com', 'is_radar': False,
        }]
        items = []
        for index in range(total):
            source = sources[index % 8]
            item = {**fixtures.ITEMS[1], 'id': f'history-{index + offset}',
                    'title': f'Noticia de referencia {index + offset}',
                    'url': f'https://example.com/noticia/{index + offset}',
                    'source': source['name'], 'publisher': source['name'],
                    'source_ids': [source['id']], 'categories': [source['category']],
                    'published_at': stamp, 'first_seen_at': stamp, 'coverage': 1}
            items.append(item)
        items[-1]['title'] = 'Archivo exclusivo verificable'
        docs = copy.deepcopy(fixtures.RESPONSES)
        docs['sources.json'] = {'version': 1, 'sources': sources, 'categories': categories}
        docs['latest.json'] = {'version': 2, 'generated_at': stamp, 'items': items[:300]}
        names = []
        for number, start in enumerate(range(300, total, 300), 1):
            name = f'archive-{number:02d}.json'
            names.append(name)
            docs[name] = {'version': 2, 'generated_at': stamp, 'items': items[start:start + 300]}
        docs['meta.json'] = {'version': 2, 'generated_at': stamp, 'total_articles': total,
                             'latest_count': min(total, 300), 'archive_files': names}
        docs['events.json']['generated_at'] = stamp
        docs['status.json']['checked_at'] = stamp
        return docs

    def route(self, route):
        name = Path(urlsplit(route.request.url).path).name
        payload = self.payloads.get(name)
        if name.startswith('archive-'):
            self.archive_requests += 1
            if self.hold:
                self.pending.append((route, payload))
                return
            if self.archive_failure:
                route.fulfill(status=503, body='Temporarily unavailable')
                return
        if payload is None:
            route.fulfill(status=404, body='Missing fixture')
        else:
            route.fulfill(content_type='application/json', body=json.dumps(payload))

    def open(self):
        self.page.goto(self.base + '#noticias')
        self.page.wait_for_function('() => state.ready')

    def release(self, fail=False, fail_generation=None):
        self.hold = False
        for route, payload in self.pending:
            if fail or fail_generation is not None and payload.get('generated_at') == fail_generation:
                route.fulfill(status=503, body='Old generation unavailable')
            else:
                route.fulfill(content_type='application/json', body=json.dumps(payload))
        self.pending.clear()

    def expect_count(self, selector, count):
        expect(self.page.locator(selector)).to_have_text(str(count) if count < 1000 else f'{count:,}'.replace(',', '.'), timeout=15000)

    def test_full_archive_counts_and_filters(self):
        self.hold = True
        self.open()
        expect(self.page.locator('#articleGrid .article-card').first).to_be_visible()
        expect(self.page.locator('#allCount')).to_have_text('…', timeout=1500)
        expect(self.page.locator('#categoryNav > .nav-link').nth(1).locator('.nav-count')).to_have_text('…')
        self.assertEqual(self.page.evaluate('state.items.length'), 300)
        self.page.set_viewport_size({'width': 375, 'height': 812})
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.release()
        self.page.wait_for_function('() => state.historyLoaded')
        self.expect_count('#allCount', 5000)
        self.expect_count('#unreadCount', 5000)
        expect(self.page.locator('#visibleCount')).to_have_text('5.000 ARTÍCULOS')
        self.assertEqual(self.page.locator('#articleGrid .article-card').count(), 36)
        expect(self.page.locator('#loadMore')).to_be_enabled()
        self.page.evaluate("() => {markRead('history-0',true);markRead('history-300',true);}")
        self.expect_count('#allCount', 5000)
        self.expect_count('#unreadCount', 4998)
        expect(self.page.locator('#categoryNav > .nav-link').nth(1).locator('.nav-count')).to_have_text('4.998')
        expect(self.page.locator('#libraryFolderNav .system-folder-link').nth(7).locator('.nav-count')).to_have_text('625')
        self.page.locator('#sidebarFeedOptions > summary').click()
        self.page.select_option('#sourceSelect', 'medio-7')
        self.expect_count('#allCount', 625)
        # The desktop filter flyout now closes after applying a source.
        self.page.locator('#sidebarFeedOptions > summary').click()
        self.page.select_option('#sourceSelect', '')
        self.page.locator('#searchInput').fill('Archivo exclusivo')
        self.expect_count('#allCount', 1)
        expect(self.page.locator('#articleGrid [data-article-id="history-4999"]')).to_be_visible()
        self.page.locator('#searchInput').fill('')
        self.page.evaluate("() => {state.hiddenSources.add('medio-7');render();}")
        self.expect_count('#allCount', 4375)
        self.expect_count('#unreadCount', 4373)
        self.assertFalse(self.errors)

    def test_failed_archive_is_not_a_fake_total_and_can_retry(self):
        self.payloads = self.dataset(900)
        self.archive_failure = True
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—', timeout=2500)
        expect(self.page.locator('#visibleCount')).to_contain_text('TOTAL NO DISPONIBLE')
        expect(self.page.locator('#loadMore')).to_have_text('Reintentar historial')
        self.assertEqual(self.page.evaluate('state.items.length'), 300)
        self.archive_failure = False
        self.page.locator('#loadMore').click()
        self.expect_count('#allCount', 900)
        self.expect_count('#unreadCount', 900)
        self.assertFalse(self.errors)

    def test_reaching_retry_does_not_paginate_or_move_the_failed_archive_action(self):
        self.payloads = self.dataset(900)
        self.archive_failure = True
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        expect(self.page.locator('#articleGrid > .article-card')).to_have_count(36)
        retry = self.page.locator('#loadMore')
        retry.scroll_into_view_if_needed()
        self.page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        expect(self.page.locator('#articleGrid > .article-card')).to_have_count(36)
        box = retry.bounding_box()
        self.assertGreaterEqual(box['y'],0)
        self.assertLessEqual(box['y']+box['height'],900)
        self.archive_failure = False
        retry.click()
        self.expect_count('#allCount',900)
        self.assertFalse(self.errors)

    def test_old_generation_failure_does_not_poison_new_counts(self):
        self.payloads = self.dataset(900)
        old_generation = self.payloads['meta.json']['generated_at']
        self.hold = True
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('…', timeout=1500)
        self.payloads = self.dataset(600, offset=10000, generation=1)
        self.page.evaluate('() => refreshPublishedData()')
        expect(self.page.locator('#publicationNotice')).to_be_visible()
        self.page.locator('#publicationApply').click()
        # Abort may settle old workers and start current downloads before this
        # release. Only old responses fail; current generation remains healthy.
        self.release(fail_generation=old_generation)
        self.expect_count('#allCount', 600)
        self.assertTrue(self.page.evaluate("state.items.every(item => Number(item.id.split('-')[1]) >= 10000)"))
        self.assertFalse(self.page.evaluate('state.historyFailed'))
        self.assertFalse(self.errors)

    def test_retry_never_overlaps_abandoned_download_workers(self):
        self.payloads = self.dataset(1500)
        self.archive_failure = True
        initial = {'value': True}
        original_route = self.route

        def route(request):
            name = Path(urlsplit(request.request.url).path).name
            if initial['value'] and name in ('archive-02.json', 'archive-03.json'):
                self.pending.append((request, self.payloads[name]))
            else:
                original_route(request)

        self.page.route('**/data/**', route)
        self.context.add_init_script("""(() => {
          const base=window.fetch;
          window.activeArchiveFetches=0;window.peakArchiveFetches=0;
          window.fetch=async function(...args){
            if(!String(args[0]).includes('/archive-'))return base.apply(this,args);
            window.activeArchiveFetches++;
            window.peakArchiveFetches=Math.max(window.peakArchiveFetches,window.activeArchiveFetches);
            try{return await base.apply(this,args);}finally{window.activeArchiveFetches--;}
          };
        })();""")
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        initial['value'] = False
        self.archive_failure = False
        self.page.locator('#loadMore').click()
        self.expect_count('#allCount', 1500)
        self.release(fail=True)
        self.assertLessEqual(self.page.evaluate('window.peakArchiveFetches'), 3)
        self.assertFalse(self.errors)

    def test_failed_search_does_not_claim_no_results(self):
        self.payloads = self.dataset(900)
        self.archive_failure = True
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        self.page.locator('#searchInput').fill('Archivo exclusivo')
        expect(self.page.locator('#articleGrid .empty-state h3')).to_have_text('No se pudo completar la búsqueda')
        self.assertFalse(self.errors)

    def test_refresh_recovers_missing_metadata_without_a_new_publication(self):
        self.payloads = self.dataset(900)
        manifest = self.payloads.pop('meta.json')
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        self.payloads['meta.json'] = manifest
        self.page.locator('#refreshNow').click()
        self.expect_count('#allCount', 900)
        self.assertFalse(self.errors)

    def test_followed_topics_and_new_since_visit_wait_for_complete_counts(self):
        self.hold = True
        self.context.add_init_script("""localStorage.setItem('radar-followed-topics',JSON.stringify(['Archivo exclusivo']));
          localStorage.setItem('radar-last-visit',String(Date.now()-3600000));""")
        self.open()
        expect(self.page.locator('#followedNav .nav-count')).to_have_text('…')
        self.page.evaluate("() => {location.hash='#inicio';}")
        self.page.wait_for_function("() => state.pageView==='dashboard'")
        expect(self.page.locator('#followedChips .trend-count')).to_have_text('…')
        expect(self.page.locator('#sinceVisit')).to_be_hidden()
        self.release()
        self.expect_count('#allCount', 5000)
        expect(self.page.locator('#followedNav .nav-count')).to_have_text('1')
        expect(self.page.locator('#followedChips .trend-count')).to_have_text('1')
        expect(self.page.locator('#sinceVisitText')).to_contain_text('5.000 noticias nuevas')
        self.page.evaluate("() => markRead('history-4999',true)")
        expect(self.page.locator('#followedNav .nav-count')).to_have_text('0')
        expect(self.page.locator('#followedChips .trend-count')).to_have_text('0')
        self.assertFalse(self.errors)

    def mark_all_news(self):
        self.page.locator('#categoryNav > .nav-link').nth(1).click(button='right')
        self.page.once('dialog', lambda dialog: dialog.accept())
        self.page.locator('#folderMenu [data-folder-action="read"]').click()

    def mark_first_folder(self):
        self.page.locator('#libraryFolderNav .system-folder-link').first.click(button='right')
        self.page.locator('#folderMenu [data-folder-action="read"]').click()

    def test_bulk_read_waits_for_verified_metadata_and_recovers(self):
        self.payloads = self.dataset(900)
        manifest = self.payloads.pop('meta.json')
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        self.mark_all_news()
        expect(self.page.locator('#actionToast')).to_be_visible()
        self.assertEqual(self.page.evaluate('state.read.size'), 0)
        self.payloads['meta.json'] = manifest
        self.page.locator('#refreshNow').click()
        self.expect_count('#allCount', 900)
        self.mark_all_news()
        self.expect_count('#unreadCount', 0)
        self.assertEqual(self.page.evaluate('state.read.size'), 900)
        self.assertFalse(self.errors)

    def test_bulk_read_rejects_metadata_of_another_generation(self):
        self.payloads = self.dataset(900)
        self.payloads['meta.json']['generated_at'] = '2026-01-01T00:00:00Z'
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        self.mark_all_news()
        expect(self.page.locator('#actionToast')).to_be_visible()
        self.assertEqual(self.page.evaluate('state.read.size'), 0)
        self.assertFalse(self.errors)

    def test_folder_bulk_read_requires_metadata(self):
        self.payloads = self.dataset(900)
        self.payloads.pop('meta.json')
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('—')
        self.mark_first_folder()
        expect(self.page.locator('#actionToast')).to_be_visible()
        self.assertEqual(self.page.evaluate('state.read.size'), 0)
        self.assertFalse(self.errors)

    def test_folder_bulk_read_includes_archived_articles(self):
        self.payloads = self.dataset(900)
        self.hold = True
        self.open()
        expect(self.page.locator('#allCount')).to_have_text('…')
        self.mark_first_folder()
        self.assertEqual(self.page.evaluate('state.read.size'), 0)
        self.release()
        self.expect_count('#allCount', 900)
        self.expect_count('#unreadCount', 787)
        self.assertEqual(self.page.evaluate('state.read.size'), 113)
        self.assertTrue(self.page.evaluate("state.read.has('history-896')"))
        self.assertFalse(self.page.evaluate("state.read.has('history-897')"))
        self.assertFalse(self.errors)

    def check_inconsistent_manifests(self, action):
        self.context.add_init_script("localStorage.removeItem('radar-read')")
        for case in ['missing', 'empty', 'not_array', 'bad_filename', 'repeated', 'bad_total']:
            with self.subTest(manifest=case):
                self.payloads = self.dataset(900)
                meta = self.payloads['meta.json']
                if case == 'missing':
                    meta.pop('archive_files')
                elif case == 'empty':
                    meta['archive_files'] = []
                elif case == 'not_array':
                    meta['archive_files'] = None
                elif case == 'bad_filename':
                    meta['archive_files'] = ['../archive.json']
                elif case == 'repeated':
                    meta['archive_files'] = ['archive-01.json', 'archive-01.json']
                else:
                    meta['total_articles'] = '900'
                self.page.goto(self.base + '?manifest_case=' + case + '#noticias')
                self.page.wait_for_function('() => state.ready')
                self.page.wait_for_function('() => !state.historyLoading')
                action()
                self.assertEqual(self.page.evaluate('state.read.size'), 0)
                expect(self.page.locator('#allCount')).to_have_text('—')
        self.assertFalse(self.errors)

    def test_inconsistent_manifest_blocks_global_bulk_read(self):
        self.check_inconsistent_manifests(self.mark_all_news)

    def test_inconsistent_manifest_blocks_folder_bulk_read(self):
        self.check_inconsistent_manifests(self.mark_first_folder)

    def test_complete_latest_without_archive_allows_bulk_read(self):
        self.payloads = self.dataset(24)
        self.open()
        self.expect_count('#allCount', 24)
        self.mark_first_folder()
        self.expect_count('#unreadCount', 21)
        self.assertEqual(self.page.evaluate('state.read.size'), 3)
        self.mark_all_news()
        self.expect_count('#unreadCount', 0)
        self.assertEqual(self.page.evaluate('state.read.size'), 24)
        self.assertFalse(self.errors)


if __name__ == '__main__':
    unittest.main(verbosity=2)
