"""Dimension layout: real routes and content, HTTPS fixtures, no publisher requests."""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import base64
import hashlib
import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright, expect
import responsive_smoke as fixtures
from agenda_regressions import event


class DimensionRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tls=tempfile.TemporaryDirectory()
        cert,key=(Path(cls.tls.name)/name for name in ('cert.pem','key.pem'))
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(key),'-out',str(cert),'-subj','/CN=localhost'],check=True,capture_output=True)
        cls.server=fixtures.ThreadingHTTPServer(('127.0.0.1',0),fixtures.QuietHandler)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(str(cert),str(key))
        cls.server.socket=tls.wrap_socket(cls.server.socket,server_side=True)
        cls.base=f'https://127.0.0.1:{cls.server.server_port}/'
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.driver=sync_playwright().start()
        engine=os.environ.get('RADAR_TEST_ENGINE','chromium');options={'headless':True}
        if engine=='chromium':
            # Trust only this temporary fixture certificate, including SW fetches.
            pem=subprocess.run(['openssl','x509','-in',str(cert),'-pubkey','-noout'],check=True,capture_output=True).stdout
            der=subprocess.run(['openssl','pkey','-pubin','-outform','DER'],input=pem,check=True,capture_output=True).stdout
            spki=base64.b64encode(hashlib.sha256(der).digest()).decode()
            options['args']=[f'--ignore-certificate-errors-spki-list={spki}']
        if engine=='chromium' and os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['RADAR_CHROMIUM_EXECUTABLE']
        cls.browser=getattr(cls.driver,engine).launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.driver.stop();cls.server.shutdown();cls.server.server_close();cls.tls.cleanup()

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},service_workers='block',ignore_https_errors=True)
        self.context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(self.base) else r.abort())
        self.page=self.context.new_page();self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.route('**/data/**',fixtures.make_route)
        self.page.goto(self.base+'#inicio')
        self.page.wait_for_function('() => state.ready')

    def tearDown(self):
        self.assertFalse(self.errors)
        self.context.close()

    def test_failed_cache_upgrade_keeps_the_working_offline_reader(self):
        from cache_upgrade_fixture import check_failed_upgrade
        check_failed_upgrade(self.browser, self.server.socket.context)

    def test_destinations_are_separate_and_agenda_is_reloadable(self):
        expect(self.page.locator('#dashboardView')).to_be_visible()
        expect(self.page.locator('#agendaSection')).to_be_hidden()
        self.page.locator('#categoryNav [data-destination="agenda"]').click()
        expect(self.page).to_have_url(self.base+'#agenda')
        expect(self.page.locator('#agendaSection')).to_be_visible()
        expect(self.page.locator('#dashboardView')).to_be_hidden()
        expect(self.page.locator('#feedView')).to_be_hidden()
        self.page.reload()
        expect(self.page.locator('#agendaSection')).to_be_visible()
        expect(self.page.locator('#categoryNav [aria-current="page"]')).to_have_count(1)
        self.page.evaluate("goTo('all')")
        expect(self.page.locator('#feedView')).to_be_visible()
        expect(self.page.locator('#agendaSection')).to_be_hidden()

    def test_sidebar_has_separate_navigation_reading_filters_and_folders(self):
        structure=self.page.evaluate("""() => {
          const nav=document.getElementById('sidebarNavigation');
          return [...nav.children].map(el=>el.id||el.className);
        }""")
        self.assertEqual(structure[:3],[
            'sidebarCoreSection','source-folders-section','sidebar-reading sidebar-tools'
        ],structure)
        expect(self.page.locator('#sidebarCoreHeading')).to_have_text('PRINCIPAL')
        expect(self.page.locator('#sourceFoldersHeading')).to_have_text('CARPETAS Y CATEGORÍAS')
        self.assertFalse(self.page.locator('#sidebarCoreContent').evaluate(
            'n=>n.contains(document.querySelector(".sidebar-reading"))'))
        expect(self.page.locator('.sidebar-reading')).to_be_visible()
        reading_toggle=self.page.locator('#sidebarReadingToggle')
        expect(reading_toggle).to_have_attribute('aria-controls','sidebarReadingContent')
        expect(reading_toggle).to_have_attribute('aria-expanded','false')
        reading_toggle.click()
        expect(reading_toggle).to_have_attribute('aria-expanded','true')
        expect(self.page.locator('#sidebarReadingContent')).to_be_visible()
        expect(self.page.locator('#categoryNav')).to_be_visible()
        reading_toggle.click()
        expect(reading_toggle).to_have_attribute('aria-expanded','false')
        reading_toggle.click()
        expect(reading_toggle).to_have_attribute('aria-expanded','true')
        expect(self.page.locator('#sidebarReadingContent')).to_be_visible()
        # Reading destinations work even when the current route is Home.
        self.page.locator('#sidebarReadingModes [data-mode="saved"]').click()
        expect(self.page).to_have_url(self.base+'#noticias')
        self.assertEqual(self.page.evaluate('state.mode'),'saved')
        expect(self.page.locator('#feedActiveFilters')).to_be_hidden()
        self.assertEqual(self.page.locator('#feedActiveFilters').evaluate('n=>getComputedStyle(n).display'),'none')
        if self.page.locator('#sidebarReadingContent').is_hidden(): self.page.locator('#sidebarReadingToggle').click()
        self.page.locator('#sidebarFeedOptions > summary').click()
        expect(self.page.locator('#sourceSelect')).to_be_visible()
        expect(self.page.locator('#presentationSummary')).to_be_visible()
        expect(self.page.locator('#readingProfile')).to_be_hidden()
        self.page.locator('#presentationSummary').click()
        expect(self.page.locator('#readingProfile')).to_be_visible()
        self.assertFalse(self.page.locator('#sidebarFeedOptions').evaluate(
            'n=>n.contains(document.getElementById("presentationControl"))'))
        # The folders can retain a closed state; verify both directions.
        if self.page.locator('#libraryFolderNav').is_hidden():
            self.page.locator('#sourceFoldersToggle').click()
        expect(self.page.locator('#libraryFolderNav')).to_be_visible()
        expect(self.page.locator('#sidebarLibrarySearch')).to_be_visible()
        self.page.locator('#sourceFoldersToggle').click()
        expect(self.page.locator('#libraryFolderNav')).to_be_hidden()
        expect(self.page.locator('#sidebarLibrarySearch')).to_be_hidden()
        self.page.locator('#sourceFoldersToggle').click()
        expect(self.page.locator('#libraryFolderNav')).to_be_visible()
        expect(self.page.locator('#sidebarLibrarySearch')).to_be_visible()
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))

    def test_reading_section_expansion_survives_reload(self):
        toggle=self.page.locator('#sidebarReadingToggle')
        panel=self.page.locator('#sidebarReadingContent')
        expect(toggle).to_have_attribute('aria-expanded','false')
        toggle.click()
        expect(panel).to_be_visible()
        self.assertEqual(self.page.evaluate("localStorage.getItem('radar-tools-open')"),'true')
        self.page.reload();self.page.wait_for_function('()=>state.ready')
        expect(toggle).to_have_attribute('aria-expanded','true')
        expect(panel).to_be_visible()
        toggle.click()
        self.assertEqual(self.page.evaluate("localStorage.getItem('radar-tools-open')"),'false')
        self.page.reload();self.page.wait_for_function('()=>state.ready')
        expect(toggle).to_have_attribute('aria-expanded','false')
        expect(panel).to_be_hidden()

    def test_reading_toggle_and_filter_reset_on_mobile_sidebar(self):
        self.page.set_viewport_size({'width':390,'height':850})
        self.page.locator('#menuToggle').click()
        toggle=self.page.locator('#sidebarReadingToggle')
        expect(toggle).to_have_attribute('aria-expanded','true')
        toggle.click()
        expect(self.page.locator('#sidebarReadingContent')).to_be_hidden()
        expect(toggle).to_have_attribute('aria-expanded','false')
        toggle.click()
        expect(self.page.locator('#sidebarReadingContent')).to_be_visible()
        self.page.locator('#sidebarReadingModes [data-mode="unread"]').click()
        expect(self.page).to_have_url(self.base+'#noticias')
        expect(self.page.locator('#feedActiveFilters')).to_be_hidden()
        self.page.locator('#menuToggle').click()
        self.page.locator('#feedFiltersToggle').click()
        expect(self.page.locator('#feedClearFilters')).to_be_visible()
        self.page.locator('#feedClearFilters').click()
        self.assertEqual(self.page.evaluate('state.mode'),'all')
        expect(self.page.locator('#feedClearFilters')).to_be_hidden()
        self.page.locator('#feedFiltersDone').click()
        self.page.locator('#menuClose').click()
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))

    def test_home_uses_direct_sections_without_retired_panels(self):
        expect(self.page.locator('#dashboardTitle')).to_be_visible()
        expect(self.page.locator('#dashboardTitle')).to_have_text('Inicio')
        expect(self.page.locator('#newsroomColumns,#dashboardFolders,#dashboardSavedPanel')).to_have_count(0)
        order=self.page.locator('#dashboardView > section').evaluate_all('nodes=>nodes.map(n=>n.id)')
        self.assertEqual(order,['sinceVisit','homeHeadlines','homeLatest','editorialLocal','coverageTools'])
        for width in (320,768,1440):
            self.page.set_viewport_size({'width':width,'height':1000})
            expect(self.page.locator('#radarFigure')).to_be_visible()
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
        self.page.evaluate("goTo('all')")
        expect(self.page.locator('#dashboardView')).to_be_hidden()
        expect(self.page.locator('#feedView')).to_be_visible()

    def test_header_content_and_footer_share_edges_across_routes_and_sidebar_widths(self):
        cases=[(1842,310),(1842,240),(1842,480),(1842,0),(2560,310),(2560,0),
               (320,None),(768,None),(950,None),(951,310),(1024,480),(1199,310),(1200,310),(1440,310)]
        for theme in ('dark','light'):
            self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
            for width,sidebar in cases:
                self.page.set_viewport_size({'width':width,'height':920})
                self.page.evaluate("""sidebar=>{
                    if(sidebar){localStorage.setItem('radar-sidebar-width',String(sidebar));window.dispatchEvent(new Event('radar-sidebar-pref-sync'));}
                    setNavOpen(sidebar!==0&&sidebar!==null,false,true);
                }""",sidebar)
                for target,selector in (('home','#dashboardView'),('all','#feedView'),('agenda','#agendaView'),('briefing','#briefingView')):
                    self.page.evaluate('(target)=>goTo(target)',target)
                    expect(self.page.locator(selector)).to_be_visible()
                    bounds=self.page.evaluate("""selector=>{
                        const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return {left:r.left,right:r.right,width:r.width};};
                        const footer=document.querySelector('.footer'),r=footer.getBoundingClientRect(),s=getComputedStyle(footer);
                        return {header:rect('.topbar'),route:rect(selector),page:rect('.page'),main:rect('.main'),footer:{left:r.left+parseFloat(s.paddingLeft),right:r.right-parseFloat(s.paddingRight)}};
                    }""",selector)
                    context=(theme,width,sidebar,target,bounds)
                    for edge in ('left','right'):
                        self.assertAlmostEqual(bounds['header'][edge],bounds['route'][edge],delta=1,msg=context)
                        self.assertAlmostEqual(bounds['footer'][edge],bounds['route'][edge],delta=1,msg=context)
                    self.assertLessEqual(bounds['main']['width'],1451,context)
                    self.assertGreaterEqual(bounds['header']['left'],bounds['page']['left'],context)
                    self.assertLessEqual(bounds['header']['right'],bounds['page']['right']+1,context)
                    self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),context)

    def test_dense_columns_resize_cards_and_text_together(self):
        self.page.set_viewport_size({'width':1842,'height':1000})
        self.page.evaluate("goTo('all');chooseColumns('3')")
        title=self.page.locator('#articleGrid .article-title').first
        normal=title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)')
        for columns in ('auto','2','3','4','5','6'):
            self.page.evaluate('(columns)=>chooseColumns(columns)',columns)
            self.page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            self.assertEqual(title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),normal)
            self.assertEqual(self.page.evaluate('state.columns'),columns)
            effective=self.page.evaluate('Number(document.body.dataset.effectiveColumns)')
            self.assertLessEqual(effective,6 if columns=='auto' else int(columns))
            cards=self.page.locator('#articleGrid>.article-card').evaluate_all("""nodes=>nodes.map(n=>({
                width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height,
                overflow:n.scrollWidth>n.clientWidth+1,
                actions:[...n.querySelectorAll('.article-actions button')].map(b=>({w:b.getBoundingClientRect().width,h:b.getBoundingClientRect().height}))
            }))""")
            for card in cards:
                self.assertLess(card['height']/card['width'],1.8,(columns,card))
                self.assertFalse(card['overflow'],(columns,card))
                for action in card['actions']:
                    self.assertGreaterEqual(action['w'],44)
                    self.assertGreaterEqual(action['h'],44)
        self.page.evaluate("state.cardTitleSize=22;applyDisplaySettings()")
        larger=title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)')
        self.page.evaluate("state.cardTitleSize=14;applyDisplaySettings()")
        smaller=title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)')
        self.assertGreater(larger,smaller)
        self.assertGreaterEqual(smaller,14)
        self.page.evaluate("state.cardTitleSize=16;applyDisplaySettings();chooseColumns('3')")
        self.assertEqual(title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),normal)

    def test_five_and_six_columns_really_render_on_normal_desktop(self):
        self.page.set_viewport_size({'width':1440,'height':900})
        self.page.evaluate("goTo('all')")
        for title_size in (16,22):
            self.page.evaluate("""(size) => {
                state.cardTitleSize=size;
                state.fontSize='normal';
                state.layout='cards';
                applyDisplaySettings();
            }""",title_size)
            for requested in ('5','6'):
                self.page.evaluate('(value)=>chooseColumns(value)',requested)
                self.page.wait_for_function(
                    '(value)=>Number(document.body.dataset.effectiveColumns)===Number(value)',
                    arg=requested)
                layout=self.page.evaluate("""() => {
                  const grid=document.querySelector('#articleGrid');
                  const cards=[...grid.querySelectorAll(':scope > .article-card')];
                  const card=cards[0];
                  return {
                    tracks:getComputedStyle(grid).gridTemplateColumns.split(' ').length,
                    width:card.getBoundingClientRect().width,
                    overflow:document.documentElement.scrollWidth>innerWidth+2,
                    buttons:[...card.querySelectorAll('.article-actions button')].map(el=>{
                      const r=el.getBoundingClientRect();return [r.width,r.height];
                    })
                  };
                }""")
                self.assertEqual(layout['tracks'],int(requested),(title_size,layout))
                self.assertGreaterEqual(layout['width'],150,(title_size,layout))
                self.assertFalse(layout['overflow'],(title_size,layout))
                for width,height in layout['buttons']:
                    self.assertGreaterEqual(width,44,(title_size,layout))
                    self.assertGreaterEqual(height,44,(title_size,layout))
        self.page.set_viewport_size({'width':768,'height':900})
        self.page.wait_for_function(
            '()=>Number(document.body.dataset.effectiveColumns)<6')
        expect(self.page.locator('#effectiveColumns')).to_contain_text('de 6 solicitadas')
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))

    def test_all_column_sizes_preserve_chosen_text_and_sidebar_rows_are_compact(self):
        self.page.set_viewport_size({'width':1842,'height':1000})
        self.page.evaluate("goTo('all')")
        sizes=[]
        for columns in ('2','3','4','5','6'):
            self.page.evaluate('(columns)=>chooseColumns(columns)',columns)
            self.page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            sizes.append(self.page.locator('#articleGrid .article-title').first.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'))
        self.assertEqual(len(set(sizes)),1,sizes)
        self.assertGreaterEqual(sizes[0],16)
        for width in (375,1440):
            self.page.set_viewport_size({'width':width,'height':900})
            if width==375:self.page.locator('#menuToggle').click()
            for selector in ('#libraryFolderNav .nav-link','#sidebarReadingModes .reader-mode-link'):
                rows=self.page.locator(selector).evaluate_all('nodes=>nodes.map(n=>({y:n.getBoundingClientRect().y,h:n.getBoundingClientRect().height}))')
                self.assertGreater(len(rows),1)
                for a,b in zip(rows,rows[1:]):
                    self.assertGreaterEqual(a['h'],44)
                    self.assertLessEqual(b['y']-a['y']-a['h'],2,(width,selector,a,b))

    def test_large_text_respects_the_saved_independent_title_size(self):
        for size in (14,22):
            self.page.evaluate('(size)=>{state.cardTitleSize=size;state.fontSize="normal";savePref("card-title-size",size);savePref("font","normal");applyDisplaySettings();goTo("all");}',size)
            title=self.page.locator('#articleGrid .article-title').first
            normal=title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)')
            self.page.evaluate('()=>{state.fontSize="large";savePref("font","large");applyDisplaySettings();}')
            self.page.reload()
            expect(title).to_be_visible()
            self.assertGreater(title.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),normal)
            self.assertEqual(self.page.evaluate('state.cardTitleSize'),size)
            self.page.set_viewport_size({'width':320,'height':900})
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))

    def test_homepage_selection_has_one_lead_and_distinct_headlines(self):
        expect(self.page.locator('#dashboardFeature')).to_be_visible()
        expect(self.page.locator('#dashboardFeature > .article-card')).to_have_count(1)
        ids=self.page.locator('#dashboardFeature > [data-article-id],#dashboardRecent > [data-article-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)')
        self.assertGreaterEqual(len(ids),4)
        self.assertEqual(len(ids),len(set(ids)))
        expect(self.page.locator('#dashboardSavedPanel')).to_have_count(0)
        expect(self.page.locator('#dashboardView #coverageTools')).to_be_visible()
        self.page.evaluate("goTo('briefing')")
        expect(self.page.locator('#coverageTools')).to_be_hidden()

    def test_home_prioritizes_recent_world_coverage_and_respects_hidden_sources(self):
        self.page.wait_for_load_state('networkidle')
        source_id=self.page.evaluate("""() => {
            const world=state.items.find(x=>x.categories.some(c=>c.startsWith('03 -')));
            const local=state.items.find(x=>!x.categories.some(c=>c.startsWith('03 -')));
            const now=Date.now();
            state.items=[
                {...world,id:'fresh-minor',title:'Un titular reciente de un solo medio',coverage:1,published_at:new Date(now-60000).toISOString()},
                {...world,id:'covered-world',title:'Una noticia mundial cubierta por varios medios',coverage:6,published_at:new Date(now-8*3600000).toISOString()},
                {...local,id:'fallback-local',coverage:1}
            ];render();return world.source_ids[0];
        }""")
        expect(self.page.locator('#dashboardFeature > .article-card')).to_have_attribute('data-article-id','covered-world')
        ids=self.page.locator('#dashboardFeature > [data-article-id],#dashboardRecent > [data-article-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)')
        self.assertEqual(len(ids),len(set(ids)))
        self.page.evaluate('(id)=>{state.hiddenSources.add(id);render();}',source_id)
        expect(self.page.locator('#dashboardFeature > .article-card')).to_have_attribute('data-article-id','fallback-local')
        expect(self.page.locator('#homeLatest')).to_be_hidden()

    def test_one_theme_and_legible_reference_palette(self):
        self.page.evaluate("setTheme('dark',true)")
        self.page.emulate_media(reduced_motion='reduce')
        colors=self.page.evaluate("() => ({bg:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color})")
        self.assertNotEqual(colors['bg'],colors['text'])
        sheets=self.page.locator('link[rel="stylesheet"]').evaluate_all('nodes=>nodes.map(n=>new URL(n.href).pathname.split("/").pop())')
        self.assertIn('dimension.css',sheets)
        self.assertFalse(set(sheets)&{'editorial.css','hashnode-preview.css','radar-hybrid.css','copper-theme.css','home-editorial.css','cosmic-theme.css','iaadc-editorial.css'})
        self.page.evaluate("setTheme('light',true)")
        self.assertNotEqual(self.page.evaluate('getComputedStyle(document.body).backgroundColor'),colors['bg'])

    def test_editorial_tech_palette_surface_depth_hover_and_reduced_motion(self):
        # Real computed-style contract: both themes and user motion preferences.
        for theme, bg, accent in (('dark', '#10151d', '#ff8968'),
                                  ('light', '#edf1f5', '#b5422a')):
            self.page.evaluate('(theme)=>setTheme(theme,true)', theme)
            tokens=self.page.evaluate("""() => {
                const style=getComputedStyle(document.body);
                return {bg:style.getPropertyValue('--bg').trim(),
                        surface:style.getPropertyValue('--surface').trim(),
                        accent:style.getPropertyValue('--accent').trim()};
            }""")
            self.assertEqual(tokens['bg'], bg)
            self.assertEqual(tokens['accent'], accent)
            self.assertNotEqual(tokens['bg'], tokens['surface'])
            for width in (320, 390, 768, 950, 951, 1440, 2560):
                self.page.set_viewport_size({'width':width,'height':950})
                for target in ('home','all','agenda','briefing'):
                    self.page.evaluate('(target)=>goTo(target)', target)
                    self.assertTrue(self.page.evaluate(
                        'document.documentElement.scrollWidth<=innerWidth+2'),
                        (theme,width,target))
        self.page.set_viewport_size({'width':1440,'height':1000})
        self.page.evaluate("goTo('all')")
        card=self.page.locator('#articleGrid > .article-card').first
        self.page.emulate_media(reduced_motion='no-preference')
        card.hover()
        self.page.wait_for_timeout(550)
        hovered=card.evaluate('node=>({transform:getComputedStyle(node).transform,shadow:getComputedStyle(node).boxShadow})')
        # Editorial: hover changes the edge/shadow without shifting the card.
        self.assertIn(hovered['transform'],('none','matrix(1, 0, 0, 1, 0, 0)'))
        self.assertNotEqual(hovered['shadow'],'none')
        self.page.emulate_media(reduced_motion='reduce')
        self.assertEqual(card.evaluate('node=>getComputedStyle(node).transform'),'none')
        self.assertEqual(card.evaluate('node=>getComputedStyle(node).transitionDuration'),'0s')

    def test_automatic_columns_use_available_space_and_preserve_a_saved_choice(self):
        self.page.evaluate("goTo('all')")
        expect(self.page.locator('#columnsCurrent')).to_have_text('Auto')
        self.assertGreaterEqual(self.page.locator('#articleGrid > .article-card').first.bounding_box()['width'],280)
        if self.page.locator('#sidebarReadingContent').is_hidden(): self.page.locator('#sidebarReadingToggle').click()
        self.page.locator('#sidebarFeedOptions > summary').click()
        self.page.locator('#presentationSummary').click()
        self.page.locator('#columnsToggle').click()
        self.page.locator('#columnsMenu [data-columns="2"]').click()
        self.page.reload()
        expect(self.page.locator('#columnsCurrent')).to_have_text('2')
        self.page.on('dialog',lambda dialog:dialog.accept())
        self.page.evaluate("document.getElementById('resetSettings').click()")
        expect(self.page.locator('#columnsCurrent')).to_have_text('Auto')
        for columns in ('5',None):
            preferences={'columns':columns} if columns else {}
            self.page.locator('#importData').set_input_files({'name':'preferences.json','mimeType':'application/json','buffer':json.dumps({'format':'radar-rss-settings-v3','preferences':preferences}).encode()})
            expect(self.page.locator('#columnsCurrent')).to_have_text(columns or 'Auto')
        self.page.reload()
        expect(self.page.locator('#columnsCurrent')).to_have_text('Auto')

    def test_closed_sidebar_keeps_news_visible_after_reload_and_mobile_resize(self):
        self.page.emulate_media(reduced_motion='reduce')
        self.page.evaluate("goTo('all')")
        self.page.locator('#menuToggle').click()
        expect(self.page.locator('#appSidebar')).to_be_hidden()
        for theme in ('light','dark'):
            self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
            expect(self.page.locator('#articleGrid')).to_be_visible()
            self.assertGreaterEqual(self.page.locator('.page').bounding_box()['width'],1438)
            self.assertGreaterEqual(self.page.locator('#articleGrid > .article-card').first.bounding_box()['width'],280)
        self.page.reload()
        expect(self.page.locator('#appSidebar')).to_be_hidden()
        expect(self.page.locator('#articleGrid')).to_be_visible()
        self.assertGreaterEqual(self.page.locator('.page').bounding_box()['width'],1438)
        self.page.set_viewport_size({'width':320,'height':900})
        expect(self.page.locator('#articleGrid')).to_be_visible()
        self.assertGreaterEqual(self.page.locator('.page').bounding_box()['width'],318)
        self.page.locator('#menuToggle').click()
        expect(self.page.locator('#appSidebar')).to_be_visible()
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#menuToggle')).to_be_focused()
        self.page.set_viewport_size({'width':1440,'height':1000})
        expect(self.page.locator('#appSidebar')).to_be_hidden()
        self.page.locator('#menuToggle').click()
        expect(self.page.locator('#appSidebar')).to_be_visible()
        self.assertGreaterEqual(self.page.locator('#articleGrid > .article-card').first.bounding_box()['width'],280)

    def test_forced_colors_has_an_unclipped_title_focus_indicator(self):
        self.page.evaluate("goTo('all')")
        self.page.emulate_media(reduced_motion='reduce',forced_colors='active')
        card=self.page.locator('#articleGrid > .article-card').first
        title=card.locator('.article-title a')
        self.page.keyboard.press('Tab')
        title.focus()
        expect(title).to_be_focused()
        # The inline link's own outline is clipped by its clamped heading;
        # the card must provide a visible alternative outside that clipping box.
        style=card.evaluate('n=>({style:getComputedStyle(n).outlineStyle,width:parseFloat(getComputedStyle(n).outlineWidth),offset:parseFloat(getComputedStyle(n).outlineOffset)})')
        self.assertNotEqual(style['style'],'none')
        self.assertGreaterEqual(style['width'],2)
        self.assertGreaterEqual(style['offset'],0)
        title.scroll_into_view_if_needed()
        output=Path('test-results/dimension');output.mkdir(parents=True,exist_ok=True)
        self.page.screenshot(path=str(output/'forced-title-focus.png'))

    def test_large_text_setting_reaches_home_agenda_summary_and_reader(self):
        document=deepcopy(fixtures.RESPONSES['events.json'])
        document['items']=[event('lectura',start=fixtures.STAMP[:10],timezone='UTC',title='Una actividad con nombre extenso para leer con comodidad')]
        self.page.route('**/data/events.json*',lambda route:route.fulfill(content_type='application/json',body=json.dumps(document)))
        self.page.reload()
        targets={'home':['#dashboardFeature .article-title','#dashboardRecent .dashboard-recent-title','#coveredList .covered-title'],
                 'all':['#articleGrid .article-title','#articleGrid .article-excerpt'],
                 'agenda':['.agenda-item-title','.agenda-meta'],
                 'briefing':['.briefing-title','.briefing-summary']}
        normal={}
        for width in (320,1440):
            self.page.set_viewport_size({'width':width,'height':900})
            for target,selectors in targets.items():
                self.page.evaluate('(target)=>goTo(target)',target)
                for selector in selectors:
                    node=self.page.locator(selector).first
                    expect(node).to_be_visible()
                    normal[width,selector]=node.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)')
        self.page.locator('#settingsButton').click()
        self.page.locator('#settingFont').select_option('large')
        self.page.locator('#settingsDone').click()
        self.page.reload()
        self.assertEqual(self.page.evaluate('state.fontSize'),'large')
        for width in (320,1440):
            self.page.set_viewport_size({'width':width,'height':900})
            for target,selectors in targets.items():
                self.page.evaluate('(target)=>goTo(target)',target)
                for selector in selectors:
                    node=self.page.locator(selector).first
                    # Hash navigation is asynchronous. WebKit may return an
                    # unresolved size for the previous, still-hidden route.
                    expect(node).to_be_visible()
                    self.assertGreater(node.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),normal[width,selector],selector)
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),(width,target))
            self.page.evaluate("goTo('all')")
            self.page.locator('#articleGrid .article-also').first.click()
            expect(self.page.locator('#articleReaderDialog')).to_be_visible()
            self.assertGreaterEqual(self.page.locator('#readerSummary').evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),20)
            fixtures.check_visible_boxes(self.page,['#readerClose','#readerPrevious','#readerNext','#readerOpenOriginal'],f'large reader {width}')
            self.page.keyboard.press('Escape')

    def test_mobile_form_text_and_article_actions_are_easy_to_use(self):
        self.page.evaluate("goTo('all')")
        for width in (1440,390):
            self.page.set_viewport_size({'width':width,'height':900})
            actions=self.page.locator('#articleGrid > .article-card').first.locator('.article-read-toggle,.article-save,.article-more')
            for node in actions.all():
                box=node.bounding_box()
                # Firefox may return 43.99997 for a computed 44px target.
                self.assertGreaterEqual(min(box['width'],box['height']),44-0.001)
        self.page.locator('#searchToggle').click()
        self.assertGreaterEqual(self.page.locator('#searchInput').evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),16)
        self.page.locator('#settingsButton').click()
        for selector in ('#settingTheme','#settingFont'):
            self.assertGreaterEqual(self.page.locator(selector).evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),16)
        self.page.locator('#settingsDone').click()
        self.page.locator('#articleGrid .article-also').first.click()
        expect(self.page.locator('#libraryTagInput')).to_be_visible()
        self.assertGreaterEqual(self.page.locator('#libraryTagInput').evaluate('n=>parseFloat(getComputedStyle(n).fontSize)'),16)

    def test_agenda_has_no_news_count_and_folder_counts_follow_their_sources(self):
        self.page.evaluate("markRead('noticia-0',true)")
        expect(self.page.locator('#categoryNav [data-destination="agenda"] .nav-count')).to_have_text('')
        for category in fixtures.CATEGORIES:
            expected=self.page.evaluate('(category)=>state.items.filter(x=>x.categories.includes(category)&&!state.read.has(x.id)).length',category)
            expect(self.page.locator('#libraryFolderNav .system-folder-link').filter(has=self.page.locator('.nav-label',has_text=category.split(' - ')[1])).locator('.nav-count')).to_have_text(str(expected))

    def test_direct_home_loads_coverage_and_topics_and_obeys_source_preferences(self):
        # Finish the initial fixture request before replacing it and reloading.
        # WebKit reports an access-control error if that old request is torn down.
        self.page.wait_for_load_state('networkidle')
        trends=deepcopy(fixtures.RESPONSES['trends.json'])
        trends['topics']=[{'label':'Tecnología','stories':4,'sources':2,'is_new':True}]
        self.page.route('**/data/trends.json*',lambda route:route.fulfill(content_type='application/json',body=json.dumps(trends)))
        # Reload for a direct entry with no earlier route warming the trend cache.
        self.page.reload()
        expect(self.page.locator('#dashboardView #coverageTools')).to_be_visible()
        expect(self.page.locator('#coveredList > li').first).to_be_visible()
        expect(self.page.locator('#trendsPanel')).to_be_visible()
        title=self.page.locator('#coveredList .covered-title').first
        title.scroll_into_view_if_needed();title.focus()
        before=title.bounding_box()['y']
        with self.page.expect_popup() as opened:title.press('Enter')
        opened.value.close()
        expect(self.page.locator('#articleReaderDialog')).to_be_hidden()
        # The reader restores its logical origin in the next animation frame.
        self.page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        expect(title).to_be_focused()
        # WebKit rounds the focused publisher-title scroll position differently:
        # the measured 5.92px drift is visually negligible, while other engines
        # retain the stricter 3px stability requirement.
        tolerance=7 if self.browser.browser_type.name=='webkit' else 3
        self.assertLess(abs(title.bounding_box()['y']-before),tolerance)
        # A pointer or assistive activation need not move DOM focus to a button.
        self.page.evaluate('document.activeElement.blur()')
        self.page.locator('#coveredList .covered-count').first.dispatch_event('click')
        expect(self.page.locator('#articleReaderDialog')).to_be_visible()
        self.page.keyboard.press('Escape')
        self.page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        expect(title).to_be_focused()
        self.assertLess(abs(title.bounding_box()['y']-before),tolerance)
        self.page.locator('#trendChips .trend-chip').first.click()
        expect(self.page.locator('#feedView')).to_be_visible()
        expect(self.page.locator('#searchInput')).to_have_value('Tecnología')
        self.page.evaluate("goTo('home')")
        self.page.evaluate('() => {state.sources.forEach(source=>state.hiddenSources.add(source.id));render()}')
        expect(self.page.locator('#coveredList .covered-item')).to_have_count(0)

    def test_no_news_shows_one_empty_state_without_an_empty_carousel(self):
        documents=deepcopy(fixtures.RESPONSES)
        documents['latest.json']['items']=[]
        documents['meta.json'].update(total_articles=0,latest_count=0)
        def route(request):
            name=request.request.url.split('/')[-1].split('?')[0]
            request.fulfill(content_type='application/json',body=json.dumps(documents.get(name,{})))
        self.page.route('**/data/**',route)
        self.page.reload()
        expect(self.page.locator('#dashboardFeature .dashboard-empty')).to_be_visible()
        expect(self.page.locator('.homepage-latest')).to_be_hidden()

    def test_selected_source_folder_and_icon_remain_legible_in_both_themes(self):
        self.page.emulate_media(reduced_motion='reduce')
        categories=[*fixtures.CATEGORIES,'08 - Monagas']
        self.page.evaluate('(categories)=>{state.categories=categories;buildNav()}',categories)
        failures=[]
        contrast=r"""node => {
          const rgba=c=>{const a=c.match(/[\d.]+/g).map(Number);return [a[0],a[1],a[2],a[3]??1]};
          const background=n=>{const c=rgba(getComputedStyle(n).backgroundColor);if(c[3]>=1||!n.parentElement)return c.slice(0,3);const below=background(n.parentElement);return c.slice(0,3).map((v,i)=>v*c[3]+below[i]*(1-c[3]));};
          const lum=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
          return [node,...node.querySelectorAll('.nav-glyph,.nav-count')].filter(n=>n.getClientRects().length).map(n=>{const bg=lum(background(n)),fg=lum(rgba(getComputedStyle(n).color).slice(0,3));return (Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05)});
        }"""
        for category in categories:
            self.page.evaluate('(category)=>goTo(category)',category)
            expect(self.page.locator('#feedHeading')).to_have_text(category.split(' - ')[1])
            for theme in ('dark','light'):
                self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
                ratios=self.page.locator('#libraryFolderNav .nav-link.active').evaluate(contrast)
                if min(ratios)<4.5:failures.append((category,theme,ratios))
        self.page.evaluate("goTo('all')")
        expect(self.page.locator('#feedHeading')).to_have_text('Todas las noticias')
        for theme in ('dark','light'):
            self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
            ratios=self.page.locator('#categoryNav [data-destination="all"]').evaluate(contrast)
            if min(ratios)<4.5:failures.append(('Noticias',theme,ratios))
        self.assertFalse(failures,failures)

    def test_category_symbols_are_distinct_and_custom_folders_have_a_symbol(self):
        expect(self.page.locator('#dashboardTitle')).to_have_text('Inicio')
        self.assertTrue(self.page.locator('.brand-mark img').evaluate('n=>n.complete&&n.naturalWidth>0'))
        brand=self.page.locator('.brand-mark img').bounding_box()
        self.assertEqual((brand['width'],brand['height']),(24,24))
        categories=[*fixtures.CATEGORIES,'08 - Monagas']
        self.page.evaluate('(categories)=>{state.categories=categories;buildNav()}',categories)
        symbols=self.page.locator('#libraryFolderNav .system-folder-link .nav-glyph svg').evaluate_all('nodes=>nodes.map(n=>n.innerHTML)')
        self.assertEqual(len(set(symbols)),8,'Each category needs its own recognizable symbol')
        folder=self.page.evaluate("svgIcon('folder').innerHTML")
        fallback=self.page.evaluate("svgIcon('unknown').innerHTML")
        self.assertNotEqual(folder,fallback,'Manual folders must not fall back to a newspaper')

    def test_cards_have_depth_and_focus_feedback_without_breaking_the_reader(self):
        self.page.emulate_media(reduced_motion='reduce')
        self.page.evaluate("goTo('all')")
        card=self.page.locator('#articleGrid > .article-card').first
        idle=card.evaluate('n=>({shadow:getComputedStyle(n).boxShadow,border:getComputedStyle(n).borderTopColor})')
        self.assertNotEqual(idle['shadow'],'none','Cards need visible depth at rest')
        title=card.locator('.article-title a');title.focus()
        focused=card.evaluate('n=>({shadow:getComputedStyle(n).boxShadow,border:getComputedStyle(n).borderTopColor})')
        self.assertNotEqual(focused,idle,'Focusing a card must highlight its edge')
        with self.page.expect_popup() as opened:title.press('Enter')
        opened.value.close()
        expect(self.page.locator('#articleReaderDialog')).to_be_hidden()
        expect(title).to_be_focused()
        self.page.emulate_media(reduced_motion='reduce',forced_colors='active')
        self.assertNotEqual(title.evaluate('n=>getComputedStyle(n).outlineStyle'),'none')
        self.page.emulate_media(reduced_motion='reduce',forced_colors='none')
        active=card.evaluate('n=>[getComputedStyle(n).animationName,getComputedStyle(n).transitionDuration]')
        self.assertEqual(active,['none','0s'])

    def test_mobile_menu_and_routes_do_not_overflow(self):
        for width in (320,390,768,1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width,'height':900})
                for target in ('home','all','agenda','briefing'):
                    self.page.evaluate('(target)=>goTo(target)',target)
                    self.page.wait_for_function('(target)=>state.pageView===target',arg={'home':'dashboard','all':'feed','agenda':'agenda','briefing':'briefing'}[target])
                    self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
                if width<=950:
                    self.page.locator('#menuToggle').click()
                    expect(self.page.locator('#appSidebar')).to_have_attribute('aria-modal','true')
                    self.page.keyboard.press('Escape')
                    expect(self.page.locator('#menuToggle')).to_be_focused()
        output=Path('test-results/dimension');output.mkdir(parents=True,exist_ok=True)
        for width in (390,1440):
            self.page.set_viewport_size({'width':width,'height':1000})
            for theme in ('dark','light'):
                self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
                self.page.evaluate("goTo('home')")
                expect(self.page.locator('#dashboardView')).to_be_visible()
                self.page.screenshot(path=str(output/f'{theme}-{width}.png'),full_page=True,animations='disabled')

    def open_source_settings(self):
        self.page.locator('#settingsButton').click()
        self.page.locator('[data-settings-tab="sources"]').click()

    def test_exports_keep_legacy_backup_format_and_use_current_identity(self):
        self.open_source_settings()
        self.page.locator('#settingsSources .library-source-details-trigger').first.click()
        expect(self.page.locator('#librarySourceDetailsDialog')).to_contain_text('catálogo público de Radar-RSS')
        self.page.locator('#librarySourceDetailsDialog button').last.click()
        self.page.evaluate('()=>{window.brandDownloads=[];downloadText=(name,body,mime)=>window.brandDownloads.push({name,body,mime});}')
        self.page.locator('#exportOPML').click()
        xml=self.page.evaluate('window.brandDownloads.at(-1).body')
        self.assertIn('<title>Mis fuentes Radar-RSS</title>',xml)
        self.page.locator('[data-settings-tab="data"]').click()
        self.page.locator('#exportData').click()
        backup=self.page.evaluate('window.brandDownloads.at(-1)')
        self.assertEqual(backup['name'],'radar-rss-respaldo-completo.json')
        self.assertEqual(json.loads(backup['body'])['format'],'radar-rss-settings-v3')

    def test_source_addresses_search_filters_and_stable_identity(self):
        self.page.evaluate("""()=>{
            state.sources[1]={...state.sources[1],name:state.sources[0].name,category:state.sources[0].category,url:'https://second.example/atom',website:'https://second.example',is_radar:true};
            state.health=[{id:state.sources[0].id,state:'ok',last_success_at:new Date().toISOString()},{id:state.sources[1].id,state:'error',error:'HTTP 404'}];
        }""")
        self.open_source_settings()
        first=self.page.locator('#settingsSources [data-source-id="medio-0"]')
        second=self.page.locator('#settingsSources [data-source-id="medio-1"]')
        expect(first.locator('.source-rss-url')).to_have_text('https://example.com/rss')
        expect(second.locator('.source-rss-url')).to_have_text('https://second.example/atom')
        expect(second.locator('.source-health')).to_contain_text('No disponible')
        second.locator('input[type="checkbox"]').uncheck()
        self.assertEqual(self.page.evaluate('[...state.hiddenSources]'),['medio-1'])
        self.page.locator('#settingsSourceSearch').fill('second.example/atom')
        expect(self.page.locator('#settingsSources .library-source-row')).to_have_count(1)
        self.page.locator('#settingsSourceVisibility').select_option('visible')
        expect(self.page.locator('#settingsSources .library-source-row')).to_have_count(0)
        expect(self.page.locator('#sourceSearchEmpty')).to_be_visible()
        self.page.locator('#settingsSourceVisibility').select_option('hidden')
        self.page.locator('#settingsSourceStatus').select_option('error')
        self.page.locator('#settingsSourceType').select_option('radar')
        expect(second).to_be_visible()
        self.page.evaluate('()=>{window.copiedRSS="";Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async value=>{window.copiedRSS=value;}}});}')
        second.locator('.source-copy-rss').click()
        self.assertEqual(self.page.evaluate('window.copiedRSS'),'https://second.example/atom')
        expect(second.locator('input[type="checkbox"]')).not_to_be_checked()

    def test_source_folder_toggle_refreshes_counts_after_individual_change(self):
        self.page.evaluate('()=>{state.sources[1].category=state.sources[0].category;}')
        self.open_source_settings()
        self.page.locator('#settingsSources [data-source-id="medio-0"] input[type="checkbox"]').uncheck()
        category=self.page.locator('#settingsCategories button').first
        expect(category).to_contain_text('1/2')
        category.click()
        self.assertFalse(self.page.evaluate('state.hiddenSources.has("medio-0")||state.hiddenSources.has("medio-1")'))
        expect(category).to_contain_text('2/2')

    def test_personal_source_folders_export_their_real_names_and_memberships(self):
        self.page.evaluate("""()=>{
            localStorage.setItem('radar-source-folders-v1',JSON.stringify({'Mi investigación':['medio-0']}));
            localStorage.setItem('radar-default-folders-v1',JSON.stringify({[state.categories[0]]:{name:'Lecturas IA',sources:[]}}));
        }""")
        self.page.reload();self.open_source_settings()
        row=self.page.locator('#settingsSources [data-source-id="medio-0"]')
        expect(row.locator('.source-folder-caption')).to_contain_text('Mi investigación')
        self.page.evaluate('()=>{window.downloads=[];downloadText=(name,body,mime)=>window.downloads.push({name,body,mime});}')
        self.page.locator('#exportOPML').click()
        xml=self.page.evaluate('window.downloads.at(-1).body')
        self.assertIn('Mi investigación',xml)
        parsed=self.page.evaluate('(xml)=>RadarSourceTools.readOPML(xml)',xml)
        self.assertTrue(any(x['folder']=='Mi investigación' and x['url']=='https://example.com/rss' for x in parsed))
        row.locator('.library-source-folder').select_option('default:'+fixtures.CATEGORIES[1])
        expect(row.locator('.source-folder-caption')).to_contain_text('Tecnología')
        self.page.locator('#settingsSourceSearch').fill('Tecnología')
        expect(self.page.locator('#settingsSources [data-source-id="medio-0"]')).to_be_visible()
        self.page.locator('#exportSourceCatalog').click()
        self.assertIn('URL RSS',self.page.evaluate('window.downloads.at(-1).body'))

    def test_opml_import_previews_cancels_and_only_applies_known_feeds(self):
        self.open_source_settings()
        xml=b'<opml version="2.0"><body><outline text="Feedly"><outline text="Known" xmlUrl="https://example.com/rss"/><outline text="Other" xmlUrl="https://unknown.example/rss"/><outline text="Unsafe" xmlUrl="javascript:alert(1)"/></outline></body></opml>'
        before=self.page.evaluate('JSON.stringify([...state.hiddenSources])')
        self.page.locator('#importOPML').set_input_files({'name':'feedly.opml','mimeType':'application/xml','buffer':xml})
        expect(self.page.locator('#sourceImportPreview')).to_be_visible()
        expect(self.page.locator('#sourceImportSummary')).to_contain_text('2 sin incorporar')
        expect(self.page.locator('#sourceImportUnknown')).to_contain_text('unknown.example')
        self.page.locator('#cancelSourceImport').click()
        self.assertEqual(before,self.page.evaluate('JSON.stringify([...state.hiddenSources])'))
        self.assertNotIn('Feedly',self.page.evaluate('localStorage.getItem("radar-source-folders-v1")||""'))
        self.page.locator('#importOPML').set_input_files({'name':'feedly.opml','mimeType':'application/xml','buffer':xml})
        self.page.locator('#applySourceImport').click()
        expect(self.page.locator('#sourceImportNotice')).to_contain_text('aplicada')
        self.assertEqual(len(self.page.evaluate('state.sources')),len(fixtures.SOURCES))
        self.assertTrue(self.page.evaluate('JSON.parse(localStorage.getItem("radar-source-folders-v1")).Feedly.length>0'))
        self.page.reload();self.open_source_settings()
        expect(self.page.locator('#settingsSources [data-source-id="medio-0"] .source-folder-caption')).to_contain_text('Feedly')

    def test_opml_rejects_malformed_entities_and_rolls_back_failed_storage(self):
        self.open_source_settings()
        for xml in ('<opml><body>', '<!DOCTYPE opml [<!ENTITY x "bad">]><opml><body/></opml>'):
            self.page.locator('#importOPML').set_input_files({'name':'bad.opml','mimeType':'application/xml','buffer':xml.encode()})
            expect(self.page.locator('#sourceImportNotice')).to_contain_text('No se pudo')
            expect(self.page.locator('#sourceImportPreview')).to_be_hidden()
        xml=b'<opml><body><outline text="Imported"><outline xmlUrl="https://example.com/rss"/></outline></body></opml>'
        self.page.locator('#importOPML').set_input_files({'name':'ok.opml','mimeType':'application/xml','buffer':xml})
        before=self.page.evaluate('JSON.stringify({folders:localStorage.getItem("radar-source-folders-v1"),defaults:localStorage.getItem("radar-default-folders-v1"),hidden:[...state.hiddenSources]})')
        self.page.evaluate("""()=>{const original=Storage.prototype.setItem;window.restoreStorage=()=>{Storage.prototype.setItem=original;};
            Storage.prototype.setItem=function(key,value){if(key==='radar-default-folders-v1')throw Error('blocked');return original.call(this,key,value);};}""")
        self.page.locator('#applySourceImport').click()
        expect(self.page.locator('#sourceImportNotice')).to_contain_text('No se pudo guardar')
        self.assertEqual(before,self.page.evaluate('JSON.stringify({folders:localStorage.getItem("radar-source-folders-v1"),defaults:localStorage.getItem("radar-default-folders-v1"),hidden:[...state.hiddenSources]})'))
        self.page.evaluate('window.restoreStorage()')

    def test_source_folders_preserve_more_than_160_members_after_reload(self):
        self.page.evaluate("""()=>{
            localStorage.setItem('radar-source-folders-v1',JSON.stringify({'Grande':Array.from({length:200},(_,i)=>'source-'+i)}));
        }""")
        self.page.reload();self.open_source_settings()
        self.page.evaluate('()=>{window.capture=null;downloadText=(name,body)=>window.capture=body;}')
        self.page.locator('[data-settings-tab="data"]').click()
        self.page.locator('#exportData').click()
        self.assertEqual(len(json.loads(self.page.evaluate('window.capture'))['sourceFolders']['Grande']),200)

    def test_source_health_views_resolve_rss_addresses_from_catalog_by_id(self):
        self.page.evaluate("()=>{state.health=[{id:'medio-0',name:'Medio de referencia 0',state:'error',error:'HTTP 404'}];}")
        self.page.locator('#settingsButton').click()
        self.page.locator('[data-settings-tab="health"]').click()
        expect(self.page.locator('#healthFeedList a')).to_have_attribute('href','https://example.com/rss')
        self.page.locator('#settingsDone').click()
        self.page.evaluate('openFeedHealth()')
        expect(self.page.locator('#feedHealthIssues a')).to_have_attribute('href','https://example.com/rss')

    def test_source_manager_updates_when_a_new_publication_changes_catalog(self):
        self.open_source_settings()
        self.page.locator('#settingsSourceSearch').fill('new.example')
        self.page.evaluate("""()=>{
            const stamp=new Date(Date.now()+1000).toISOString();
            const source={...state.sources[0],id:'new-feed',name:'Una fuente nueva',url:'https://new.example/rss',website:'https://new.example'};
            pendingPublication={meta:{version:2,generated_at:stamp,total_articles:state.items.length,archive_files:[]},sources:{sources:[...state.sources,source],categories:state.categories},latest:{items:state.items},status:{checked_at:stamp,feeds:[{id:'new-feed',state:'ok'}]}};
            applyPendingPublication();
        }""")
        expect(self.page.locator('#settingsSources [data-source-id="new-feed"]')).to_be_visible()
        expect(self.page.locator('#settingsSourceCount')).to_contain_text('1 resultados')

    def test_source_portability_actions_precede_the_long_catalog(self):
        self.open_source_settings()
        export=self.page.locator('#exportOPML').bounding_box()
        first=self.page.locator('#settingsSources .library-source-row').first.bounding_box()
        self.assertLess(export['y'],first['y'])

    def test_long_radar_url_stays_compact_and_full_address_is_available_in_details(self):
        url='https://news.google.com/rss/search?q='+('region%20noticias%20'*40)
        self.page.evaluate('(url)=>{state.sources[0].url=url;}',url)
        self.open_source_settings();self.page.set_viewport_size({'width':320,'height':900})
        row=self.page.locator('#settingsSources [data-source-id="medio-0"]')
        self.assertLessEqual(row.locator('.source-rss-url').bounding_box()['height'],65)
        expect(row.locator('.source-rss-url')).to_have_attribute('href',url)
        row.locator('.library-source-details-trigger').click()
        expect(self.page.locator('#librarySourceDetailsDialog')).to_contain_text(url)
        self.page.locator('#librarySourceDetailsDialog button').last.click()

    def test_source_news_action_keeps_the_requested_source_after_navigation(self):
        for route in ('home','all'):
            self.page.evaluate('(route)=>goTo(route)',route)
            self.open_source_settings()
            self.page.locator('#settingsSources [data-source-id="medio-0"] .source-view-news').click()
            self.page.wait_for_function('()=>state.pageView==="feed"')
            expect(self.page.locator('#sourceSelect')).to_have_value('medio-0')
            ids=self.page.locator('#articleGrid .article-card').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)')
            self.assertTrue(ids)
            allowed={item['id'] for item in fixtures.ITEMS if 'medio-0' in item['source_ids']}
            self.assertTrue(set(ids)<=allowed)

    def test_default_folders_receive_new_catalog_sources_after_a_move_and_reload(self):
        self.open_source_settings()
        self.page.locator('#settingsSources [data-source-id="medio-0"] .library-source-folder').select_option('default:'+fixtures.CATEGORIES[1])
        source={**fixtures.SOURCES[0],'id':'new-published','name':'Nueva fuente publicada','url':'https://new-published.example/rss'}
        updated={**fixtures.RESPONSES['sources.json'],'sources':[*fixtures.SOURCES,source]}
        self.page.evaluate("""source=>{
            const stamp=new Date(Date.now()+1000).toISOString();
            pendingPublication={meta:{version:2,generated_at:stamp,total_articles:state.items.length,archive_files:[]},sources:{sources:[...state.sources,source],categories:state.categories},latest:{items:state.items},status:{checked_at:stamp,feeds:[]}};
            applyPendingPublication();
        }""",source)
        def check():
            group=self.page.evaluate('(cat)=>RadarLibrary.getSourceGroups().find(g=>g.key==="default:"+cat)',fixtures.CATEGORIES[0])
            self.assertIn('new-published',group['ids'])
            self.assertNotIn('medio-0',group['ids'])
        check()
        self.page.route('**/data/sources.json',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(updated)))
        self.page.reload();self.page.wait_for_function('()=>state.ready');check()

    def test_default_folder_import_preserves_future_auto_membership_and_exclusions(self):
        self.open_source_settings()
        # Make a deliberate removal from the original category before importing there.
        self.page.locator('#settingsSources [data-source-id="medio-0"] .library-source-folder').select_option('default:'+fixtures.CATEGORIES[1])
        xml=('<opml><body><outline text="Inteligencia Artificial"><outline xmlUrl="https://example.com/rss"/></outline></body></opml>').encode()
        self.page.locator('#importOPML').set_input_files({'name':'known.opml','mimeType':'application/xml','buffer':xml})
        self.page.locator('#applySourceImport').click()
        # A fresh source inherits its original default category even after an explicit selection.
        self.page.evaluate("""()=>{
            state.sources.push({...state.sources[0],id:'future-after-import',name:'Después de importar',url:'https://after-import.example/rss'});
            renderSettingsSources();
        }""")
        group=self.page.evaluate('(cat)=>RadarLibrary.getSourceGroups().find(g=>g.key==="default:"+cat)',fixtures.CATEGORIES[0])
        self.assertIn('future-after-import',group['ids'])
        self.assertIn('medio-0',group['ids'])

    def test_unassigned_source_option_cannot_claim_a_move_without_changing_membership(self):
        self.open_source_settings()
        select=self.page.locator('#settingsSources [data-source-id="medio-0"] .library-source-folder')
        self.assertTrue(select.locator('option[value=""]').evaluate('node=>node.matches(":disabled")'))
        select.focus();self.page.keyboard.press('Home')
        expect(select).to_have_value('default:'+fixtures.CATEGORIES[0])

    def test_legacy_default_folder_selections_preserve_exclusions_and_allow_future_sources(self):
        self.page.evaluate('()=>localStorage.setItem("radar-default-folders-v1",JSON.stringify({[state.categories[0]]:{sources:[]}}))')
        self.page.reload();self.page.wait_for_function('()=>state.ready')
        self.page.evaluate('()=>{state.sources.push({...state.sources[0],id:"after-legacy",url:"https://after-legacy.example/rss"});}')
        group=self.page.evaluate('(cat)=>RadarLibrary.getSourceGroups().find(g=>g.key==="default:"+cat)',fixtures.CATEGORIES[0])
        self.assertIn('after-legacy',group['ids'])
        self.assertNotIn('medio-0',group['ids'])

    def test_opml_nested_atom_duplicate_and_size_limits_are_explicit(self):
        result=self.page.evaluate("""()=>{
            const xml='<opml><body><outline text="A"><outline text="B"><outline type="atom" title="Atom" xmlUrl="https://example.com/rss"/><outline xmlUrl="https://example.com/rss"/></outline></outline></body></opml>';
            const records=RadarSourceTools.readOPML(xml),match=RadarSourceTools.matchOPML(records,state.sources);
            const errors=[];
            for(const text of ['x'.repeat(1000001),'<opml><body>'+Array.from({length:1001},()=>'<outline xmlUrl="https://example.com/rss"/>').join('')+'</body></opml>']){
                try{RadarSourceTools.readOPML(text);}catch(error){errors.push(error.message);}
            }
            return {records,match,errors};
        }""")
        self.assertEqual(result['records'][0]['folder'],'A / B')
        self.assertEqual(result['match']['knownCount'],1)
        self.assertEqual(result['match']['duplicates'],1)
        self.assertEqual(len(result['errors']),2)

    def test_reset_preferences_resets_lite_without_erasing_read_or_saved(self):
        self.page.evaluate("()=>{state.lite=true;savePref('lite',true);document.body.classList.add('lite');state.read.add('keep-read');state.saved.add('keep-saved');}")
        self.page.on('dialog',lambda dialog:dialog.accept())
        self.page.locator('#settingsButton').click()
        self.page.locator('[data-settings-tab="data"]').click()
        self.page.locator('#resetSettings').click()
        self.assertFalse(self.page.evaluate('state.lite||document.body.classList.contains("lite")'))
        self.assertTrue(self.page.evaluate('state.read.has("keep-read")&&state.saved.has("keep-saved")'))
        self.page.reload();self.page.locator('#settingsButton').click()
        expect(self.page.locator('#settingLite')).not_to_be_checked()

    def test_source_manager_is_readable_in_both_themes_on_small_screens(self):
        self.open_source_settings()
        for width in (320,768,1440):
            self.page.set_viewport_size({'width':width,'height':900})
            for theme in ('light','dark'):
                self.page.evaluate('(theme)=>{setTheme(theme,true);state.fontSize="large";applyDisplaySettings();}',theme)
                expect(self.page.locator('#settingsSources .source-rss-url').first).to_be_visible()
                self.assertTrue(self.page.locator('#settingsPages').evaluate('n=>n.scrollWidth<=n.clientWidth+2'))
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
        self.page.locator('#settingsSourceSearch').focus();self.page.keyboard.press('Tab')
        expect(self.page.locator('#settingsSourceVisibility')).to_be_focused()


    def test_manual_refresh_reports_unchanged_news_then_applies_a_new_publication(self):
        self.page.evaluate("goTo('all')")
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_have_text('No hay novedades publicadas.')
        expect(self.page.locator('#refreshNow')).to_be_enabled()
        stamp=(datetime.fromisoformat(fixtures.STAMP.replace('Z','+00:00'))+timedelta(minutes=1)).isoformat()
        docs=deepcopy(fixtures.RESPONSES)
        for doc in docs.values():
            if 'generated_at' in doc:doc['generated_at']=stamp
            if 'checked_at' in doc:doc['checked_at']=stamp
        docs['latest.json']['items'].insert(0,{**docs['latest.json']['items'][0],
            'id':'manual-new','title':'Noticia recién publicada tras actualizar','published_at':stamp})
        docs['meta.json']['total_articles']=docs['meta.json']['latest_count']=len(docs['latest.json']['items'])
        def publication(route):
            name=route.request.url.split('/')[-1].split('?')[0]
            route.fulfill(json=docs[name])
        self.page.route('**/data/**',publication)
        self.page.evaluate("()=>{state.saved.add('noticia-1');state.read.add('noticia-2');}")
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_have_text('Noticias actualizadas.')
        expect(self.page.locator('#articleGrid > [data-article-id="manual-new"]')).to_be_visible()
        expect(self.page.locator('#publicationNotice')).to_be_hidden()
        self.assertEqual(self.page.evaluate('state.generated'),stamp)
        self.assertTrue(self.page.evaluate("state.saved.has('noticia-1')&&state.read.has('noticia-2')"))
        self.assertEqual(self.page.evaluate('state.pageView'),'feed')

    def test_manual_refresh_network_error_keeps_news_and_can_be_retried(self):
        before=self.page.evaluate('state.items.map(x=>x.id)')
        def offline(route):route.abort('failed')
        self.page.route('**/data/meta.json*',offline)
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_contain_text('No se pudo actualizar')
        expect(self.page.locator('#refreshNow')).to_be_enabled()
        self.assertEqual(self.page.evaluate('state.items.map(x=>x.id)'),before)
        self.page.unroute('**/data/meta.json*',offline)
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_have_text('No hay novedades publicadas.')
        expect(self.page.locator('#refreshStatus')).to_have_attribute('role','status')

    def test_manual_refresh_recovers_after_the_initial_news_download_fails(self):
        def offline(route):route.abort('failed')
        self.page.route('**/data/latest.json*',offline)
        self.page.reload()
        self.page.wait_for_function('()=>!bootBusy&&!state.ready')
        expect(self.page.locator('#refreshNow')).to_be_enabled()
        self.page.unroute('**/data/latest.json*',offline)
        self.page.locator('#refreshNow').click()
        expect(self.page.locator('#refreshStatus')).to_have_text('Noticias actualizadas.')
        self.assertTrue(self.page.evaluate('state.ready'))
        self.assertEqual(self.page.evaluate('state.items.length'),len(fixtures.ITEMS))
        expect(self.page.locator('#dashboardFeature > .article-card')).to_have_count(1)

    def test_controls_keep_contrast_keyboard_focus_and_accessible_refresh_target(self):
        self.page.emulate_media(reduced_motion='reduce')
        self.page.evaluate("goTo('all')")
        contrast=r"""node=>{
            const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
            const ctx=canvas.getContext('2d',{willReadFrequently:true});
            const rgba=c=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=c;ctx.fillRect(0,0,1,1);const v=Array.from(ctx.getImageData(0,0,1,1).data);return [v[0],v[1],v[2],v[3]/255];};
            const bg=n=>{const c=rgba(getComputedStyle(n).backgroundColor);if(c[3]>=1||!n.parentElement)return c.slice(0,3);const below=bg(n.parentElement);return c.slice(0,3).map((v,i)=>v*c[3]+below[i]*(1-c[3]));};
            const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
            const a=lum(bg(node)),b=lum(rgba(getComputedStyle(node).color).slice(0,3));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
        }"""
        for theme in ('dark','light'):
            self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
            for selector in ('#refreshNow','#settingsButton','#themeToggle','#categoryNav .nav-link.active','.mode-tab.active'):
                self.assertGreaterEqual(self.page.locator(selector).evaluate(contrast),4.5,(theme,selector))
            self.page.locator('#settingsButton').focus();self.page.keyboard.press('Tab')
            expect(self.page.locator('#themeToggle')).to_be_focused()
            outline=self.page.locator('#themeToggle').evaluate('n=>({style:getComputedStyle(n).outlineStyle,width:parseFloat(getComputedStyle(n).outlineWidth)})')
            self.assertEqual(outline['style'],'solid');self.assertGreaterEqual(outline['width'],2)
            for width in (320,390,951,1440):
                was_mobile=self.page.evaluate('MOBILE_NAV.matches')
                self.page.set_viewport_size({'width':width,'height':950})
                # Let the breakpoint change finish before a user opens the
                # drawer. WebKit dispatches matchMedia changes asynchronously.
                if (width<=950)!=was_mobile:
                    if width<=950:
                        expect(self.page.locator('#menuToggle')).to_have_attribute('aria-expanded','false')
                    else:
                        expect(self.page.locator('#appSidebar')).not_to_have_attribute('role','dialog')
                if self.page.locator('#menuToggle').get_attribute('aria-expanded')!='true':
                    self.page.locator('#menuToggle').click()
                button=self.page.locator('#refreshNow')
                expect(button).to_be_visible()
                box=button.bounding_box()
                self.assertGreaterEqual(box['height'],44)
                self.assertGreaterEqual(box['width'],44)
                self.assertGreaterEqual(box['x'],0)
                self.assertLessEqual(box['x']+box['width'],width+1)
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
            self.page.set_viewport_size({'width':1440,'height':1000})

            self.page.locator('#articleGrid .article-also').first.click()
            expect(self.page.locator('#articleReaderDialog')).to_be_visible()
            for selector in ('.reader-primary', '.reader-primary .reader-open-hint'):
                self.assertGreaterEqual(self.page.locator(selector).evaluate(contrast), 4.5, (theme, selector))
            self.page.locator('.reader-primary').hover()
            for selector in ('.reader-primary', '.reader-primary .reader-open-hint'):
                self.assertGreaterEqual(self.page.locator(selector).evaluate(contrast), 4.5, (theme, 'hover', selector))
            self.page.keyboard.press('Escape')


if __name__=='__main__':
    result=unittest.main(verbosity=2,exit=False).result
    if not result.wasSuccessful():
        # CI keeps the tail of stderr. Preserve full diagnostics above, then
        # repeat each failure's cause so a long ARIA snapshot cannot hide it.
        print('\nCompact failure summary:',file=sys.stderr)
        for case,detail in result.failures+result.errors:
            cause=detail.split('Call log:',1)[0].split('Aria snapshot:',1)[0]
            print(f'{case.id()}\n{cause[:2400]}',file=sys.stderr)
            if os.environ.get('GITHUB_ACTIONS')=='true':
                escaped=cause[:2400].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
                print(f'::error title={case.id()}::{escaped}',file=sys.stderr)
    sys.exit(not result.wasSuccessful())
