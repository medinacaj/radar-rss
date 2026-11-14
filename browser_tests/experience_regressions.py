#!/usr/bin/env python3
"""Reading profiles, legible columns and local navigation, with fixture-only traffic.

Run: python browser_tests/experience_regressions.py
Shares only the TLS/browser fixture lifecycle with the existing reading test.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from reading_experience import QuietHandler, ROOT
from responsive_smoke import RESPONSES, CATEGORIES

OUTPUT = ROOT / 'test-results' / 'experience'


def exercise(browser, base, width):
    context = browser.new_context(viewport={'width': width, 'height': 900},
                                  ignore_https_errors=True, service_workers='block')
    context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
    responses = copy.deepcopy(RESPONSES)

    def data(route):
        name = urlsplit(route.request.url).path.rsplit('/', 1)[-1]
        route.fulfill(status=200 if name in responses else 404, content_type='application/json',
                      body=json.dumps(responses.get(name, {})))

    context.route('**/data/**', data)
    context.add_init_script("""localStorage.setItem('radar-experience-v1','{broken');
      localStorage.setItem('radar-source-folders-v1',JSON.stringify({'Mis lecturas':['medio-0']}));
      localStorage.setItem('radar-card-title-size','22');localStorage.setItem('radar-columns','6');""")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(base + '#noticias', wait_until='networkidle')
        expect(page.locator('#articleGrid>.article-card')).to_have_count(18)
        assert page.evaluate('window.RadarExperience.getPinnedDestinations()') == []
        if width <= 950:page.locator('#menuToggle').click()
        if width <= 640:
            page.locator('#feedFiltersToggle').click()
        else:
            if page.locator('#sidebarReadingContent').is_hidden(): page.locator('#sidebarReadingToggle').click()
            page.locator('#sidebarFeedOptions > summary').click()
            page.locator('#presentationSummary').click()
        profile = page.locator('#readingProfile')
        expect(profile).to_be_visible()
        for value, layout, images, summaries in [('compact','cards',False,True), ('headlines','list',False,False), ('visual','cards',True,True)]:
            profile.select_option(value)
            assert page.evaluate('({layout:state.layout,images:state.showImages,summaries:state.showSummaries})') == {'layout':layout,'images':images,'summaries':summaries}
            assert page.evaluate("state.cardTitleSize===22&&state.columns==='6'")
        page.wait_for_function("() => Number(document.body.dataset.effectiveColumns)>=1")
        actual=page.evaluate("Number(document.body.dataset.effectiveColumns)")
        assert 1<=actual<=6
        expect(page.locator('#effectiveColumns')).to_contain_text(str(actual)+' columna')
        if actual<6:
            expect(page.locator('#effectiveColumns')).to_contain_text('de 6 solicitadas')
        assert page.locator('#articleGrid .article-title').first.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)') >= 22
        assert page.locator('#articleGrid .no-cover .article-cover-placeholder').first.evaluate('n=>n.getBoundingClientRect().height') <= 60
        for selector in ('.article-save','.article-more','.article-read-toggle'):
            expect(page.locator('#articleGrid '+selector).first.locator('.experience-action-label')).to_be_visible()

        # Labels must fit their buttons, and header selectors remain readable.
        for button in page.locator('#articleGrid>.article-card').first.locator('.article-actions button').all():
            assert button.evaluate('n=>n.scrollWidth<=n.clientWidth+1'), button.inner_text()
            assert button.locator('.experience-action-label').evaluate('n=>{const r=n.getBoundingClientRect(),b=n.closest("button").getBoundingClientRect();return r.left>=b.left&&r.right<=b.right+1}')
        assert page.locator('#sourceSelect').bounding_box()['width'] >= 120
        assert page.locator('#editorialType').bounding_box()['width'] >= 120

        if width<=640:page.locator('#feedFiltersDone').click()
        else:page.locator('#presentationSummary').click()

        # Search operates on existing folder rows; source selection uses the existing feed filter.
        if width <= 950 and page.locator('#appSidebar').evaluate('n=>n.inert'):
            page.locator('#menuToggle').click()
        search = page.locator('#sidebarLibrarySearch')
        search.fill('lecturas')
        expect(page.locator('#libraryFolderNav .library-folder-row')).to_be_visible()
        expect(page.locator('#libraryFolderNav .folder-default-row').first).not_to_be_visible()
        pin = page.locator('#libraryFolderNav .library-folder-row .experience-pin')
        # Storage quota/security errors cannot silently create a saved preference.
        page.evaluate("""() => {window.experienceSetItem=Storage.prototype.setItem;
          Storage.prototype.setItem=function(key,value){if(key==='radar-experience-v1')throw new Error('quota fixture');return window.experienceSetItem.call(this,key,value)};}""")
        pin.click()
        assert page.evaluate('window.RadarExperience.getPinnedDestinations()') == []
        expect(page.locator('#actionToast')).to_contain_text('No se pudieron guardar')
        page.evaluate('() => {Storage.prototype.setItem=window.experienceSetItem;}')
        pin.focus()
        pin.press('Enter')
        expect(pin).to_have_attribute('aria-pressed','true')
        assert page.evaluate('window.RadarExperience.getPinnedDestinations()') == ['carpeta/Mis lecturas']
        search.fill('referencia 0')
        expect(page.locator('#sidebarSourceResults button')).to_have_count(1)
        page.locator('#sidebarSourceResults button').focus()
        page.evaluate('render()')
        expect(page.locator('#sidebarSourceResults button')).to_be_focused()
        page.locator('#sidebarSourceResults button').press('Enter')
        expect(page.locator('#sourceSelect')).to_have_value('medio-0')
        expect(page.locator('#feedActiveFilters')).to_be_hidden()
        assert page.locator('#feedActiveFilters').evaluate('n=>getComputedStyle(n).display') == 'none'
        # The actual source control remains in the side menu, not a chip over the feed.
        if width<=950 and page.locator('#appSidebar').evaluate('n=>n.inert'):
            page.locator('#menuToggle').click()
        if width<=640:
            page.locator('#feedFiltersToggle').click()
        else:
            if page.locator('#sidebarReadingContent').is_hidden(): page.locator('#sidebarReadingToggle').click()
            if not page.locator('#sidebarFeedOptions').evaluate('n=>n.open'): page.locator('#sidebarFeedOptions > summary').click()
        page.locator('#sourceSelect').select_option('')
        expect(page.locator('#sourceSelect')).to_have_value('')
        if width<=640:page.locator('#feedFiltersDone').click()
        if width<=950:page.locator('#menuClose').click()

        # Reader closing restores the same article and viewport, including after a profile render.
        card = page.locator('#articleGrid>.article-card').nth(4)
        card.scroll_into_view_if_needed()
        before = page.evaluate('window.scrollY')
        # Playwright may scroll again to expose the title below sticky controls.
        # Capture the actual user-action viewport after that positioning finishes.
        page.evaluate("""() => {window.experienceReaderScroll=null;
          document.addEventListener('pointerdown',()=>{window.experienceReaderScroll=window.scrollY;window.experienceReaderTop=document.querySelector('[data-article-id="noticia-4"]').getBoundingClientRect().top;},{capture:true,once:true});}""")
        card.locator('.article-also').click()
        opened = page.evaluate('window.experienceReaderScroll')
        assert opened is not None, 'Reader opening pointer action was not captured'
        page.locator('#readerClose').click()
        page.wait_for_function("() => document.activeElement?.closest('[data-article-id]')?.dataset.articleId==='noticia-4'")
        after = page.evaluate('window.scrollY')
        returned_top = card.evaluate('n=>n.getBoundingClientRect().top')
        opened_top = page.evaluate('window.experienceReaderTop')
        assert abs(returned_top - opened_top) <= 2, f'{width}px reader return: scroll {opened}->{after}, anchor {opened_top}->{returned_top}'

        # Registered module is included in actual downloaded backups and restored by normal import.
        page.locator('#settingsButton').click()
        page.locator('[data-settings-tab="data"]').click()
        with page.expect_download() as download:
            page.locator('#exportData').click()
        backup = json.loads(Path(download.value.path()).read_text())
        assert backup['modules']['experiencePreferences']['pinnedDestinations'] == ['carpeta/Mis lecturas']

        # A late module write failure must roll back the entire import, including
        # preferences/folders/read state already applied before the pin module.
        rejected_backup = copy.deepcopy(backup)
        rejected_backup['preferences'].update(layout='list', density='compact', columns='2',
                                              fontSize='large', cardTitleSize=14,
                                              showImages=False, showSummaries=False)
        rejected_backup['read'] = []
        rejected_backup['saved'] = ['noticia-0']
        rejected_backup['sourceFolders'] = {'Carpeta importada': ['medio-1']}
        rejected_backup['articleTags'] = {'noticia-0': ['Importada']}
        rejected_backup['modules']['experiencePreferences']['pinnedDestinations'] = [CATEGORIES[0]]
        snapshot = """() => ({
          preferences:Object.fromEntries(['layout','density','columns','fontSize','cardTitleSize','showImages','showSummaries'].map(key=>[key,state[key]])),
          read:[...state.read].sort(),saved:[...state.saved].sort(),
          folders:window.RadarLibrary.getSourceGroups(),pins:window.RadarExperience.getPinnedDestinations(),
          storage:Object.fromEntries(Object.keys(localStorage).filter(key=>key.startsWith('radar-')).sort().map(key=>[key,localStorage.getItem(key)])),
          rendered:{profile:document.getElementById('readingProfile').value,
            layout:document.getElementById('articleGrid').className,
            titleSize:document.body.dataset.cardTitleSize,
            articles:[...document.querySelectorAll('#articleGrid>.article-card')].map(node=>node.dataset.articleId)}
        })"""
        before_failed_import = page.evaluate(snapshot)
        page.evaluate("""() => {window.experienceImportSetItem=Storage.prototype.setItem;
          Storage.prototype.setItem=function(key,value){
            if(key==='radar-experience-v1')throw new Error('import quota fixture');
            return window.experienceImportSetItem.call(this,key,value);
          };}""")
        try:
            page.locator('#importData').set_input_files({'name':'rejected-backup.json','mimeType':'application/json','buffer':json.dumps(rejected_backup).encode()})
            expect(page.locator('#dataNotice')).to_contain_text('Se conservaron tus preferencias y lecturas anteriores')
            assert page.evaluate(snapshot) == before_failed_import, 'Failed import changed live state, local data, pins or rendered profile'
            expect(profile).to_have_value(before_failed_import['rendered']['profile'])
        finally:
            page.evaluate('() => {Storage.prototype.setItem=window.experienceImportSetItem;}')

        backup['modules']['experiencePreferences']['pinnedDestinations'] = [CATEGORIES[0], 'unknown-folder']
        page.locator('#importData').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
        expect(page.locator('#dataNotice')).to_contain_text('correctamente')
        assert page.evaluate('window.RadarExperience.getPinnedDestinations()') == [CATEGORIES[0]]
        # Old backups may omit this module and must preserve current pins.
        del backup['modules']['experiencePreferences']
        page.locator('#importData').set_input_files({'name':'old-backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
        expect(page.locator('#dataNotice')).to_contain_text('correctamente')
        assert page.evaluate('window.RadarExperience.getPinnedDestinations()') == [CATEGORIES[0]]
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('#resetSettings').click()
        assert page.evaluate('window.RadarExperience.getPinnedDestinations()') == []
        page.locator('#settingsDone').click()
        page.evaluate('window.scrollTo(0,0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), width
        page.screenshot(path=str(OUTPUT / f'experience-{width}.png'))
        assert not errors, errors
        print(f'{width}px: profiles, font/columns, labels, folders, source search, backup, reset and reader return OK', flush=True)
    finally:
        context.close()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        cert, key = Path(temporary)/'cert.pem', Path(temporary)/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost'],check=True,capture_output=True)
        server = ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'web')))
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert,key)
        server.socket = tls.wrap_socket(server.socket,server_side=True)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with sync_playwright() as driver:
                options = {'headless': True}
                engine = os.environ.get('RADAR_TEST_ENGINE','chromium')
                if engine == 'chromium':
                    options['args'] = ['--no-sandbox','--disable-dev-shm-usage']
                    binary = os.environ.get('RADAR_CHROMIUM_EXECUTABLE') or shutil.which('chromium')
                    if binary:
                        options['executable_path'] = binary
                browser = getattr(driver,engine).launch(**options)
                try:
                    for width in (320,768,1440,1842):
                        exercise(browser,f'https://127.0.0.1:{server.server_port}/',width)
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    main()
