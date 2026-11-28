"""Offline agenda contracts: local days, reader filters, safe data and refresh.

Run with Playwright's Chromium or RADAR_CHROMIUM_EXECUTABLE=/usr/bin/chromium.
Only HTTP data is replaced; the real static app and its render pipeline run.
"""
import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect
import responsive_smoke as fixtures

STAMP = '2026-10-25T03:59:30Z'
OLD = '2026-07-01T00:00:00Z'
CHILE = '07 - Concepción'
MONAGAS = '08 - Monagas'


def event(key, start='2026-10-25', **changes):
    row = dict(id=key, title=f'Actividad {key}', url=f'https://example.com/eventos/{key}',
               source_id='medio-6', source_name='Medio de Concepción', category=CHILE,
               timezone='America/Santiago', start_date=start, end_date=None,
               status='scheduled', location=None, announced_at=OLD,
               first_seen_at=OLD, last_seen_at=STAMP,
               date_evidence={'kind': 'rss', 'value': start, 'url': f'https://example.com/eventos/{key}'})
    row.update(changes)
    return row


def document():
    pending = event('sin-fecha', None, end_date=None, timezone=None, date_evidence=None,
                    reason='date_unverified', announced_at=None)
    postponed = event('aplazado', None, date_evidence=None, reason='postponed', status='postponed')
    return dict(version=1, generated_at=STAMP, horizon_days=90, sources=[],
                items=[event('viejo-futuro', '2026-11-01'),
                       event('multidia', '2026-10-20', end_date='2026-10-26', location='Teatro local'),
                       event('hoy-chile'), event('ayer-chile', '2026-10-24'),
                       event('ayer-venezuela', '2026-10-24', timezone='America/Caracas',
                             source_id='medio-7', category=MONAGAS),
                       event('hoy-venezuela', timezone='America/Caracas', source_id='medio-7', category=MONAGAS),
                       event('limite90', '2027-01-23'), event('fuera90', '2027-01-24'),
                       event('cancelado', status='cancelled'),
                       event('texto', title='<img src=x onerror=alert(1)> & feria'),
                       event('anio-deducido', '2026-11-05',
                             date_evidence={'kind': 'text', 'value': '2026-11-05', 'year_inferred': True,
                                            'url': 'https://example.com/eventos/anio-deducido'})],
                pending=[pending, postponed])


