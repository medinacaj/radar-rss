"""Offline editorial journeys: one digest, attributable duplicates and type filters."""
import json
import os
import threading
from copy import deepcopy
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
import responsive_smoke as fixtures


def main():
    categories = [*fixtures.CATEGORIES, '08 - Monagas']
    sources = deepcopy(fixtures.SOURCES)
    sources.append({'id':'medio-7', 'name':'Medio de Monagas', 'category':categories[-1],
                    'url':'https://example.com/rss', 'website':'https://example.com', 'is_radar':False})
    items = []
    for index in range(24):
        source = sources[index % len(sources)]
        item = deepcopy(fixtures.ITEMS[index % len(fixtures.ITEMS)])
        item.update(id=f'editorial-{index}', title=f'Historia de la comunidad sobre obras y servicios número {index}',
                    url=f'https://example.com/editorial/{index}', publisher=source['name'], source=source['name'],
                    source_ids=[source['id']], categories=[source['category']], coverage=1, also_in=[], image=None)
        if index < 4:
            item['content_type'] = ['news','opinion','analysis','press_release'][index]
        items.append(item)
    # A duplicate outlet with its own metadata and publication text.
    duplicate = deepcopy(items[0])
    duplicate.update(id='editorial-duplicate', url='https://second.example/same-story',
                     source_ids=['medio-1'], publisher='Otro diario', source='Otro diario')
    items.append(duplicate)
    data = deepcopy(fixtures.RESPONSES)
    data['sources.json'] = {'version':1, 'categories':categories, 'sources':sources}
    data['latest.json']['items'] = items
    data['meta.json'].update(total_articles=len(items), latest_count=len(items), archive_files=[])

    def route(request):
        name = request.request.url.split('/')[-1].split('?')[0]
        if name in data:
            request.fulfill(status=200, content_type='application/json', body=json.dumps(data[name]))
        else:
            request.fulfill(status=404, body='{}')

    server = ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            options = {'headless':True, 'args':['--no-sandbox']}
            if os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
                options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
            browser = p.chromium.launch(**options)
            for width in (320, 1440):
                context = browser.new_context(viewport={'width':width,'height':900},
                                              service_workers='block', reduced_motion='reduce')
                context.route('**/*',lambda r:r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
                page = context.new_page()
                page.route('**/data/**',route)
                errors = []
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/#resumen')
                rows = page.locator('#briefingSections .briefing-item')
                expect(rows).to_have_count(7)
                assert page.locator('.editorial-digest').count() == 1
                expect(page.locator('#v12BriefingScope')).to_be_visible()
                assert rows.first.locator('time').get_attribute('datetime')
                assert 'medios' in rows.first.inner_text()
                assert 'Medio de referencia 0' in rows.first.inner_text()
                assert page.locator('#briefingSections [data-article-id="editorial-duplicate"]').count() == 0
                page.evaluate("""() => {
                    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copiedDigest=text;}}});
                    Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{cancel(){},speak(value){window.spokenDigest=value.text;}}});
                    render();
                }""")
                visible_titles = rows.locator('.briefing-title').all_text_contents()
                page.locator('#briefingCopy').click()
                page.wait_for_function('() => Boolean(window.copiedDigest)')
                page.locator('#briefingListen').click()
                page.wait_for_function('() => Boolean(window.spokenDigest)')
                assert page.evaluate('window.copiedDigest === window.spokenDigest')
                copied = page.evaluate('window.copiedDigest')
                assert all(title in copied for title in visible_titles)
                page.locator('#briefingStop').click()
                # The digest reader owns the displayed sequence even if a feed
                # type/source/search selection remains active in the background.
                page.evaluate("""() => {
                    const select=document.getElementById('editorialType'); select.value='opinion';
                    select.dispatchEvent(new Event('change',{bubbles:true}));
                    state.search='not in the digest'; state.feed='medio-7';
                }""")
                rows.first.locator('.briefing-coverage').click()
                expect(page.locator('#readerTitle')).to_have_text(visible_titles[0])
                page.locator('#readerNext').click()
                expect(page.locator('#readerTitle')).to_have_text(visible_titles[1])
                page.locator('#readerPrevious').click()
                expect(page.locator('#readerTitle')).to_have_text(visible_titles[0])
                page.locator('#readerClose').click()
                page.evaluate("""() => {
                    state.search=''; state.feed='';
                    const select=document.getElementById('editorialType'); select.value='all';
                    select.dispatchEvent(new Event('change',{bubbles:true}));
                }""")
                rows.first.locator('.briefing-coverage').click()
                expect(page.locator('#articleReaderDialog')).to_be_visible()
                assert 'Otro diario' in page.locator('#readerCompare').inner_text()
                assert page.locator('#readerCompare a[href="https://second.example/same-story"]').count() == 1
                page.locator('#readerClose').click()
                page.locator('#v12BriefingScope').select_option('cat:08 - Monagas')
                expect(rows).to_have_count(3)
                assert all('Monagas' in value for value in rows.all_text_contents())
                # A source hidden by the reader cannot enter the selected digest.
                page.evaluate("state.hiddenSources.add('medio-7'); render()")
                expect(rows).to_have_count(0)
                expect(page.locator('#briefingListen')).to_be_disabled()
                page.evaluate("state.hiddenSources.clear(); goTo('all')")
                page.wait_for_function("() => state.pageView==='feed'")
                if width <= 640:
                    page.locator('#feedFiltersToggle').click()
                else:
                    page.locator('#sidebarFeedOptions > summary').click()
                expect(page.locator('#editorialType')).to_be_visible()
                page.locator('#editorialType').select_option('opinion')
                expect(page.locator('#articleGrid .article-card')).to_have_count(1)
                expect(page.locator('#allCount')).to_have_text('1')
                expect(page.locator('#feedActiveFilters')).to_be_hidden()
                # Desktop topbar filters close after each change; reopen to adjust again.
                if width>640:page.locator('#sidebarFeedOptions > summary').click()
                page.locator('#editorialType').select_option('all')
                expect(page.locator('#editorialType')).to_have_value('all')
                expect(page.locator('#articleGrid .article-card')).to_have_count(24)
                if width>640:page.locator('#sidebarFeedOptions > summary').click()
                page.locator('#editorialType').select_option('unknown')
                expect(page.locator('#articleGrid .article-card')).to_have_count(20)
                if width>640:page.locator('#sidebarFeedOptions > summary').click()
                expect(page.locator('#feedClearFilters')).to_be_visible()
                page.locator('#feedClearFilters').click()
                expect(page.locator('#editorialType')).to_have_value('all')
                if width<=640:
                    page.locator('#feedFiltersDone').click()
                # Type is a view filter, so it never changes stored preferences.
                assert page.evaluate("!Object.keys(localStorage).some(k=>k.includes('editorial-type'))")
                page.evaluate("goTo('home')")
                page.wait_for_function("() => state.pageView==='dashboard'")
                expect(page.locator('#editorialLocal')).to_be_visible()
                assert page.locator('#editorialLocal .editorial-local-row').count() <= 3
                page.evaluate("localStorage.setItem('radar-experience-v1',JSON.stringify({pinnedDestinations:['08 - Monagas']}))")
                page.reload()
                expect(page.locator('#editorialLocal')).to_be_visible()
                assert all('Monagas' in text for text in page.locator('#editorialLocal .editorial-local-row').all_text_contents())
                # A surviving source must not expose a hidden grouped lead or
                # hidden alternative, either in cards or inside the reader.
                page.evaluate("""() => {
                    state.items=[{id:'private-group',title:'Titular del medio oculto',url:'https://hidden.example/story',
                      publisher:'Editor oculto',source:'Editor oculto',source_ids:['medio-0','medio-1'],
                      categories:['01 - Inteligencia Artificial','02 - Tecnología'],published_at:new Date().toISOString(),
                      summary:'Texto reservado al editor oculto',image:'https://hidden.example/image',content_type:'news',coverage:2,
                      also_in:[{id:'visible-version',title:'Titular publicado por el medio visible',url:'https://visible.example/story',
                        publisher:'Editor visible',source_id:'medio-1',category:'02 - Tecnología',
                        published_at:new Date().toISOString(),content_type:'opinion'}]}];
                    state.hiddenSources=new Set(['medio-0']); goTo('all');
                }""")
                page.wait_for_function("() => state.pageView==='feed'")
                expect(page.locator('#articleGrid .article-card')).to_have_count(1)
                assert 'Editor oculto' not in page.locator('#articleGrid').inner_text()
                assert 'Texto reservado' not in page.locator('#articleGrid').inner_text()
                page.evaluate("openArticleReader(applyFilters()[0],null,'compare')")
                expect(page.locator('#readerTitle')).to_have_text('Titular publicado por el medio visible')
                assert 'Editor oculto' not in page.locator('#articleReaderDialog').inner_text()
                expect(page.locator('#readerCompare')).to_have_count(0)
                page.locator('#readerClose').click()
                page.evaluate("state.hiddenSources=new Set(['medio-1']); render()")
                assert 'Editor visible' not in page.locator('#articleGrid').inner_text()
                page.evaluate("openArticleReader(applyFilters()[0],null,'compare')")
                expect(page.locator('#readerTitle')).to_have_text('Titular del medio oculto')
                assert 'Editor visible' not in page.locator('#articleReaderDialog').inner_text()
                expect(page.locator('#readerCompare')).to_have_count(0)
                page.locator('#readerClose').click()
                # Guardadas intentionally survives source hiding, including its
                # original attribution and the complete saved reader sequence.
                page.evaluate("""() => {
                    state.items.push({id:'saved-hidden-only',title:'Historia guardada de una fuente oculta',
                      url:'https://visible.example/saved-only',publisher:'Editor visible',source:'Editor visible',
                      source_ids:['medio-1'],categories:['02 - Tecnología'],published_at:new Date().toISOString()});
                    state.saved=new Set(['private-group','saved-hidden-only']);
                    state.hiddenSources=new Set(['medio-0','medio-1']);state.mode='saved';render();
                }""")
                expect(page.locator('#articleGrid .article-card')).to_have_count(2)
                expect(page.locator('#savedCount')).to_have_text('2')
                page.locator('#articleGrid [data-article-id="private-group"] .article-also').click()
                expect(page.locator('#readerTitle')).to_have_text('Titular del medio oculto')
                assert 'Editor oculto' in page.locator('#readerCompare').inner_text()
                assert 'Editor visible' in page.locator('#readerCompare').inner_text()
                page.locator('#readerNext').click()
                expect(page.locator('#readerTitle')).to_have_text('Historia guardada de una fuente oculta')
                page.locator('#readerPrevious').click()
                expect(page.locator('#readerTitle')).to_have_text('Titular del medio oculto')
                page.locator('#readerClose').click()
                page.evaluate("state.mode='all'; render()")
                expect(page.locator('#articleGrid .article-card')).to_have_count(0)
                # Real archived saved stories survive leaving the current feed.
                # Exercise library's private archive through the public API.
                page.evaluate("""() => {
                    localStorage.setItem('radar-saved',JSON.stringify(['cached-story']));
                    localStorage.setItem('radar-saved-archive-v1',JSON.stringify([{
                      id:'cached-story',title:'Una noticia guardada del archivo anterior',url:'https://cached.example/story',
                      source_ids:['medio-0','medio-1'],categories:['01 - Inteligencia Artificial'],publisher:'Medio original',
                      published_at:new Date().toISOString(),coverage:2,editorial_member_ids:['cached-story','cached-alternate'],
                      also_in:[{id:'cached-alternate',url:'https://alternate.example/story',title:'Otro titular atribuido',publisher:'Medio alternativo',source_id:'medio-1'}]
                    }]));
                }""")
                page.reload()
                page.evaluate("state.items=[];state.mode='saved';goTo('all');state.mode='saved';render()")
                expect(page.locator('#articleGrid .article-card')).to_have_count(1)
                page.evaluate("openArticleReader(applyFilters()[0],null,'compare')")
                expect(page.locator('#readerTitle')).to_have_text('Una noticia guardada del archivo anterior')
                assert page.evaluate("state.read.has('cached-story')&&state.read.has('cached-alternate')")
                assert 'Medio alternativo' in page.locator('#readerCompare').inner_text()
                page.locator('#readerClose').click()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                assert not errors, errors
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print('OK: 7-story digest, scope/hidden-source selection, attributed comparison, type counts/reset and mobile')


if __name__ == '__main__':
    main()
