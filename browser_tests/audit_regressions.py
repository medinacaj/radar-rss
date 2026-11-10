"""Deterministic browser regressions for backup, routes and article controls.
Run: /workspace/radar-audit-tools/bin/python browser_tests/audit_regressions.py
"""
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
import responsive_smoke as fixtures


class AuditRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/'
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
        self.page = self.context.new_page()
        self.page.route('**/data/**', fixtures.make_route)
        self.page.route('https://example.com/**', lambda route: route.abort())
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(self.base)
        self.page.wait_for_function('() => state.ready && document.querySelector(".article-card")')

    def tearDown(self):
        self.context.close()

    def test_invalid_hash_and_reset(self):
        self.page.goto(self.base + '#%')
        self.page.wait_for_function('() => state.ready')
        self.page.wait_for_timeout(100)
        self.assertFalse(self.errors)
        self.assertGreater(self.page.locator('.article-card').count(), 0)
        self.page.on('dialog', lambda dialog: dialog.accept())
        self.page.evaluate("document.getElementById('resetSettings').click()")
        reset_theme = self.page.evaluate('state.theme')
        self.page.reload()
        self.page.wait_for_function('() => state.ready')
        self.assertEqual(self.page.evaluate('state.theme'), reset_theme)

    def test_placeholder_and_empty_tags(self):
        self.page.evaluate("goTo('all')")
        self.page.wait_for_function("() => state.pageView==='feed'")
        self.assertFalse(self.page.locator('#libraryTagFilter').is_visible())
        for item_id in ['noticia-1', 'noticia-0']:
            placeholder = self.page.locator(f'#articleGrid [data-article-id="{item_id}"] .article-cover-placeholder')
            # PR106 restored aligned typographic covers when an image is absent.
            # Keep that cover distinguishable from an invented photograph.
            expect(placeholder).to_be_visible()
            expect(placeholder.locator('img')).to_have_count(0)
            expect(placeholder.locator('.article-cover-publisher')).not_to_be_empty()
            self.page.locator(f'#articleGrid [data-article-id="{item_id}"] .article-also').click()
            self.assertTrue(self.page.locator('#articleReaderDialog').is_visible())
            self.page.locator('#readerClose').click()
        self.page.locator('#articleGrid .article-also').first.click()
        self.page.locator('#libraryTagInput').fill('Research')
        self.page.locator('.reader-tag-create button').click()
        self.page.locator('#readerClose').click()
        self.assertTrue(self.page.locator('#libraryTagFilter').is_visible())
        self.page.locator('#articleGrid .article-also').first.click()
        self.page.locator('#libraryReaderTags button').click()
        self.page.locator('#readerClose').click()
        self.assertFalse(self.page.locator('#libraryTagFilter').is_visible())

    def test_complete_backup_and_live_import(self):
        self.page.evaluate("""() => {
            localStorage.setItem('radar-followed-topics','["robotics"]');
            localStorage.setItem('radar-v12-preferences',JSON.stringify({mine:true,categories:['02 - Tecnología'],briefing:'mine'}));
            localStorage.setItem('radar-v12-saved-searches',JSON.stringify([{label:'Research',query:'chips',geo:'all',category:'all',feed:'',age:7}]));
            localStorage.setItem('radar-lite','true');
        }""")
        self.page.reload()
        self.page.wait_for_function('() => state.ready')
        with self.page.expect_download() as download:
            self.page.evaluate("document.getElementById('exportData').click()")
        with open(download.value.path()) as saved:
            backup = json.load(saved)
        self.assertEqual(backup['modules']['followedTopics'], ['robotics'])
        self.assertEqual(backup['modules']['savedSearches'][0]['label'], 'Research')
        self.assertEqual(backup['modules']['v12Preferences']['categories'], ['02 - Tecnología'])
        self.assertTrue(backup['preferences']['lite'])
        backup['modules']['followedTopics'] = ['quantum']
        backup['modules']['savedSearches'][0]['label'] = 'Restored now'
        backup['modules']['v12Preferences']['categories'] = ['07 - Concepción']
        backup['preferences']['lite'] = False
        self.page.locator('#importData').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
        self.page.wait_for_function("() => document.getElementById('dataNotice').textContent==='Respaldo importado correctamente.'")
        self.assertFalse(self.page.evaluate('state.lite'))
        self.assertFalse(self.page.locator('body').evaluate("node=>node.classList.contains('lite')"))
        self.assertEqual(self.page.evaluate('window.RadarV12.briefingCategories()'), ['07 - Concepción'])
        self.assertIn('Restored now', self.page.locator('#v12SavedSearches').inner_text())
        self.assertIn('quantum', self.page.locator('#followedNav').text_content())
        self.assertFalse(self.errors)


    def import_backup(self, backup):
        self.page.locator('#importData').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
        self.page.wait_for_function("() => document.getElementById('dataNotice').textContent==='Respaldo importado correctamente.'")

    def test_read_history_and_agenda_backup_roundtrip(self):
        agenda = {'version': 1, 'saved': ['event-one', 'expired-event'], 'view': 'calendar'}
        self.page.evaluate("""value => {
          state.read=new Set(Array.from({length:5000},(_,i)=>'read-'+i));
          RadarAgenda.restorePreferences(value);
        }""", agenda)
        with self.page.expect_download() as download:
            self.page.evaluate("document.getElementById('exportData').click()")
        with open(download.value.path()) as saved:
            backup = json.load(saved)
        self.assertEqual(backup['modules']['agendaPreferences'], agenda)
        self.page.evaluate('() => {state.read.clear();RadarAgenda.clearPreferences();}')
        self.import_backup(backup)
        self.assertEqual(self.page.evaluate('state.read.size'), 5000)
        self.assertTrue(self.page.evaluate("state.read.has('read-0')"))
        self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'), agenda)
        self.assertFalse(self.errors)

    def test_invalid_agenda_backup_does_not_partially_import(self):
        before = self.page.evaluate('() => ({theme:state.theme,read:[...state.read],agenda:RadarAgenda.exportPreferences()})')
        backup = {'format':'radar-rss-settings-v3', 'preferences':{'theme':'dark' if before['theme'] != 'dark' else 'light'},
                  'read':['unexpected'], 'modules':{'agendaPreferences':{'version':1,'saved':['duplicate','duplicate'],'view':'calendar'}}}
        self.page.locator('#importData').set_input_files({'name':'invalid.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
        self.page.wait_for_function("() => document.getElementById('dataNotice').textContent==='Archivo inválido o incompatible.'")
        after = self.page.evaluate('() => ({theme:state.theme,read:[...state.read],agenda:RadarAgenda.exportPreferences()})')
        self.assertEqual(after, before)

    def test_reset_preserves_saved_activities_and_explicit_clear_removes_them(self):
        self.page.evaluate("RadarAgenda.restorePreferences({version:1,saved:['keep-event'],view:'calendar'})")
        self.page.on('dialog', lambda dialog: dialog.accept())
        self.page.evaluate("document.getElementById('resetSettings').click()")
        self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'), {'version':1,'saved':['keep-event'],'view':'list'})
        self.page.evaluate("document.getElementById('clearAgendaSaved').click()")
        self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'), {'version':1,'saved':[],'view':'list'})

    def test_full_storage_does_not_abort_global_preference_reset(self):
        self.page.evaluate("""() => {
          setTheme('dark',true);state.density='compact';
          RadarAgenda.restorePreferences({version:1,saved:['keep-event'],view:'calendar'});
          Storage.prototype.setItem=function(){throw new DOMException('Quota exceeded','QuotaExceededError')};
        }""")
        self.page.on('dialog',lambda dialog:dialog.accept())
        self.page.evaluate("document.getElementById('resetSettings').click()")
        self.assertEqual(self.page.evaluate('state.density'),'comfortable')
        self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences().saved'),['keep-event'])
        self.assertIn('agenda',self.page.locator('#dataNotice').text_content())
        self.assertFalse(self.errors)

    def test_legacy_backups_preserve_module_preferences(self):
        self.page.evaluate("RadarAgenda.restorePreferences({version:1,saved:['legacy-keep'],view:'calendar'})")
        self.page.evaluate("""() => {
          localStorage.setItem('radar-followed-topics','["robotics"]');
          localStorage.setItem('radar-v12-preferences',JSON.stringify({mine:true,categories:['02 - Tecnología'],briefing:'mine'}));
          localStorage.setItem('radar-v12-saved-searches',JSON.stringify([{label:'Keep this',query:'chips',geo:'all'}]));
        }""")
        for version in ['v2', 'v3']:
            self.import_backup({'format':'radar-rss-settings-' + version,'preferences':{'theme':'dark'}})
            self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('radar-followed-topics'))"), ['robotics'])
            self.assertEqual(self.page.evaluate("window.RadarV12.briefingCategories()"), ['02 - Tecnología'])
            self.assertIn('Keep this', self.page.locator('#v12SavedSearches').text_content())
            self.assertEqual(self.page.evaluate('RadarAgenda.exportPreferences()'), {'version':1,'saved':['legacy-keep'],'view':'calendar'})
        self.assertFalse(self.errors)

    def test_malformed_modules_are_normalized(self):
        self.import_backup({'format':'radar-rss-settings-v3','preferences':{},'modules':{
            'followedTopics':[None, {}, '', '  robotics  ', 'robotics', 'x' * 200],
            'v12Preferences':{'mine':'yes','categories':['unknown',None,'07 - Concepción'],'briefing':'cat:unknown'},
            'savedSearches':[None,{}, {'label':'Bad geography','query':'','geo':'bogus'},
                            {'label':'Valid','query':'chips','geo':'all','age':999,'feed':'unknown','category':'unknown'}]}})
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('radar-followed-topics'))"), ['robotics', 'x' * 40])
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('radar-v12-preferences'))"), {'mine':False,'categories':['07 - Concepción'],'briefing':'all'})
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('radar-v12-saved-searches'))"), [{'label':'Valid','query':'chips','geo':'all','age':0,'category':'all','feed':''}])
        self.assertFalse(self.errors)


if __name__ == '__main__':
    unittest.main(verbosity=2)