def review_regressions(browser, server):
    """Catch boot coupling, automatic focus loss, and unreadable active dates."""
    selected = os.environ.get('RADAR_AGENDA_REVIEW_ONLY')
    for case in ('boot', 'focus', 'contrast', 'mixed_generation', 'mine_boot', 'mine_slow'):
        if selected and selected != case:
            continue
        payload = document()
        mine = case in ('mine_boot', 'mine_slow')
        state = {'event_status': 200, 'news_status': 503 if case in ('boot', 'mine_boot') else 200,
                 'hold': mine, 'route': None, 'source_route': None}

        def route_data(route):
            name = Path(urlsplit(route.request.url).path).name
            if name == 'events.json':
                if state['hold']:
                    state['route'] = route
                else:
                    route.fulfill(status=state['event_status'], content_type='application/json', body=json.dumps(payload))
            elif name == 'status.json' and state['news_status'] != 200:
                route.fulfill(status=state['news_status'], body='Unavailable')
            elif name == 'sources.json' and case == 'mine_slow':
                state['source_route'] = route
            else:
                fixtures.make_route(route)

        context = browser.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block', reduced_motion='reduce')
        if mine:
            context.add_init_script("localStorage.setItem('radar-v12-preferences', JSON.stringify({mine:true,categories:['08 - Monagas']}))")
        context.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
        page = context.new_page()
        page.clock.install(time=datetime(2026, 10, 25, 3, 59, 30, tzinfo=timezone.utc))
        page.route('**/data/**', route_data)
        page.goto(f'http://127.0.0.1:{server.server_port}/#agenda')
        if mine:
            assert page.evaluate('state.categories.length') == 0
            # Hold events until this observer is attached: every rendered output
            # before/after the delayed catalog must honor the saved selection.
            observations = page.evaluate_handle("""() => {
              const seen=[];
              const observer=new MutationObserver(()=>{
                seen.push([...document.querySelectorAll('#agendaList [data-event-id], #agendaPendingList [data-event-id]')].map(n=>n.dataset.eventId));
              });
              observer.observe(document.getElementById('agendaSection'),{childList:true,subtree:true});
              return {seen,observer};
            }""")
            assert state['route'] is not None
            state['hold'] = False
            state['route'].fulfill(status=200, content_type='application/json', body=json.dumps(payload))
            expect(page.locator('#agendaList [data-event-id="hoy-venezuela"]')).to_have_count(1)
            allowed = {'ayer-venezuela', 'hoy-venezuela'}
            shown = page.locator('#agendaList [data-event-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.eventId)')
            assert shown and set(shown) <= allowed, (case, shown)
            expect(page.locator('#agendaPending')).to_be_hidden()
            if case == 'mine_slow':
                assert state['source_route'] is not None
                state['source_route'].fulfill(status=200, content_type='application/json', body=json.dumps(fixtures.RESPONSES['sources.json']))
                page.wait_for_function('() => state.ready')
            else:
                page.clock.run_for(61_000)
                assert page.evaluate('state.ready') is False
            page.evaluate('window.RadarAgenda.refresh()')
            expect(page.locator('#agendaList [data-event-id="hoy-venezuela"]')).to_be_visible()
            rendered = observations.evaluate('observation=>observation.seen')
            assert rendered and all(set(ids) <= allowed for ids in rendered), (case, rendered)
            observations.evaluate('observation=>observation.observer.disconnect()')
        elif case == 'boot':
            page.clock.run_for(61_000)
            # A failed news resource cannot leave the independent agenda busy.
            expect(page.locator('#agendaSection')).to_have_attribute('aria-busy', 'false')
            if page.locator('#agendaRetry').is_visible():
                page.locator('#agendaRetry').click()
            expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
            assert page.evaluate('state.ready') is False
            state['event_status'] = 503
            page.evaluate('window.RadarAgenda.refresh()')
            expect(page.locator('#agendaRetry')).to_be_visible()
            state['event_status'] = 200
            page.locator('#agendaRetry').click()
            expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
            # Once a news generation is known it still rejects another one.
            page.evaluate("state.generated='2026-10-25T04:00:00Z';window.RadarAgenda.refresh()")
            expect(page.locator('#agendaStatus')).to_contain_text('No se pudo')
        elif case == 'focus':
            row = page.locator('#agendaList [data-event-id="multidia"] a')
            expect(row).to_be_visible()
            row.focus()
            handle = row.element_handle()
            page.clock.run_for(31_000)
            expect(row).to_be_focused()
            assert row.evaluate('(n, old) => n === old', handle)
            for action in ('document.dispatchEvent(new Event("visibilitychange"))', 'window.dispatchEvent(new Event("focus"))'):
                page.evaluate(action)
                expect(row).to_be_focused()
                assert row.evaluate('(n, old) => n === old', handle)
            payload['items'][1]['title'] = 'Actividad con título actualizado'
            page.evaluate('window.RadarAgenda.refresh()')
            expect(row).to_have_text('Actividad con título actualizado')
            expect(row).to_be_focused()
            page.locator('#agendaPending > summary').click()
            pending = page.locator('#agendaPendingList [data-event-id="sin-fecha"] a')
            pending.focus()
            handle = pending.element_handle()
            page.clock.run_for(31_000)
            expect(pending).to_be_focused()
            assert pending.evaluate('(n, old) => n === old', handle)
            page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
            expect(pending).to_be_focused()
            payload['pending'][0]['title'] = 'Anuncio actualizado'
            page.evaluate('window.RadarAgenda.refresh()')
            expect(pending).to_have_text('Anuncio actualizado')
            expect(pending).to_be_focused()
            assert page.locator('#agendaPending').get_attribute('open') is not None
        elif case == 'mixed_generation':
            expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
            state['hold'] = True
            page.evaluate("state.generated='2026-10-25T04:00:00Z';render()")
            expect(page.locator('#agendaSection')).to_have_attribute('aria-busy', 'true')
            expect(page.locator('#agendaList li')).to_have_count(0)
            expect(page.locator('#agendaPendingList li')).to_have_count(0)
            payload['generated_at'] = '2026-10-25T04:00:00Z'
            assert state['route'] is not None
            state['route'].fulfill(status=200, content_type='application/json', body=json.dumps(payload))
            expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
        else:
            expect(page.locator('#agendaList .agenda-date').first).to_be_visible()
            for theme in ('light', 'dark'):
                page.evaluate('theme => setTheme(theme, true)', theme)
                if page.locator('#agendaPending').get_attribute('open') is None:
                    page.locator('#agendaPending > summary').click()
                ratios = page.evaluate(r"""() => {
                  const rgb=color=>color.match(/[\d.]+/g).slice(0,3).map(Number);
                  const luminance=color=>rgb(color).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
                  const contrast=(a,b)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
                  return [...document.querySelectorAll('.agenda-controls [aria-pressed="true"], #agendaList .agenda-date, #agendaPendingList .agenda-date')].map(n=>{
                    let bg=n;while(getComputedStyle(bg).backgroundColor==='rgba(0, 0, 0, 0)')bg=bg.parentElement;
                    return {text:n.textContent, ratio:contrast(getComputedStyle(n).color,getComputedStyle(bg).backgroundColor)};
                  });
                }""")
                assert ratios and all(row['ratio'] >= 4.5 for row in ratios), (theme, ratios)
                print(f'contrast {theme}: minimum {min(row["ratio"] for row in ratios):.2f}:1')
        context.close()
        print(f'OK: agenda review {case}')


