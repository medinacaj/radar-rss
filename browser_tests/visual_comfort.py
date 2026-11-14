"""Visual comfort and native publisher navigation, fixture traffic only."""
import json, os, threading
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import responsive_smoke as fixtures


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),fixtures.QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/'
    output=fixtures.ROOT/'test-results'/'visual-comfort';output.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as driver:
            options={'headless':True}
            if os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['RADAR_CHROMIUM_EXECUTABLE']
            browser=driver.chromium.launch(**options)
            for width in (320,390,768,1440,1842):
                context=browser.new_context(viewport={'width':width,'height':900},service_workers='block',reduced_motion='reduce')
                context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.fulfill(status=200,content_type='text/html',body='<title>Medio original</title>Medio original'))
                docs=deepcopy(fixtures.RESPONSES)
                # Native background tabs in system Chromium bypass Playwright's
                # request routing. Use a local publisher path for modifier tests.
                docs['latest.json']['items'][2]['url']=base+'publisher/2'
                context.route('**/data/**',lambda r:r.fulfill(json=docs[r.request.url.split('/')[-1].split('?')[0]]))
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base+'#noticias');page.wait_for_function('()=>state.ready')
                mobile=width<=640
                if mobile:
                    page.locator('#feedFiltersToggle').click()
                    expect(page.locator('#feedFilterPanel')).to_have_attribute('open','')
                    assert page.locator('#feedFilterPanel').evaluate('n=>n.getBoundingClientRect().bottom<=innerHeight+1')
                    for theme in ('light','dark'):
                        page.evaluate('(theme)=>setTheme(theme,true)',theme)
                        ratio=page.locator('#feedFiltersDone').evaluate("""n=>{
                            const lum=c=>c.match(/[0-9.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
                            const s=getComputedStyle(n),a=lum(s.color),b=lum(s.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                        }""")
                        assert ratio>=4.5,(theme,ratio)
                    page.evaluate("setTheme('light',true)")
                    page.keyboard.press('Escape')
                    expect(page.locator('#feedFilterPanel')).to_be_hidden()
                    expect(page.locator('#feedFiltersToggle')).to_be_focused()
                    page.locator('#feedFiltersToggle').click()
                else:
                    page.locator('#sidebarFeedOptions > summary').click()
                    expect(page.locator('#readingProfile')).to_be_hidden()
                    page.locator('#presentationSummary').click()
                expect(page.locator('#readingProfile')).to_be_visible()
                assert page.locator('#readingProfile').evaluate('n=>Boolean(n.closest("#presentationControl"))')
                page.locator('#presentationTitleSize').select_option('22')
                assert page.evaluate('state.cardTitleSize')==22
                assert page.locator('#settingCardTitleSize').input_value()=='22'
                page.locator('#readingProfile').select_option('compact')
                assert page.evaluate('state.cardTitleSize')==22
                page.locator('#readingProfile').select_option('visual')
                page.locator('#columnsToggle').click();page.locator('#columnsMenu [data-columns="6"]').click()
                assert page.evaluate('state.columns')=='6'
                if mobile:
                    page.locator('#sourceSelect').select_option('medio-1')
                    expect(page.locator('#feedActiveFilters')).to_be_hidden()
                    page.locator('#sourceSelect').select_option('')
                    page.locator('#feedFiltersDone').click()
                    expect(page.locator('#feedFiltersToggle')).to_be_focused()
                else:
                    page.keyboard.press('Escape')
                    expect(page.locator('#readingProfile')).to_be_hidden()
                # Duplicate publisher, read contrast, spacing and touch targets.
                card=page.locator('#articleGrid [data-article-id="noticia-1"]')
                names=card.locator('.article-cover-publisher,.article-meta .publisher').evaluate_all('nodes=>nodes.filter(n=>{const r=n.getBoundingClientRect();return r.width>2&&r.height>2}).length')
                assert names==1
                assert card.aria_snapshot().count('Medio de referencia 1')==1
                page.evaluate("state.density='compact';applyDisplaySettings();render()")
                assert card.locator('.article-cover-publisher,.article-meta .publisher').evaluate_all('nodes=>nodes.filter(n=>{const r=n.getBoundingClientRect();return r.width>2&&r.height>2}).length')==1
                page.evaluate("state.density='comfortable';applyDisplaySettings();render()")
                before=card.locator('.article-title a').evaluate('n=>getComputedStyle(n).color')
                card.locator('.article-read-toggle').click()
                assert card.locator('.article-title a').evaluate('n=>getComputedStyle(n).color')==before
                expect(card.locator('.experience-read-state')).to_have_text('Leída')
                assert card.evaluate('n=>getComputedStyle(n).opacity')=='1'
                # Same-row cards stretch to a consistent height, with auto rows intact.
                assert page.locator('#articleGrid').evaluate('n=>getComputedStyle(n).alignItems')=='stretch'
                assert page.locator('#articleGrid').evaluate('n=>getComputedStyle(n).gridAutoRows')=='auto'
                assert card.locator('.article-content').evaluate('n=>parseFloat(getComputedStyle(n).paddingTop)')<=16
                for button in card.locator('.article-actions button').all():
                    box=button.bounding_box();assert box['width']>=44 and box['height']>=44
                # Primary news links are native source navigation, never a preview.
                title=page.locator('#articleGrid [data-article-id="noticia-0"] .article-title a')
                with context.expect_page() as created:title.click()
                publisher=created.value;publisher.wait_for_load_state();assert publisher.url=='https://example.com/noticias/0';publisher.close()
                expect(page.locator('#articleReaderDialog')).to_be_hidden()
                expect(page.locator('#articleGrid [data-article-id="noticia-0"] .article-title a')).to_be_focused()
                assert page.evaluate("state.read.has('noticia-0')&&state.read.has('noticia-0-alternativa')")
                for how in ('keyboard','middle','control'):
                    title=page.locator('#articleGrid [data-article-id="noticia-2"] .article-title a')
                    with context.expect_page() as created:
                        if how=='keyboard':title.press('Enter')
                        elif how=='middle':title.click(button='middle')
                        else:title.click(modifiers=['Control'])
                    publisher=created.value;publisher.wait_for_url(base+'publisher/2');publisher.close()
                page.locator('#articleGrid [data-article-id="noticia-0"] .article-also').click()
                expect(page.locator('#readerCompare')).to_be_visible();page.locator('#readerClose').click()
                for theme in ('light','dark'):
                    page.evaluate('(theme)=>setTheme(theme,true)',theme)
                    page.evaluate('window.scrollTo(0,0)')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
                    page.screenshot(path=str(output/f'{theme}-{width}.png'))
                # Resize with a sheet open must close it and preserve existing nodes.
                page.set_viewport_size({'width':390,'height':900})
                if not page.locator('#appSidebar').evaluate('n=>n.inert'):page.locator('#menuClose').click()
                page.locator('#feedFiltersToggle').click()
                page.set_viewport_size({'width':1440,'height':900})
                expect(page.locator('#feedFilterPanel')).to_be_hidden()
                assert page.locator('#sourceSelect').count()==1
                assert page.locator('#presentationControl').count()==1
                if not page.locator('#sidebarFeedOptions').evaluate('n=>n.open'):
                    page.locator('#sidebarFeedOptions > summary').click()
                page.locator('#presentationSummary').click();expect(page.locator('#readingProfile')).to_be_visible()
                page.keyboard.press('Escape')
                for target,selector in [('home','#dashboardFeature .article-title a'),('briefing','#briefingSections .briefing-title')]:
                    page.evaluate('(target)=>goTo(target)',target)
                    anchor=page.locator(selector).first;url=anchor.get_attribute('href')
                    with context.expect_page() as created:anchor.click()
                    publisher=created.value;publisher.wait_for_load_state();assert publisher.url==url;publisher.close()
                    expect(page.locator('#articleReaderDialog')).to_be_hidden()
                page.evaluate("goTo('all');state.newTab=false;render()")
                title=page.locator('#articleGrid .article-title a').first;url=title.get_attribute('href');title.click();page.wait_for_url(url)
                page.go_back();page.wait_for_function('()=>state.ready')
                assert page.evaluate('state.read.size>0')
                assert not errors,errors
                context.close();print(f'{width}px: presentation, sheet, cards, contrast, publisher links and comparison OK',flush=True)
            browser.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
