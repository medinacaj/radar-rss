"""HTTPS, offline browser contracts for the single agenda and its local tools.

RADAR_TEST_ENGINE=chromium|firefox|webkit; RADAR_CHROMIUM_EXECUTABLE only
overrides Chromium. Uses real UI, JSON boundaries and downloaded calendar files.
"""
from copy import deepcopy
from datetime import datetime, timezone
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
from agenda_regressions import document, event, STAMP, MONAGAS


class AgendaToolsRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tls = tempfile.TemporaryDirectory()
        cert, key = (Path(cls.tls.name) / name for name in ('cert.pem', 'key.pem'))
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-keyout', str(key), '-out', str(cert), '-subj', '/CN=localhost',
                        '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'], check=True, capture_output=True)
        cls.server = fixtures.ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.load_cert_chain(str(cert), str(key))
        cls.server.socket = tls_context.wrap_socket(cls.server.socket, server_side=True)
        cls.base = f'https://127.0.0.1:{cls.server.server_port}/'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.driver = sync_playwright().start()
        cls.engine = os.environ.get('RADAR_TEST_ENGINE', 'chromium')
        options = {'headless': True}
        if cls.engine == 'chromium' and os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
        cls.browser = getattr(cls.driver, cls.engine).launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.tls.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900},
                                                service_workers='block', ignore_https_errors=True)
        self.context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        self.page = self.context.new_page()
        self.page.set_default_timeout(2500)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.clock.install(time=datetime(2026, 10, 25, 3, 59, 30, tzinfo=timezone.utc))
        self.payload = document()
        self.payload['items'][0].update(locality='Concepción', event_type='Feria',
                                        price_text='Entrada $2.000', is_free=False)
        self.payload['items'][1].update(locality='Talcahuano', event_type='Teatro', is_free=True)
        self.payload['items'].append(event('calendario', '2026-11-03', preference_source_id='medio-6',
                                            source_id='calendario-local',
                                            date_evidence={'kind': 'rss', 'value': '2026-11-03',
                                                           'url': 'https://example.com/agenda.ics'}))
        self.docs = deepcopy(fixtures.RESPONSES)
        self.docs['sources.json']['categories'].append(MONAGAS)
        self.docs['sources.json']['sources'].append(dict(id='medio-7', name='Medio de Monagas', category=MONAGAS,
                                                        url='https://example.com/rss', website='https://example.com', is_radar=False))
        for name in ('latest.json', 'meta.json'):
            self.docs[name]['generated_at'] = STAMP
        for row in self.docs['latest.json']['items']:
            row['published_at'] = STAMP
        self.status = 200
        self.page.route('**/data/**', self.route)

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.context.close()

    def route(self, route):
        name = Path(urlsplit(route.request.url).path).name
        if name == 'events.json':
            route.fulfill(status=self.status, content_type='application/json', body=json.dumps(self.payload))
        elif name in self.docs:
            route.fulfill(status=200, content_type='application/json', body=json.dumps(self.docs[name]))
        else:
            route.abort()

    def open(self):
        self.page.goto(self.base + '#agenda')
        expect(self.page.locator('#agendaSection')).to_have_attribute('aria-busy', 'false')
        expect(self.page.locator('#agendaStatus')).not_to_contain_text('No se pudo')

    def rows(self):
        return self.page.locator('#agendaList [data-event-id]')

    def test_calendar_navigation_selects_local_multiday_and_excludes_changes(self):
        # A second agenda, hidden default list, or stale day counts breaks this.
        self.open()
        expect(self.page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
        expect(self.page.locator('#agendaViewList')).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#agendaCalendar')).to_be_hidden()
        self.page.locator('#agendaViewCalendar').click()
        expect(self.page.locator('#agendaCalendarTitle')).to_contain_text('octubre de 2026')
        expect(self.page.locator('#agendaCalendarPrev')).to_be_disabled()
        day = self.page.locator('[data-agenda-date="2026-10-26"]')
        day.focus()
        self.page.keyboard.press('Enter')
        expect(day).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#agendaList [data-event-id="multidia"]')).to_be_visible()
        expect(self.page.locator('#agendaList [data-event-id="cancelado"]')).to_have_count(0)
        expect(self.page.locator('#agendaCalendar [data-event-id="cancelado"]')).to_have_count(0)
        self.page.locator('#agendaCalendarNext').click()
        expect(self.page.locator('#agendaCalendarTitle')).to_contain_text('noviembre de 2026')
        self.page.locator('[data-agenda-date="2026-11-01"]').click()
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'viejo-futuro')
        self.page.locator('#agendaViewList').click()
        expect(self.page.locator('#agendaList [data-event-id="limite90"]')).to_be_visible()
        expect(self.page.locator('#agendaList [data-event-id="fuera90"]')).to_have_count(0)
        self.assertEqual(self.page.locator('#agendaSection').count(), 1)

    def test_filters_use_explicit_details_and_keep_unknowns_accessible(self):
        # Guessing commune/type/price from prose or dropping legacy rows fails.
        self.open()
        self.page.locator('#agendaLocality').select_option('value:Concepción')
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'viejo-futuro')
        self.page.locator('#agendaLocality').select_option('')
        self.page.locator('#agendaType').select_option('value:Teatro')
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'multidia')
        self.page.locator('#agendaType').select_option('')
        self.page.locator('#agendaPrice').select_option('free')
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'multidia')
        self.page.locator('#agendaPrice').select_option('paid')
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'viejo-futuro')
        self.page.locator('#agendaPrice').select_option('unknown')
        expect(self.page.locator('#agendaList [data-event-id="hoy-chile"]')).to_be_visible()
        expect(self.page.locator('#agendaList [data-event-id="multidia"]')).to_have_count(0)
        self.page.locator('#agendaPrice').select_option('')
        self.page.locator('#agendaCategory').select_option('value:' + MONAGAS)
        expect(self.page.locator('#agendaList [data-event-id="hoy-venezuela"]')).to_be_visible()
        expect(self.page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_have_count(0)
        self.page.locator('#agendaCategory').select_option('')
        self.page.locator('#agendaSearch').fill('concepcion')
        expect(self.page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
        self.page.locator('#agendaSearch').fill('imposible-sin-resultados')
        expect(self.page.locator('#agendaStatus')).to_contain_text('No hay actividades')
        expect(self.rows()).to_have_count(0)

    def test_saved_ids_and_view_survive_reload_and_restore_is_atomic(self):
        # A cosmetic count, non-persistent save, or partial invalid restore fails.
        self.open()
        self.page.locator('[data-event-id="viejo-futuro"] [data-agenda-save]').click()
        expect(self.page.locator('#agendaSavedOnly')).to_contain_text('(1)')
        self.page.locator('#agendaSavedOnly').click()
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'viejo-futuro')
        self.page.locator('#agendaViewCalendar').click()
        self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'),
                         {'version': 1, 'saved': ['viejo-futuro'], 'view': 'calendar'})
        self.page.reload()
        expect(self.page.locator('#agendaViewCalendar')).to_have_attribute('aria-pressed', 'true')
        self.page.locator('#agendaViewList').click()
        expect(self.page.locator('[data-event-id="viejo-futuro"] [data-agenda-save]')).to_have_attribute('aria-pressed', 'true')
        before = self.page.evaluate('RadarAgenda.exportPreferences()')
        for value in [None, {}, {'version': 2, 'saved': [], 'view': 'list'},
                      {'version': 1, 'saved': ['ok', 3], 'view': 'list'},
                      {'version': 1, 'saved': ['x' * 129], 'view': 'list'},
                      {'version': 1, 'saved': ['a'] * 1001, 'view': 'list'},
                      {'version': 1, 'saved': [], 'view': 'other'}]:
            rejected = self.page.evaluate('value => {try{RadarAgenda.restorePreferences(value);return false}catch{return true}}', value)
            self.assertTrue(rejected, value)
            self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'), before)
        self.page.evaluate("RadarAgenda.restorePreferences({version:1,saved:['multidia','expired'],view:'list'})")
        expect(self.page.locator('#agendaSavedOnly')).to_contain_text('(1)')
        self.page.locator('#agendaSavedOnly').click()
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'multidia')
        expect(self.page.locator('#agendaSavedHelp')).to_contain_text('vigente')
        self.page.evaluate('RadarAgenda.clearPreferences()')
        self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'), {'version': 1, 'saved': [], 'view': 'list'})
        self.assertIsNone(self.page.evaluate("localStorage.getItem('radar-agenda-preferences-v1')"))

    def test_preference_validation_is_pure_and_rejects_sparse_ids(self):
        # The application backup must validate agenda before changing any storage.
        self.open()
        result = self.page.evaluate("""() => {
          const input={version:1,saved:['multidia'],view:'calendar'};
          const before=localStorage.getItem('radar-agenda-preferences-v1');
          const output=RadarAgenda.validatePreferences(input);output.saved.push('copy');
          let sparseRejected=false;
          try{RadarAgenda.validatePreferences({version:1,saved:new Array(1),view:'list'})}catch{sparseRejected=true}
          return {input,sparseRejected,unchanged:before===localStorage.getItem('radar-agenda-preferences-v1'),preferences:RadarAgenda.exportPreferences()};
        }""")
        self.assertEqual(result, {'input': {'version': 1, 'saved': ['multidia'], 'view': 'calendar'},
                                  'sparseRejected': True, 'unchanged': True,
                                  'preferences': {'version': 1, 'saved': [], 'view': 'list'}})

    def test_removing_last_saved_activity_keeps_keyboard_focus(self):
        # Removing a focused row from saved-only results must leave usable focus.
        self.open()
        self.page.locator('[data-event-id="viejo-futuro"] [data-agenda-save]').click()
        self.page.locator('#agendaSavedOnly').click()
        self.page.locator('[data-event-id="viejo-futuro"] [data-agenda-save]').click()
        expect(self.rows()).to_have_count(0)
        expect(self.page.locator('#agendaSavedOnly')).to_be_focused()

    def test_pending_and_cancelled_saved_items_never_enter_calendar_or_ics(self):
        # Saving changes must never turn pending/cancelled rows into active dates.
        self.open()
        self.page.evaluate("RadarAgenda.restorePreferences({version:1,saved:['sin-fecha','cancelado'],view:'list'})")
        self.page.locator('#agendaSavedOnly').click()
        expect(self.rows()).to_have_count(0)
        expect(self.page.locator('#agendaExport')).to_be_disabled()
        self.page.locator('#agendaPending > summary').click()
        expect(self.page.locator('#agendaPendingList [data-event-id="sin-fecha"]')).to_be_visible()
        expect(self.page.locator('#agendaPendingList [data-event-id="cancelado"]')).to_be_visible()
        expect(self.page.locator('#agendaPendingList [data-agenda-export]')).to_have_count(0)
        self.page.locator('#agendaViewCalendar').click()
        self.assertTrue(all('0 actividades' in label for label in self.page.locator('#agendaCalendarGrid button').evaluate_all('nodes=>nodes.map(n=>n.getAttribute("aria-label"))')))
        expect(self.rows()).to_have_count(0)

    def test_ics_export_escapes_text_and_uses_exclusive_all_day_end(self):
        # Date-time guesses, an inclusive DTEND, or unescaped injection fails.
        self.payload['items'] = [event('ics', '2026-10-25', end_date='2026-10-27',
                                      title='Feria, arte; música\\visita\nOtra línea ' + 'ó' * 70,
                                      location='Sala, A; piso\\2\nConcepción'),
                                 event('cancelado', status='cancelled')]
        self.open()
        with self.page.expect_download() as download_info:
            self.page.locator('#agendaExport').click()
        download = download_info.value
        self.assertEqual(download.suggested_filename, 'radar-rss-agenda.ics')
        raw = Path(download.path()).read_bytes()
        self.assertTrue(raw.endswith(b'END:VCALENDAR\r\n'))
        self.assertTrue(all(len(line) <= 75 for line in raw.split(b'\r\n')))
        value = raw.decode().replace('\r\n ', '')
        self.assertIn('PRODID:-//Radar-RSS//Agenda//ES\r\n', value)
        self.assertIn('UID:ics@agenda.radar-rss\r\n', value)
        self.assertEqual(value.count('BEGIN:VEVENT'), 1)
        self.assertIn('DTSTART;VALUE=DATE:20261025\r\n', value)
        self.assertIn('DTEND;VALUE=DATE:20261028\r\n', value)
        self.assertIn('SUMMARY:Feria\\, arte\\; música\\\\visita\\nOtra línea', value)
        self.assertIn('LOCATION:Sala\\, A\\; piso\\\\2\\nConcepción', value)
        self.assertIn('URL:https://example.com/eventos/ics\r\n', value)
        self.assertNotIn('cancelado', value)
        self.assertNotIn('sin-fecha', value)
        self.page.locator('#agendaSearch').fill('ninguna')
        expect(self.page.locator('#agendaExport')).to_be_disabled()

    def test_parent_source_and_existing_reader_preferences_still_apply(self):
        # Hiding a parent feed must hide its derived calendar and filter options.
        self.payload['items'][-1]['date_evidence']['kind'] = 'calendar'
        self.open()
        expect(self.page.locator('[data-event-id="calendario"]')).to_be_visible()
        self.page.evaluate("state.hiddenSources.add('medio-6');render()")
        expect(self.page.locator('#agendaList [data-event-id="calendario"]')).to_have_count(0)
        expect(self.page.locator('#agendaLocality option[value="value:Concepción"]')).to_have_count(0)
        expect(self.page.locator('#agendaPending')).to_be_hidden()
        self.page.evaluate("state.hiddenSources.clear();state.hiddenSources.add('calendario-local');render()")
        expect(self.page.locator('#agendaList [data-event-id="calendario"]')).to_have_count(0)
        self.page.evaluate("state.hiddenSources.clear();state.mutedKeywords='calendario';render()")
        expect(self.page.locator('#agendaList [data-event-id="calendario"]')).to_have_count(0)
        self.page.evaluate("state.mutedKeywords='';state.search='viejo-futuro';render()")
        self.assertEqual(self.rows().get_attribute('data-event-id'), 'viejo-futuro')

    def test_multiday_remains_until_local_end_and_window_is_inclusive_90(self):
        # UTC expiry, start-only expiry, or a 89/91-day window fails.
        self.open()
        expect(self.page.locator('#agendaList [data-event-id="limite90"]')).to_be_visible()
        expect(self.page.locator('#agendaList [data-event-id="fuera90"]')).to_have_count(0)
        expect(self.page.locator('#agendaList [data-event-id="ayer-chile"]')).to_have_count(0)
        expect(self.page.locator('#agendaList [data-event-id="ayer-venezuela"]')).to_be_visible()
        self.page.clock.set_system_time(datetime(2026, 10, 27, 2, 59, 30, tzinfo=timezone.utc))
        self.page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
        expect(self.page.locator('#agendaList [data-event-id="multidia"]')).to_be_visible()
        self.page.clock.run_for(60_000)
        expect(self.page.locator('#agendaList [data-event-id="multidia"]')).to_have_count(0)

    def test_optional_fields_are_strict_and_failure_does_not_export_stale_data(self):
        # Optional coercion, unsafe parent IDs or stale export after failure fails.
        self.open()
        for changes in [dict(locality=5), dict(locality='x' * 201), dict(event_type=[]),
                        dict(price_text={}), dict(is_free='true'), dict(is_free=0),
                        dict(preference_source_id=3), dict(preference_source_id='x' * 129)]:
            self.payload['items'] = [event('invalid', **changes)]
            self.page.evaluate('RadarAgenda.refresh()')
            expect(self.page.locator('#agendaStatus')).to_contain_text('No se pudo')
            expect(self.rows()).to_have_count(0)
            expect(self.page.locator('#agendaExport')).to_be_disabled()
        self.payload['items'] = [event('valid', locality=None, event_type=None, price_text=None,
                                      is_free=None, preference_source_id=None)]
        self.page.evaluate('RadarAgenda.refresh()')
        expect(self.page.locator('#agendaList [data-event-id="valid"]')).to_be_visible()
        self.page.evaluate("state.generated='2026-10-25T04:00:00Z';RadarAgenda.refresh()")
        expect(self.page.locator('#agendaStatus')).to_contain_text('No se pudo')
        expect(self.page.locator('#agendaExport')).to_be_disabled()
        self.status = 503
        self.page.locator('#agendaRetry').click()
        expect(self.page.locator('#agendaStatus')).to_contain_text('No se pudo')

    def test_share_fallback_is_a_safe_readonly_source_link(self):
        # Sharing an unsafe/unrelated URL, or no usable fallback, fails.
        self.context.add_init_script("Object.defineProperty(navigator,'share',{value:undefined});Object.defineProperty(navigator,'clipboard',{value:undefined})")
        self.open()
        self.page.locator('[data-event-id="viejo-futuro"] [data-agenda-share]').click()
        field = self.page.locator('[data-event-id="viejo-futuro"] .agenda-share-link')
        expect(field).to_be_visible()
        expect(field).to_have_value('https://example.com/eventos/viejo-futuro')
        self.assertIsNotNone(field.get_attribute('readonly'))
        anchor = self.page.locator('[data-event-id="viejo-futuro"] h3 a')
        self.assertEqual(anchor.get_attribute('rel'), 'noopener noreferrer external')

    def test_calendar_and_controls_fit_mobile_and_have_readable_selected_text(self):
        # Overflow and theme-inherited low contrast on active controls fail.
        self.open()
        self.page.locator('#agendaViewCalendar').click()
        for width in (375, 1440):
            self.page.set_viewport_size({'width': width, 'height': 900})
            for theme in ('light', 'dark'):
                self.page.evaluate('theme => setTheme(theme,true)', theme)
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'))
                ratios = self.page.evaluate(r"""() => {
                  const lum=c=>c.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
                  return [...document.querySelectorAll('#agendaSection button[aria-pressed="true"]')].map(n=>{
                    let bg=n;while(getComputedStyle(bg).backgroundColor==='rgba(0, 0, 0, 0)')bg=bg.parentElement;
                    const a=lum(getComputedStyle(n).color),b=lum(getComputedStyle(bg).backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                  });
                }""")
                self.assertTrue(ratios and min(ratios) >= 4.5, (width, theme, ratios))


if __name__ == '__main__':
    unittest.main(verbosity=2)
