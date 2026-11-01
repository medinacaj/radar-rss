"""Exercise real service-worker updates with local, deterministic failures."""
import json
import re
import socket
import threading
from urllib.parse import urlsplit

from playwright.sync_api import expect
import responsive_smoke as fixtures


def check_failed_upgrade(browser, tls_context):
    source = (fixtures.WEB / 'sw.js').read_text()
    # Observe before the production handler: respondWith stops later listeners.
    # The observer does not replace the production fetch response.
    source = """
    self.addEventListener('fetch', event => {
        if (event.request.mode !== 'navigate') return;
        event.waitUntil(caches.open('upgrade-test-diagnostics').then(cache => cache.put(
            new URL('__navigation', self.registration.scope).href,
            new Response(JSON.stringify({cache:event.request.cache, mode:event.request.mode}))
        )));
    });
    """ + source
    legacy = re.sub(r"const CACHE = '[^']+';", "const CACHE = 'notisonda-v4';", source, count=1)

    for failed_path, failure in (('/app.js', 'http'), ('/data/latest.json', 'network')):
        state = {'upgrade': False, 'failure': failure, 'offline': False, 'offline_attempts': 0}

        class Handler(fixtures.QuietHandler):
            def end_headers(self):
                # Keep this test offline without browser request interception,
                # which changes cache/navigation behavior in Firefox.
                self.send_header('Content-Security-Policy',
                    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                    "font-src 'self'; connect-src 'self'; worker-src 'self'")
                super().end_headers()

            def do_GET(self):
                try:
                    self.respond()
                except (BrokenPipeError, ConnectionResetError):
                    # addAll cancels outstanding requests when one download fails.
                    pass

            def respond(self):
                path = urlsplit(self.path).path
                if state['offline']:
                    state['offline_attempts'] += 1
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                if state['upgrade'] and state['failure'] and path == failed_path:
                    if state['failure'] == 'network':
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                    else:
                        self.send_error(503, 'Upgrade fixture: temporarily unavailable')
                    return
                if path == '/sw.js':
                    body = (source if state['upgrade'] else legacy).encode()
                    content_type = 'text/javascript'
                elif path.startswith('/data/') and path.rsplit('/', 1)[-1] in fixtures.RESPONSES:
                    body = json.dumps(fixtures.RESPONSES[path.rsplit('/', 1)[-1]]).encode()
                    content_type = 'application/json'
                else:
                    return super().do_GET()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)

        server = fixtures.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.socket = tls_context.wrap_socket(server.socket, server_side=True)
        base = f'https://127.0.0.1:{server.server_port}/'
        threading.Thread(target=server.serve_forever, daemon=True).start()
        context = browser.new_context(service_workers='allow', ignore_https_errors=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def update():
            return page.evaluate("""async () => {
                const registration = await navigator.serviceWorker.getRegistration();
                const finished = new Promise(resolve => {
                    registration.addEventListener('updatefound', () => {
                        const worker = registration.installing;
                        worker.addEventListener('statechange', () => {
                            if (['activated','redundant'].includes(worker.state)) resolve(worker.state);
                        });
                    }, {once:true});
                });
                await registration.update();
                return Promise.race([finished, new Promise((_, reject) => {
                    setTimeout(() => reject(new Error('Worker update did not settle')), 15000);
                })]);
            }""")

        def offline_reload():
            registration = page.evaluate("""async () => {
                const r = await navigator.serviceWorker.getRegistration();
                return {active:r?.active?.state, controller:navigator.serviceWorker.controller?.state,
                    cachedHTML:!!(await caches.match(location.origin+'/'))};
            }""")
            assert registration['active'] == 'activated', (failed_path, registration)
            assert registration['controller'] == 'activated', (failed_path, registration)
            assert registration['cachedHTML'], (failed_path, registration)
            # Drop every connection, then open the reader in a new tab and use
            # DOM reload. This checks real navigation without automation reload
            # commands that can ask an engine to bypass its service worker.
            attempts = state['offline_attempts']
            state['offline'] = True
            offline_page = context.new_page()
            try:
                offline_page.goto(base, wait_until='domcontentloaded')
                with offline_page.expect_navigation(wait_until='domcontentloaded'):
                    offline_page.evaluate('location.reload()')
                offline_page.wait_for_function('() => typeof state !== "undefined" && state.ready')
                assert offline_page.evaluate('state.items.length') == len(fixtures.ITEMS), (failed_path, 'offline news lost', registration)
                expect(offline_page.locator('#dashboardTitle')).to_have_text('Inicio')
                assert offline_page.locator('.topbar').evaluate('node => getComputedStyle(node).display') == 'flex'
                navigation = offline_page.evaluate("""async () => {
                    const response = await caches.match(new URL('__navigation', location.href).href);
                    return response ? await response.json() : null;
                }""")
                assert navigation and navigation['mode'] == 'navigate', (failed_path, 'SW navigation was bypassed', navigation)
                assert state['offline_attempts'] > attempts, (failed_path, 'network failure not exercised')
            finally:
                offline_page.close()
                state['offline'] = False

        try:
            page.goto(base)
            page.wait_for_function('() => typeof state !== "undefined" && state.ready')
            page.wait_for_function('() => !!navigator.serviceWorker.controller')
            page.wait_for_function("async () => (await caches.keys()).includes('notisonda-v4')")
            state['upgrade'] = True
            assert update() == 'redundant', (failed_path, 'incomplete worker replaced the working reader')
            assert page.evaluate("async () => (await caches.keys()).includes('notisonda-v4')"), failed_path
            offline_reload()
            state['failure'] = None
            assert update() == 'activated', (failed_path, 'complete upgrade failed')
            page.wait_for_function("async () => !(await caches.keys()).includes('notisonda-v4')")
            offline_reload()
        except Exception as error:
            diagnostics = page.evaluate("""async () => {
                const r = await navigator.serviceWorker.getRegistration();
                const navigation = await caches.match(new URL('__navigation', location.href).href);
                return {active:r?.active?.state, navigation:navigation ? await navigation.text() : null};
            }""")
            raise AssertionError((failed_path, 'upgrade fixture failed', errors, diagnostics)) from error
        finally:
            context.close()
            server.shutdown()
            server.server_close()