def main():
    fixtures.CATEGORIES = (*fixtures.CATEGORIES, MONAGAS)
    fixtures.SOURCES.append(dict(id='medio-7', name='Medio de Monagas', category=MONAGAS,
                                url='https://example.com/rss', website='https://example.com', is_radar=False))
    fixtures.RESPONSES['sources.json']['categories'] = list(fixtures.CATEGORIES)
    fixtures.RESPONSES['latest.json']['generated_at'] = STAMP
    fixtures.RESPONSES['meta.json']['generated_at'] = STAMP
    for row in fixtures.ITEMS:
        row['published_at'] = STAMP
    payload = document()
    mode = {'status': 200, 'hold': False, 'route': None}

    def data_route(route):
        if Path(urlsplit(route.request.url).path).name != 'events.json':
            fixtures.make_route(route)
        elif mode['hold']:
            mode['route'] = route
        else:
            route.fulfill(status=mode['status'], content_type='application/json', body=json.dumps(payload))

    server = ThreadingHTTPServer(('127.0.0.1', 0), fixtures.QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    screenshots = Path(os.environ.get('RADAR_SCREENSHOTS', '/tmp/radar-agenda'))
    screenshots.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            options = dict(headless=True, args=['--no-sandbox'])
            if os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
                options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
            browser = p.chromium.launch(**options)
            review_regressions(browser, server)
            if os.environ.get('RADAR_AGENDA_REVIEW_ONLY'):
                browser.close()
                return
            for width in (375, 1440):
                payload = document()
                context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block', reduced_motion='reduce')
                context.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.clock.install(time=datetime(2026, 10, 25, 3, 59, 30, tzinfo=timezone.utc))
                page.route('**/data/**', data_route)
                mode['hold'] = True
                page.goto(f'http://127.0.0.1:{server.server_port}/#agenda')
                expect(page.locator('#agendaStatus')).to_contain_text('Cargando')
                page.wait_for_function("() => typeof window.RadarAgenda === 'object'")
                assert mode['route'] is not None
                mode['hold'] = False
                mode['route'].fulfill(status=200, content_type='application/json', body=json.dumps(payload))
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
                expect(page.locator('#agendaList [data-event-id="ayer-chile"]')).to_have_count(0)
                expect(page.locator('#agendaList [data-event-id="ayer-venezuela"]')).to_be_visible()
                expect(page.locator('#agendaList [data-event-id="limite90"]')).to_be_visible()
                expect(page.locator('#agendaList [data-event-id="fuera90"]')).to_have_count(0)
                expect(page.locator('#agendaList [data-event-id="multidia"]')).to_contain_text('Teatro local')
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_contain_text('Anunciado')
                expect(page.locator('#agendaList [data-event-id="hoy-chile"]')).to_contain_text('Lugar por confirmar')
                # D-11: un año deducido de la fecha del anuncio queda señalado en la ficha.
                expect(page.locator('#agendaList [data-event-id="anio-deducido"] .agenda-year-note')).to_contain_text('año deducido del anuncio')
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"] .agenda-year-note')).to_have_count(0)
                expect(page.locator('#agendaList [data-event-id="cancelado"]')).to_have_count(0)
                expect(page.locator('#agendaPending')).to_be_visible()
                page.locator('#agendaPending > summary').click()
                expect(page.locator('#agendaPendingList [data-event-id="aplazado"]')).to_contain_text('Aplazada')
                expect(page.locator('#agendaPendingList [data-event-id="sin-fecha"]')).to_contain_text('Fecha por confirmar')
                expect(page.locator('#agendaPendingList [data-event-id="sin-fecha"]')).not_to_contain_text('Anunciado')
                expect(page.locator('#agendaPendingList [data-event-id="cancelado"]')).to_contain_text('Cancelada')
                page.locator('#agendaPending > summary').click()
                assert page.locator('#agendaList img').count() == 0
                expect(page.locator('#agendaList [data-event-id="texto"] a')).to_have_text('<img src=x onerror=alert(1)> & feria')
                assert page.locator('#agendaList a').first.get_attribute('rel') == 'noopener noreferrer external'
                expect(page.get_by_role('heading', name='En portada', exact=True)).to_be_hidden()
                expect(page.locator('#dashboardFeature')).to_be_hidden()
                expect(page.locator('#newsroomColumns,#dashboardFolders')).to_have_count(0)
                assert page.locator('#libraryFolderNav .system-folder-link').count() == 8
                page.locator('[data-agenda-days="0"]').click()
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_have_count(0)
                expect(page.locator('#agendaList [data-event-id="multidia"]')).to_be_visible()
                page.locator('[data-agenda-days="7"]').click()
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
                page.locator('[data-agenda-days="30"]').click()
                expect(page.locator('#agendaList [data-event-id="limite90"]')).to_have_count(0)
                page.locator('[data-agenda-days="90"]').click()
                page.locator('[data-agenda-days="90"]').focus()
                page.clock.run_for(60_000)
                expect(page.locator('#agendaList [data-event-id="ayer-venezuela"]')).to_have_count(0)
                expect(page.locator('[data-agenda-days="90"]')).to_be_focused()
                page.clock.set_system_time(datetime(2026, 10, 26, 2, 59, 30, tzinfo=timezone.utc))
                page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
                expect(page.locator('#agendaList [data-event-id="hoy-chile"]')).to_be_visible()
                page.clock.run_for(60_000)
                expect(page.locator('#agendaList [data-event-id="hoy-chile"]')).to_have_count(0)
                expect(page.locator('#agendaList [data-event-id="hoy-venezuela"]')).to_be_visible()
                page.clock.set_system_time(datetime(2026, 10, 25, 4, 1, tzinfo=timezone.utc))
                page.evaluate("state.hiddenSources.add('medio-6'); render()")
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_have_count(0)
                expect(page.locator('#agendaPending')).to_be_hidden()
                page.evaluate("state.hiddenSources.clear(); render()")
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
                page.screenshot(path=str(screenshots / f'agenda-{width}.png'), full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                page.evaluate("goTo('07 - Concepción')")
                expect(page.locator('#agendaSection')).to_be_hidden()
                expect(page.locator('#articleGrid .article-card').first).to_be_visible()
                page.evaluate("state.mode='saved';goTo('all')")
                expect(page.locator('#feedView')).to_be_visible()
                page.evaluate("location.hash='#agenda'")
                expect(page.locator('#agendaSection')).to_be_visible()
                payload['items'] = [event('actualizada', '2026-11-05')]
                payload['pending'] = []
                page.evaluate('window.RadarAgenda.refresh()')
                expect(page.locator('#agendaList [data-event-id="actualizada"]')).to_be_visible()
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_have_count(0)
                # A new publication generation must trigger a new agenda load.
                payload['generated_at'] = '2026-10-25T04:00:00Z'
                payload['items'] = [event('nueva-generacion', '2026-11-06')]
                page.evaluate("state.generated='2026-10-25T04:00:00Z';state.feedMeta.generated_at=state.generated;render()")
                expect(page.locator('#agendaList [data-event-id="nueva-generacion"]')).to_be_visible()
                payload['generated_at'] = STAMP
                page.evaluate('window.RadarAgenda.refresh()')
                expect(page.locator('#agendaStatus')).to_contain_text('No se pudo')
                payload['generated_at'] = '2026-10-25T04:00:00Z'
                payload['items'] = []
                page.evaluate('window.RadarAgenda.refresh()')
                expect(page.locator('#agendaStatus')).to_contain_text('No hay actividades')
                assert page.locator('#agendaList li').count() == 0
                for malformed in [dict(version='1'), dict(items='bad'), dict(items=[event('bad', '2026-02-30')]),
                                  dict(items=[event('bad', timezone='Mars/Unknown')]),
                                  dict(items=[event('bad', url='javascript:alert(1)')]),
                                  dict(items=[event('bad', end_date='2026-01-01')])]:
                    payload = dict(document(), **malformed)
                    payload['generated_at'] = '2026-10-25T04:00:00Z'
                    page.evaluate('window.RadarAgenda.refresh()')
                    expect(page.locator('#agendaStatus')).to_contain_text('No se pudo')
                    assert page.locator('#agendaList li').count() == 0
                mode['status'] = 404
                page.evaluate('window.RadarAgenda.refresh()')
                expect(page.locator('#agendaStatus')).to_contain_text('No se pudo')
                expect(page.locator('#agendaRetry')).to_be_visible()
                payload = document()
                payload['generated_at'] = '2026-10-25T04:00:00Z'
                mode['status'] = 200
                page.locator('#agendaRetry').click()
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_be_visible()
                page.evaluate("localStorage.setItem('radar-v12-preferences', JSON.stringify({mine:true,categories:['08 - Monagas']}))")
                page.reload()
                # Boot has STAMP again; align the fixture generation.
                payload['generated_at'] = STAMP
                page.evaluate('window.RadarAgenda.refresh()')
                expect(page.locator('#agendaList [data-event-id="hoy-venezuela"]')).to_be_visible()
                expect(page.locator('#agendaList [data-event-id="viejo-futuro"]')).to_have_count(0)
                assert not errors, errors
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print('OK: agenda, local midnight CL/VE, multi-day, inclusive90, reader preferences, safe text, errors, refresh, 375/1440')


if __name__ == '__main__':
    main()
