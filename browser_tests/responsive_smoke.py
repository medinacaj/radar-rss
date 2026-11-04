#!/usr/bin/env python3
"""Browser-level responsive smoke tests with deterministic mock RSS data.

Run: python browser_tests/responsive_smoke.py
Only test code depends on Playwright; production has no new dependencies.
"""
from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
REPORTS = ROOT / "test-results" / "responsive"
WIDTHS = (320, 375, 390, 430, 768, 1024, 1440)
CATEGORIES = (
    "01 - Inteligencia Artificial", "02 - Tecnología", "03 - Internacionales",
    "04 - Chile", "05 - Venezuela", "06 - Latinoamérica", "07 - Concepción",
)
STAMP = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
SOURCES = [
    {"id": f"medio-{i}", "name": f"Medio de referencia {i}", "category": cat,
     "url": "https://example.com/rss", "website": "https://example.com", "is_radar": False}
    for i, cat in enumerate(CATEGORIES)
]
ITEMS = [
    {"id": f"noticia-{i}", "title": (
        "Titular de referencia con palabras extensas para verificar el ajuste "
        f"responsivo de la lectura en pantallas de diferentes dimensiones {i}"
        if i % 4 != 1 else f"Noticia breve número {i}"
    ), "url": f"https://example.com/noticias/{i}",
     "image": "https://example.com/radar-fixture-cover.svg" if i % 3 == 0 else None,
     "summary": ("Resumen amplio " * 25 if i % 5 == 0 else
                 "Resumen corto." if i % 5 == 1 else
                 "" if i % 7 == 2 else
                 "Resumen informativo de ejemplo para comprobar distribución de tarjetas."),
     "published_at": STAMP, "first_seen_at": STAMP,
     "publisher": SOURCES[i % len(SOURCES)]["name"], "source": SOURCES[i % len(SOURCES)]["name"],
     "source_ids": [SOURCES[i % len(SOURCES)]["id"]],
     "categories": [CATEGORIES[i % len(CATEGORIES)]], "coverage": 2, "is_radar": False}
    for i in range(18)
]
ITEMS[0]["also_in"] = [
    {"id":"noticia-0-alternativa","title":"Otro medio publica una versión del mismo anuncio",
     "url":"https://example.com/noticias/comparacion","publisher":"Segundo diario",
     "published_at":STAMP,"category":CATEGORIES[0],"source_id":"medio-1"}
]

RESPONSES = {
    "events.json": {"version": 1, "generated_at": STAMP, "horizon_days": 90, "items": [], "pending": [], "sources": []},
    "sources.json": {"version": 1, "sources": SOURCES, "categories": list(CATEGORIES)},
    "latest.json": {"version": 2, "generated_at": STAMP, "items": ITEMS},
    "status.json": {"version": 1, "checked_at": STAMP, "feeds": [], "errors": 0, "stale": 0},
    "meta.json": {"version": 2, "generated_at": STAMP, "total_articles": len(ITEMS),
                  "latest_count": len(ITEMS), "archive_files": []},
    "trends.json": {"version": 1, "generated_at": STAMP, "window_hours": 24,
                    "baseline_days": 7, "topics": []},
}

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, *args):
        pass

def check_uniform_card_heights(page, label):
    """Cards align within EACH row; a long item must not stretch every row."""
    result = page.evaluate("""() => {
      const grid = document.querySelector('#articleGrid');
      if (!grid || grid.classList.contains('list-view')) return {error:'not in cards view'};
      const cards = [...grid.querySelectorAll(':scope > .article-card')];
      const rows = new Map();
      for(const card of cards){
        const r=card.getBoundingClientRect();
        const y=Math.round(r.top);
        if(!rows.has(y))rows.set(y, []);
        rows.get(y).push(Math.round(r.height*10)/10);
      }
      const covers=cards.map(c=>c.querySelector(':scope > .cover')).filter(Boolean);
      const placeholders=cards.map(c=>c.querySelector(':scope > .article-cover-placeholder')).filter(Boolean);
      return {
        rows:[...rows.values()], gridAutoRows:getComputedStyle(grid).gridAutoRows,
        hasImage:covers.length>0, hasNoImage:cards.some(x=>!x.querySelector('.cover')),
        maxImageHeight:covers.length?Math.max(...covers.map(c=>c.getBoundingClientRect().height)):0,
        maxPlaceholderHeight:placeholders.length?Math.max(...placeholders.map(c=>c.getBoundingClientRect().height)):0
      };
    }""")
    rows=result.get("rows", [])
    if sum(map(len,rows))<6 or not result["hasImage"] or not result["hasNoImage"]:
        raise AssertionError(f"{label}: fixture lacks mixed images: {result}")
    if result["gridAutoRows"] != "auto":
        raise AssertionError(f"{label}: global equal-height grid creates wasted space: {result}")
    for heights in rows:
        if max(heights)-min(heights)>2:
            raise AssertionError(f"{label}: cards in same row differ in height: {result}")
    if result["maxImageHeight"]>153 or result["maxPlaceholderHeight"]>153:
        raise AssertionError(f"{label}: image/placeholder unnecessarily tall: {result}")


def check_visible_boxes(page, selectors, label):
    findings = page.evaluate("""selectors => {
      const viewport = window.innerWidth;
      const bad = [];
      for (const selector of selectors) {
        const node = document.querySelector(selector);
        if (!node || node.hidden) continue;
        const style = getComputedStyle(node);
        if (style.display === 'none' || style.visibility !== 'visible') continue;
        const rect = node.getBoundingClientRect();
        if (rect.width < 1 || rect.height < 1) continue;
        if (rect.left < -2 || rect.right > viewport + 2) {
          bad.push({selector, left: +rect.left.toFixed(1), right: +rect.right.toFixed(1), viewport});
        }
      }
      const scrollingWidth = document.documentElement.scrollWidth;
      if (scrollingWidth > viewport + 2) bad.push({scrollingWidth, viewport});
      return bad;
    }""", selectors)
    if findings:
        raise AssertionError(f"{label}: desbordamiento detectado: {findings}")

def check_header_overlap(page, label):
    overlaps = page.evaluate("""() => {
      const selectors = ['#menuToggle', '.topbar-caption', '#searchToggle',
        '.topbar-actions', '.topbar-search'];
      const rects = selectors.map(s => document.querySelector(s)).filter(Boolean)
        .filter(el => getComputedStyle(el).display !== 'none')
        .map(el => ({name: el.id || el.className, r: el.getBoundingClientRect()}))
        .filter(x => x.r.width > 1 && x.r.height > 1);
      const bad = [];
      for (let i = 0; i < rects.length; i++)
        for (let j = i + 1; j < rects.length; j++) {
          const a = rects[i], b = rects[j];
          const x = Math.min(a.r.right,b.r.right) - Math.max(a.r.left,b.r.left);
          const y = Math.min(a.r.bottom,b.r.bottom) - Math.max(a.r.top,b.r.top);
          if (x > 3 && y > 3) bad.push([a.name,b.name]);
        }
      return bad;
    }""")
    if overlaps:
        raise AssertionError(f"{label}: controles superpuestos: {overlaps}")

def check_accessibility_contract(page, label):
    """Deterministic structural and accessible-name guard; not a full WCAG audit."""
    failures = page.evaluate("""() => {
      const issues = [];
      if (document.documentElement.lang !== 'es') issues.push('Falta idioma español');
      const ids = [...document.querySelectorAll('[id]')].map(n => n.id);
      if (ids.length !== new Set(ids).size) issues.push('IDs repetidos');
      const selectors = ['#menuToggle','#searchToggle','#settingsButton','#themeToggle',
        '#refreshNow','#loadMore','#markAllVisible'];
      for (const selector of selectors) {
        const el = document.querySelector(selector);
        if (!el) { issues.push('Control ausente ' + selector); continue; }
        const name = (el.getAttribute('aria-label') || el.getAttribute('title') ||
          el.textContent || '').trim();
        if (!name) issues.push('Control sin nombre ' + selector);
      }
      for (const id of ['dashboardTitle','briefingTitle','feedHeading']) {
        if (document.querySelector('#'+id)?.tagName !== 'H1')
          issues.push('Jerarquía sin H1: '+id);
      }
      return issues;
    }""")
    if failures:
        raise AssertionError(f"{label}: {failures}")


def make_route(route):
    name = Path(urlsplit(route.request.url).path).name
    payload = RESPONSES.get(name)
    if payload is None:
        route.continue_()
    else:
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=json.dumps(payload, ensure_ascii=False))

def ensure_navigation(page):
    if page.locator('#appSidebar').evaluate('(node) => node.inert'):
        page.locator('#menuToggle').click()
    expect(page.locator('#appSidebar')).to_be_visible()
    assert not page.locator('#appSidebar').evaluate('(node) => node.inert')
    # Por defecto visibles; se reabren si otra prueba los contrajo.
    for toggle_id in ('sidebarNavigationToggle', 'sourceFoldersToggle'):
        toggle = page.locator('#' + toggle_id)
        if toggle.get_attribute('aria-expanded') == 'false':
            toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'true')


def check_concepcion_category(page):
    """The seventh folder stays accessible, exclusive and part of Chile/Latam."""
    ensure_navigation(page)
    folder = page.locator("#libraryFolderNav .system-folder-link").filter(has_text="Concepción")
    expect(folder).to_be_visible()
    assert folder.get_attribute("data-topic") == "7"
    folder.focus()
    folder.press("Shift+F10")
    page.locator('#folderMenu [data-folder-action="sources"]').click()
    expect(page.locator("#folderDialog[open]")).to_be_visible()
    assert page.locator("#folderSourceList input[type='checkbox']").count() == len(SOURCES)
    page.locator("#folderDialog .folder-dialog-close").click()
    folder.click()
    expect(page.locator("#feedHeading")).to_have_text("Concepción")
    expect(page.locator("#articleGrid .article-card")).to_have_count(2)
    local_ids = ["noticia-6", "noticia-13"]
    article_ids = lambda: page.locator("#articleGrid > .article-card").evaluate_all(
        "nodes => nodes.map(node => node.dataset.articleId)")
    assert set(article_ids()) == set(local_ids)
    assert page.locator("#sourceSelect option").evaluate_all("nodes => nodes.map(x => x.value)") == ["", "medio-6"]
    page.locator("#articleGrid .article-title a").first.click()
    expect(page.locator("#articleReaderDialog[open]")).to_be_visible()
    expect(page.locator("#readerCategory")).to_have_text("Concepción")
    page.locator("#readerClose").click()
    for slug, expected_ids, expected_sources in (
        ("chile", ["noticia-3", "noticia-6", "noticia-10", "noticia-13", "noticia-17"], ["medio-3", "medio-6"]),
        ("latinoamerica", ["noticia-3", "noticia-4", "noticia-5", "noticia-6", "noticia-10", "noticia-11", "noticia-12", "noticia-13", "noticia-17"], ["medio-3", "medio-4", "medio-5", "medio-6"]),
    ):
        page.evaluate("slug => { location.hash = '#region/' + slug; }", slug)
        expect(page.locator("#articleGrid .article-card")).to_have_count(len(expected_ids))
        assert set(article_ids()) == set(expected_ids)
        assert set(page.locator("#sourceSelect option").evaluate_all("nodes => nodes.map(x => x.value)")) == {"", *expected_sources}
    page.evaluate("location.hash = '#resumen'")
    expect(page.locator("#briefingView")).to_be_visible()
    for scope, labels in (("chile", ["Chile", "Concepción"]),
                          ("latam", ["Chile", "Venezuela", "Latinoamérica", "Concepción"]),
                          ("cat:07 - Concepción", ["Concepción"])):
        page.locator("#v12BriefingScope").select_option(scope)
        assert page.locator(".briefing-section h2").all_text_contents() == labels
        assert set(local_ids).issubset(set(page.locator(".briefing-item").evaluate_all(
            "nodes => nodes.map(node => node.dataset.articleId)")))
    page.locator("#v12BriefingScope").select_option("all")
    page.evaluate("location.hash = '#inicio'")
    expect(page.locator("#dashboardView")).to_be_visible()

def main():
    browser_name = sys.argv[1] if len(sys.argv) > 1 else "chromium"
    if browser_name not in ("chromium", "firefox", "webkit"):
        raise ValueError(f"Unsupported engine: {browser_name}")
    categories_only = "--categories-only" in sys.argv[2:]
    output = REPORTS / browser_name
    output.mkdir(parents=True, exist_ok=True)
    # Run over HTTPS like GitHub Pages; WebKit enforces upgrade-insecure-requests
    # and will otherwise attempt TLS against a plain HTTP test server.
    tls = tempfile.TemporaryDirectory()
    cert_dir = Path(tls.name)
    cert = cert_dir / "cert.pem"
    key = cert_dir / "key.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-days", "1",
        "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost",
    ], check=True, capture_output=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_context.load_cert_chain(certfile=str(cert), keyfile=str(key))
    server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"https://127.0.0.1:{server.server_port}/"
    try:
        with sync_playwright() as p:
            engine = getattr(p, browser_name)
            options = {"headless": True, "args": ["--no-sandbox"] if browser_name == "chromium" else []}
            if browser_name == "chromium" and os.environ.get("RADAR_CHROMIUM_EXECUTABLE"):
                options["executable_path"] = os.environ["RADAR_CHROMIUM_EXECUTABLE"]
            browser = engine.launch(**options)
            try:
                for width in ((375, 1440) if categories_only else WIDTHS):
                    mobile = width <= 768
                    context = browser.new_context(
                        viewport={"width": width, "height": 812 if mobile else 900},
                        is_mobile=mobile and browser_name != "firefox",
                        has_touch=mobile, device_scale_factor=1,
                        service_workers="block", ignore_https_errors=True,
                    )
                    page = context.new_page()
                    javascript_errors = []
                    page.on("pageerror", lambda error: javascript_errors.append(str(error)))
                    page.on("console", lambda msg: javascript_errors.append("console: " + msg.text) if msg.type == "error" else None)
                    context.route("**/*", lambda route: route.continue_()
                                  if urlsplit(route.request.url).hostname == "127.0.0.1"
                                  else route.abort())
                    page.route("**/data/**", make_route)
                    page.route("https://example.com/radar-fixture-cover.svg",
                               lambda route: route.fulfill(
                                   status=200, content_type="image/svg+xml",
                                   body='<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><rect width="400" height="200" fill="#cccccc"/></svg>'))
                    try:
                        page.goto(base + "#inicio", wait_until="load")
                        page.locator("#dashboardView:not([hidden])").wait_for(timeout=15000)
                        page.locator("#dashboardRecent .dashboard-recent-row").first.wait_for(timeout=15000)
                        # El radar tiene su propia ficha, separada del listado "Lo más cubierto".
                        radar_card=page.locator("#coverageTools .radar-standalone-card")
                        covered_card=page.locator("#coverageTools .covered-standalone-card")
                        expect(radar_card).to_be_visible()
                        expect(covered_card).to_be_visible()
                        expect(radar_card.locator("#radarStage svg")).to_have_count(1)
                        expect(radar_card.locator("#radarStage svg")).to_be_visible()
                        expect(radar_card.locator("#radarFigure")).to_be_visible()
                        expect(radar_card.locator("#radarCaption")).to_be_visible()
                        assert page.locator("#radarMapToggle, #radarMapDetails").count() == 0
                        assert radar_card.evaluate("(node)=>node.closest('#newsroomColumns') === null")
                        assert radar_card.evaluate("(node)=>node.closest('#dashboardView') !== null")
                        expect(covered_card.locator("#coveredList")).to_be_visible()
                        assert radar_card.locator("#coveredList").count()==0
                        separate=page.evaluate("""() => {
                          const a=document.querySelector('#coverageTools .radar-standalone-card');
                          const b=document.querySelector('#coverageTools .covered-standalone-card');
                          const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
                          return {distinct:a!==b,fill:getComputedStyle(a).backgroundColor,
                            border:getComputedStyle(a).borderTopWidth,
                            overlap:Math.min(ar.right,br.right)>Math.max(ar.left,br.left)
                                 &&Math.min(ar.bottom,br.bottom)>Math.max(ar.top,br.top)};
                        }""")
                        assert separate["distinct"] and not separate["overlap"],separate
                        assert separate["border"]!="0px",separate
                        if categories_only:
                            check_concepcion_category(page)
                            assert not javascript_errors, javascript_errors
                            print(f"OK [{browser_name}]: {width}px, Concepción administrable, lectura, filtros Chile/Latam y resúmenes", flush=True)
                            continue
                        # Dimension replaces the former visual references with one theme.
                        visual=page.evaluate("""() => ({
                          bg:getComputedStyle(document.body).getPropertyValue('--bg').trim(),
                          radius:getComputedStyle(document.querySelector('#dashboardFeature .article-card')).borderTopLeftRadius,
                          shadow:getComputedStyle(document.querySelector('#dashboardFeature .article-card')).boxShadow
                        })""")
                        assert visual['radius']=='24px' and visual['shadow']!='none',visual
                        light_background=visual['bg']
                        assert page.locator('#dashboardTitle').inner_text() == 'Inicio'
                        expect(page.locator('#dashboardFeature')).to_be_visible()
                        expect(page.locator('#dashboardFeature > .article-card')).to_have_count(1)
                        page.evaluate("document.body.classList.remove('light')")
                        assert page.evaluate("getComputedStyle(document.body).getPropertyValue('--bg').trim()") != light_background
                        page.evaluate("document.body.classList.add('light')")
                        # En móvil la barra está fuera de pantalla hasta abrir el cajón.
                        if page.locator('#appSidebar').evaluate('(node) => node.inert'):
                            page.locator('#menuToggle').click()
                        expect(page.locator('#appSidebar')).to_be_visible()
                        # Ambas listas son visibles al iniciar, se cierran por separado
                        # y vuelven a abrirse para continuar las pruebas de navegación.
                        for control_id, content_id in (('sidebarNavigationToggle','sidebarCoreContent'),
                                                       ('sourceFoldersToggle','libraryFolderNav')):
                            toggle=page.locator('#'+control_id)
                            content=page.locator('#'+content_id)
                            expect(toggle).to_have_attribute('aria-expanded','true')
                            expect(content).to_be_visible()
                            toggle.click()
                            expect(toggle).to_have_attribute('aria-expanded','false')
                            expect(content).to_be_hidden()
                            toggle.click()
                            expect(toggle).to_have_attribute('aria-expanded','true')
                            expect(content).to_be_visible()
                        # Fondo de lectura y barra lateral claramente diferenciados.
                        colors=page.evaluate("""() => ({
                           background:getComputedStyle(document.body).getPropertyValue('--bg').trim(),
                           sidebar:getComputedStyle(document.querySelector('#appSidebar')).backgroundColor,
                           page:getComputedStyle(document.querySelector('.page')).backgroundColor
                        })""")
                        assert colors['sidebar'] != colors['page'], colors
                        # Identidad cromática solo en los iconos, sin pastillas decorativas.
                        icon_colors=page.locator('#libraryFolderNav .system-folder-link .nav-glyph').evaluate_all('nodes=>nodes.map(n=>getComputedStyle(n).color)')
                        assert len(icon_colors) == len(CATEGORIES) and len(set(icon_colors)) == len(CATEGORIES),icon_colors
                        # Las seis carpetas originales y Concepción siguen accesibles y administrables.
                        assert page.locator("#libraryFolderNav .system-folder-link").count() == len(CATEGORIES)
                        assert page.locator("#libraryFolderNav .v12-hidden-category").count() == 0
                        assert page.locator("#libraryFolderNav .v12-region-nav").count() == 0
                        actual = page.locator("#libraryFolderNav .system-folder-link .nav-label").all_text_contents()
                        assert actual == ["Inteligencia Artificial","Tecnología","Internacionales","Chile","Venezuela","Latinoamérica","Concepción"], actual
                        ensure_navigation(page)
                        folder = page.locator("#libraryFolderNav .system-folder-link").nth(6)
                        expect(folder).to_be_visible()
                        folder.focus()
                        folder.press("Shift+F10")
                        expect(page.locator("#folderMenu")).to_be_visible()
                        page.locator('#folderMenu [role="menuitem"]', has_text="Administrar fuentes").click()
                        expect(page.locator("#folderDialog[open]")).to_be_visible()
                        assert page.locator("#folderSourceList input[type='checkbox']").count() == len(SOURCES)
                        page.locator("#folderDialog .folder-dialog-close").click()
                        expect(page.locator("#folderDialog")).to_be_hidden()
                        # «Todas las noticias» tiene el mismo acceso contextual que
                        # las carpetas, pero nunca ofrece renombrar ni eliminarlas.
                        all_link=page.locator("#categoryNav > .nav-link").nth(1)
                        all_link.focus()
                        all_link.press("Shift+F10")
                        expect(page.locator("#folderMenu")).to_be_visible()
                        expect(page.locator('#folderMenu [data-folder-action="read"]')).to_have_text("Marcar todas como leídas")
                        assert page.locator('#folderMenu [data-folder-action="rename"]:visible').count() == 0
                        assert page.locator('#folderMenu [data-folder-action="delete"]:visible').count() == 0
                        assert page.locator('#folderMenu [data-folder-action="sources"]:visible').count() == 1
                        assert page.locator('#folderMenu [data-folder-action="unread"]:visible').count() == 1
                        page.locator('#folderMenu [data-folder-action="sources"]').click()
                        expect(page.locator("#settingsDialog[open]")).to_be_visible()
                        expect(page.locator('[data-settings-pane="sources"]')).to_be_visible()
                        page.locator('[data-settings-tab="appearance"]').click()
                        expect(page.locator("#settingsDesignAdvanced")).not_to_have_attribute("open", "")
                        expect(page.locator("#settingFont")).to_be_visible()
                        expect(page.locator("#settingSidebarWidth")).to_be_hidden()
                        page.locator("#settingsDesignAdvanced summary").click()
                        expect(page.locator("#settingSidebarWidth")).to_be_visible()
                        page.locator("#settingsDesignAdvanced summary").click()

                        page.locator("#closeSettings").click()
                        expect(page.locator("#settingsDialog")).to_be_hidden()
                        if width <= 950:
                            page.keyboard.press("Escape")
                            page.locator("body:not(.nav-open)").wait_for(timeout=3000)
                        # La guía ya no ocupa la portada: sus 3 acciones viven
                        # exclusivamente en Configuración > Lectura y filtros.
                        assert page.locator("#dashboardView #v13Guide").count() == 0
                        assert page.locator("#v13OpenGuide").count() == 0
                        assert page.locator("#articleGrid .article-card").count() == 0
                        page.locator("#settingsButton").click()
                        page.locator('[data-settings-tab="reading"]').click()
                        expect(page.locator('[data-settings-pane="reading"]')).to_be_visible()
                        assert page.locator("#v13Guide .settings-reading-action").count() == 3
                        expect(page.locator("#v13Guide")).to_be_visible()
                        page.locator(".settings-reading-action").first.click()
                        expect(page.locator("#v12MineToggle")).to_be_focused()
                        page.locator("#closeSettings").click()
                        expect(page.locator("#settingsDialog")).to_be_hidden()
                        check_visible_boxes(page, [".topbar", ".topbar-caption", ".topbar-actions",
                            "#dashboardView", ".homepage-latest .dashboard-panel-head", "#dashboardFeature",
                            "#dashboardRecent .dashboard-recent-row"], f"portada {width}px")
                        # Inicio and Agenda have one purpose each, with no repeated news IDs.
                        expect(page.locator('#dashboardFeature')).to_be_visible()
                        expect(page.locator('#newsroomColumns,#dashboardFolders')).to_have_count(0)
                        expect(page.locator('#agendaSection')).to_be_hidden()
                        visible_ids=page.locator('#dashboardFeature > [data-article-id], #dashboardRecent > [data-article-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)')
                        assert len(visible_ids)>=4 and len(visible_ids)==len(set(visible_ids)),visible_ids
                        page.evaluate("goTo('agenda')")
                        expect(page.locator('#agendaSection')).to_be_visible()
                        expect(page.locator('#dashboardView')).to_be_hidden()
                        expect(page.locator('#agendaStatus')).to_contain_text('No hay actividades confirmadas')
                        page.evaluate("goTo('home')")
                        expect(page.locator('#dashboardView')).to_be_visible()
                        check_header_overlap(page, f"{browser_name} barra superior {width}px")
                        check_accessibility_contract(page, f"{browser_name} portada {width}px")
                        if width in (320, 768, 1440):
                            page.screenshot(path=str(output / f"portada-{width}.png"), full_page=False)

                        # Evitar el CTA duplicado de Inicio, sin retirar acciones
                        # distintas como las guardadas de Noticias o la navegación responsive.
                        assert page.locator("#dashboardView .dashboard-feature-panel .dashboard-read-all").count() == 0
                        assert page.locator("#dashboardSavedAll").count() == 0
                        ensure_navigation(page)
                        all_news=page.locator("#categoryNav > .nav-link").nth(1)
                        expect(all_news).to_be_visible()
                        all_news.click()
                        page.locator("#feedView:not([hidden])").wait_for(timeout=10000)
                        page.locator("#articleGrid .article-card").first.wait_for(timeout=10000)
                        # Los contadores usan la selección y filtros, no un número fijo.
                        assert page.locator("#sourceSelect option").evaluate_all(
                            "(opts) => opts.length > 1 && opts.slice(1).every(o => /\\(\\d+\\)$/.test(o.textContent.trim()))"
                        )

                        # Auto follows the actual content width, including the sidebar.
                        columns_state=page.evaluate("""() => ({
                          value:document.body.dataset.columns,
                          label:document.getElementById('columnsCurrent').textContent.trim(),
                          selection:document.querySelector('#columnsMenu [data-columns="auto"]').getAttribute('aria-checked'),
                          visible:getComputedStyle(document.getElementById('articleGrid')).gridTemplateColumns.split(' ').length,
                          card:document.querySelector('#articleGrid > .article-card').getBoundingClientRect().width,
                          width:document.getElementById('articleGrid').clientWidth
                        })""")
                        assert columns_state["value"] == "auto", columns_state
                        assert columns_state["label"] == "Auto", columns_state
                        assert columns_state["selection"] == "true", columns_state
                        assert columns_state['card'] >= min(280,columns_state['width'])-1, (width,columns_state)
                        assert columns_state['visible'] >= 1, (width,columns_state)
                        # Validar imágenes RSS/OG sin alterar la sección de carpetas.
                        expect(page.locator("#articleGrid .article-card .cover img").first).to_have_js_property("naturalWidth", 400)
                        # El recorte debe mostrar la zona superior (rostros),
                        # no el centro de las fotos panorámicas.
                        image_crop=page.locator("#articleGrid .article-card .cover img").first.evaluate(
                            "(img) => ({position:getComputedStyle(img).objectPosition, fit:getComputedStyle(img).objectFit})")
                        assert image_crop["position"].endswith("8%"), image_crop
                        assert image_crop["fit"] == "cover", image_crop
                        assert page.locator("#articleGrid .article-card.no-cover").count() > 0
                        assert page.locator("#articleGrid .article-card.unread-card").count() >= 1
                        assert page.locator("#articleGrid .article-card.no-excerpt").count() >= 1
                        placeholders=page.locator("#articleGrid .article-card.no-cover .article-cover-placeholder")
                        expect(placeholders.first).to_be_visible()
                        image_height=page.locator("#articleGrid .article-card .cover").first.evaluate("(el)=>el.getBoundingClientRect().height")
                        fallback_height=placeholders.first.evaluate("(el)=>el.getBoundingClientRect().height")
                        assert abs(image_height-fallback_height)<=1,(image_height,fallback_height)
                        assert placeholders.first.locator(".article-cover-publisher").inner_text()
                        expect(placeholders.first.locator(".article-cover-note")).to_have_text("Vista previa")
                        assert placeholders.first.locator("img").count() == 0
                        assert page.locator("#articleGrid .article-card.no-excerpt .article-excerpt").count() == 0
                        # El cristal aporta relieve a leídas y pendientes sin cambiar
                        # la geometría de las filas ni inventar fotografías.
                        shadow_unread=page.locator("#articleGrid .article-card.unread-card").first.evaluate(
                            "(node) => getComputedStyle(node).boxShadow")
                        assert shadow_unread != "none", shadow_unread
                        check_uniform_card_heights(page, f"tarjetas {browser_name} {width}px")
                        # El tamaño de los titulares se configura sin cambiar los resúmenes.
                        page.locator("#settingsButton").click()
                        size_control=page.locator("#settingCardTitleSize")
                        expect(size_control).to_have_value("16")
                        size_control.fill("14")
                        expect(page.locator("#cardTitleSizeValue")).to_have_text("14 px")
                        page.locator("#settingsDone").click()
                        computed_title_size=page.locator("#articleGrid .article-title").first.evaluate("(el)=>getComputedStyle(el).fontSize")
                        assert 14 <= float(computed_title_size.removesuffix("px")) <= 17.5,computed_title_size
                        page.reload(wait_until="load")
                        page.locator("#settingsButton").click()
                        expect(page.locator("#settingCardTitleSize")).to_have_value("14")
                        page.locator("#settingCardTitleSize").fill("16")
                        page.locator("#settingsDone").click()
                        page.locator("#articleGrid .article-card").first.wait_for()
                        # Preferencia Compacto mantiene miniaturas y títulos acotados.
                        # Compacto debe ocultar los resúmenes; no basta con reducir imágenes.
                        page.evaluate("document.body.classList.add('compact')")
                        assert page.locator("#articleGrid .article-card .cover").first.evaluate(
                            "(node) => node.getBoundingClientRect().height") <= 101
                        assert placeholders.first.evaluate(
                            "(node) => node.getBoundingClientRect().height") <= 101
                        excerpt=page.locator("#articleGrid .article-card:not(.no-excerpt) .article-excerpt").first
                        assert excerpt.count() > 0
                        assert excerpt.evaluate("(node) => getComputedStyle(node).display") == "none"
                        page.evaluate("document.body.classList.remove('compact')")
                        # CSS states are checked directly: the quick column button is
                        # deliberately hidden on some mobile widths.
                        page.evaluate("() => { document.body.dataset.columns = '2'; }")
                        check_uniform_card_heights(page, f"dos columnas {browser_name} {width}px")
                        page.evaluate("() => document.querySelector('#articleGrid').classList.add('list-view')")
                        assert page.locator("#articleGrid.list-view").count() == 1
                        assert page.evaluate("() => getComputedStyle(document.querySelector('#articleGrid')).gridAutoRows") == "auto"
                        page.evaluate("() => { document.querySelector('#articleGrid').classList.remove('list-view'); document.body.dataset.columns = 'auto'; }")
                        check_uniform_card_heights(page, f"tarjetas restauradas {browser_name} {width}px")
                        page.locator("#articleGrid .article-card .article-save").first.click()
                        assert page.evaluate("() => document.activeElement?.classList.contains('article-save')")
                        # Acceso directo a marcar una noticia, sin depender del menú.
                        first_card=page.locator("#articleGrid .article-card").first
                        read_button=first_card.locator(".article-read-toggle")
                        expect(read_button).to_be_visible()
                        expect(read_button).to_have_attribute("title","Marcar como leída")
                        assert read_button.locator("svg").count() == 1
                        assert read_button.locator("span").count() == 0
                        assert read_button.inner_text() == ""
                        initial_unread=int(page.locator("#unreadCount").text_content().replace(".",""))
                        initial_nav=int(page.locator("#categoryNav > .nav-link").nth(1).locator(".nav-count").text_content())
                        read_button.click()
                        expect(page.locator("#unreadCount")).to_have_text(str(initial_unread-1))
                        expect(page.locator("#categoryNav > .nav-link").nth(1).locator(".nav-count")).to_have_text(str(initial_nav-1))
                        expect(page.locator("#articleGrid .article-card").first.locator(".article-read-toggle")).to_have_attribute("aria-pressed","true")
                        expect(page.locator("#articleGrid .article-card").first.locator(".article-read-toggle")).to_have_attribute("title","Marcar como no leída")
                        assert page.locator("#articleGrid .article-card").first.evaluate(
                            "(node) => node.classList.contains('read-article')")
                        shadow_read=page.locator("#articleGrid .article-card").first.evaluate(
                            "(node) => getComputedStyle(node).boxShadow")
                        assert shadow_read != "none", shadow_read
                        expect(page.locator("#filterSummary")).to_contain_text(str(initial_unread-1)+" sin leer")
                        # El menú contextual debe estar disponible desde cualquier parte de la tarjeta.
                        page.locator("#articleGrid .article-card").first.locator(".article-title").click(button="right")
                        expect(page.locator("#cardMenu")).to_be_visible()
                        expect(page.locator("#cardMenuReadLabel")).to_have_text("Marcar como no leída")
                        page.locator("#cardMenu [data-card-action='read']").click()
                        expect(page.locator("#unreadCount")).to_have_text(str(initial_unread))
                        expect(page.locator("#categoryNav > .nav-link").nth(1).locator(".nav-count")).to_have_text(str(initial_nav))
                        expect(page.locator("#articleGrid .article-card").first.locator(".article-read-toggle")).to_have_attribute("aria-pressed","false")
                        first_title=page.locator("#articleGrid .article-card").first.locator(".article-title a")
                        first_title.focus()
                        first_title.press("Shift+F10")
                        expect(page.locator("#cardMenu")).to_be_visible()
                        page.keyboard.press("Escape")
                        expect(page.locator("#cardMenu")).to_be_hidden()
                        if width >= 1024:
                            first_card=page.locator("#articleGrid .article-card").first
                            first_card.hover()
                            page.wait_for_timeout(240)
                            shadow=first_card.evaluate("(node) => getComputedStyle(node).boxShadow")
                            assert shadow != "none", (width,browser_name,shadow)
                        check_visible_boxes(page, [".topbar", ".topbar-actions", ".filter-bar",
                            ".filter-controls", ".mode-tabs", "#articleGrid",
                            "#articleGrid .article-card"], f"listado {width}px")
                        ensure_navigation(page)
                        page.keyboard.press("Escape")
                        if width <= 950:
                            page.locator("body:not(.nav-open)").wait_for(timeout=2000)
                        if width <= 710:
                            page.locator("#searchToggle").click()
                            page.locator("#topbarSearch").wait_for(state="visible", timeout=2000)
                            check_visible_boxes(page, ["#topbarSearch", "#searchInput"],
                                                f"búsqueda {width}px")
                            page.locator("#searchToggle").click()

                        page.locator("#settingsButton").click()
                        page.locator("#settingsDialog[open]").wait_for(timeout=3000)
                        check_visible_boxes(page, ["#settingsDialog", ".settings-top",
                            ".settings-body", ".settings-footer"], f"configuración {width}px")
                        page.locator("#closeSettings").click()

                        page.evaluate("location.hash = '#resumen'")
                        page.locator("#briefingView:not([hidden])").wait_for(timeout=10000)
                        assert page.locator("#articleGrid .article-card").count() == 0
                        check_visible_boxes(page, [".briefing-head", ".briefing-actions",
                            ".briefing-sections"], f"resumen {width}px")
                        # RadarRRS V1.2: navegación regional, favoritos y resúmenes personalizables.
                        assert page.locator("#v12BriefingScope").count() == 1
                        page.locator("#v12BriefingScope").select_option("chile")
                        assert page.locator(".briefing-section").count() >= 1
                        assert page.locator(".briefing-section h2").all_text_contents() == ["Chile", "Concepción"]
                        page.locator("#v12BriefingScope").select_option("cat:02 - Tecnología")
                        assert page.locator(".briefing-section").count() == 1
                        assert "Tecnología" in page.locator(".briefing-section h2").first.inner_text()
                        page.locator("#v12BriefingScope").select_option("all")
                        page.evaluate("location.hash = '#inicio'")
                        page.locator("#dashboardView:not([hidden])").wait_for()
                        # No duplicar categorías en Inicio: ajustes opcionales y plegados.
                        assert page.locator("#dashboardView #v12MyRadar").count() == 0
                        assert page.locator('#v12MyRadar').count() == 1
                        page.locator("#settingsButton").click()
                        page.locator('[data-settings-tab="reading"]').click()
                        expect(page.locator("#v12MyRadar")).to_be_visible()
                        assert page.locator("#v12MineDetails").get_attribute("open") is None
                        page.locator("#v12MineToggle").click()
                        assert page.locator("#v12MineToggle").get_attribute("aria-pressed") == "true"
                        page.locator("#v12MineDetails summary").click()
                        expect(page.locator("#v12MineCategories button").first).to_be_visible()
                        page.locator("#v12MineCategories button").first.click()
                        assert page.locator("#v12MineCategories button").first.get_attribute("aria-pressed") == "false"
                        page.locator("#v12MineToggle").click()
                        page.locator("#closeSettings").click()
                        page.evaluate("location.hash = '#region/latinoamerica'")
                        page.locator("#feedView:not([hidden])").wait_for()
                        assert page.locator("#feedHeading").inner_text() == "Latinoamérica"
                        # Acciones secundarias plegadas sin perder los controles existentes.
                        expect(page.locator("#v12Date")).to_be_hidden()
                        page.locator('#settingsButton').click()
                        page.locator('[data-settings-tab="reading"]').click()
                        expect(page.locator('#v12Date')).to_be_visible()
                        check_visible_boxes(page, ['#v12Date','#v12SaveSearch','#markAllVisible'],
                                            f'configuración de noticias {browser_name} {width}px')
                        # Sin fila auxiliar flotante bajo las pestañas.
                        assert page.locator("#v12FilterBar").count() == 0
                        assert page.locator(".feed-actions").count() == 0
                        assert page.locator("#filterSummary.sr-only").count() == 1
                        assert page.locator("#v12Date").get_attribute("title") == "Filtrar por antigüedad"
                        assert page.locator("#v12SaveSearch").get_attribute("aria-label") == "Guardar búsqueda con los filtros actuales"
                        assert page.locator("#markAllVisible").get_attribute("aria-label") == "Marcar las noticias visibles como leídas"
                        assert page.locator("#v12SaveSearch svg").count() == 1
                        assert page.locator("#markAllVisible svg").count() == 1
                        assert page.locator("#v12SaveSearch").inner_text() == ""
                        assert page.locator("#markAllVisible").inner_text() == ""
                        page.locator("#closeSettings").click()
                        filter_boxes = [page.locator(selector).bounding_box() for selector in
                                        ("#feedView .filter-bar", "#feedFilterPanel", "#feedActiveFilters")
                                        if page.locator(selector).is_visible()]
                        filter_bottom = max(box['y']+box['height'] for box in filter_boxes)
                        news=page.locator("#articleGrid").bounding_box()
                        assert 0 <= news["y"]-filter_bottom < 45, (width,browser_name,news["y"]-filter_bottom)
                        # El filtro geográfico duplicaba las seis carpetas.
                        assert page.locator("#v12Geo").count() == 0
                        assert page.locator("#v12CountryTabs").count() == 0
                        assert page.locator('#libraryFolderNav .system-folder-link').count() == len(CATEGORIES)
                        # URLs existentes permanecen válidas aunque el selector se retire.
                        page.evaluate("location.hash = '#region/chile'")
                        expect(page.locator("#feedHeading")).to_have_text("Chile",timeout=10000)
                        page.evaluate("location.hash = '#categoria/04%20-%20Chile'")
                        expect(page.locator("#feedHeading")).to_have_text("Chile",timeout=10000)
                        assert page.locator("#articleGrid .article-card").count() > 0
                        page.locator('#settingsButton').click()
                        page.locator('[data-settings-tab="reading"]').click()
                        page.locator("#v12Date").select_option("7")
                        page.locator('#closeSettings').click()
                        if not page.locator('#sourceSelect').is_visible():page.locator('#feedFiltersToggle').click()
                        page.locator("#sourceSelect").select_option("medio-3")
                        page.locator('#settingsButton').click()
                        page.locator('[data-settings-tab="reading"]').click()
                        page.locator("#v12SaveSearch").click()
                        page.locator('#closeSettings').click()
                        assert page.locator(".v12-saved-open").count() == 1
                        page.locator("#sourceSelect").select_option("")
                        page.locator(".v12-saved-open").first.click()
                        assert page.locator("#v12Date").input_value() == "7"
                        expect(page.locator("#sourceSelect")).to_have_value("medio-3")
                        page.locator(".v12-search-remove").first.click()
                        assert page.locator(".v12-saved-open").count() == 0
                        # Búsquedas antiguas con «geo: chile» deben poderse abrir
                        # desde la carpeta nativa sin recrear el selector.
                        page.evaluate("""() => localStorage.setItem(
                            'radar-v12-saved-searches',
                            JSON.stringify([{label:'Chile anterior',query:'',geo:'chile',
                                age:7,category:'all',feed:'medio-3'},
                                {label:'Latinoamérica anterior',query:'',
                                geo:'latam',age:7,category:'all',feed:''}])
                        )""")
                        page.reload(wait_until="domcontentloaded")
                        page.locator(".v12-saved-open").first.wait_for(timeout=12000)
                        page.locator(".v12-saved-open").first.click()
                        page.wait_for_url("**/#region/chile")
                        expect(page.locator("#feedHeading")).to_have_text("Chile")
                        expect(page.locator("#sourceSelect")).to_have_value("medio-3")
                        # Restaurar el ámbito Chile conserva disponible Concepción,
                        # incluso cuando la búsqueda elige una fuente específica.
                        assert page.locator('#sourceSelect option[value="medio-6"]').count() == 1
                        page.locator(".v12-saved-open").nth(1).click()
                        page.wait_for_url("**/#region/latinoamerica")
                        expect(page.locator("#feedHeading")).to_have_text("Latinoamérica")
                        assert page.locator("#v12Geo").count() == 0
                        page.locator(".v12-search-remove").first.click()
                        page.locator(".v12-search-remove").first.click()
                        assert page.locator(".v12-saved-open").count() == 0
                        page.evaluate("location.hash = '#noticias'")
                        page.locator('#articleGrid [data-article-id="noticia-0"] .article-title a').first.click()
                        page.locator("#articleReaderDialog[open]").wait_for()
                        page.locator("#v12CompareSort").select_option("time")
                        assert page.locator(".v12-timeline-item").count() == 2
                        page.locator("#v12CompareSort").select_option("publisher")
                        assert page.locator(".v12-timeline-item").count() == 0
                        page.locator("#readerClose").click()
                        page.locator("#articleReaderDialog[open]").wait_for(state="hidden")
                        # Una acción de lectura global confirma antes de modificar
                        # el estado y actualiza los contadores de todas las carpetas.
                        ensure_navigation(page)
                        all_link=page.locator("#categoryNav > .nav-link").nth(1)
                        all_link.focus()
                        all_link.press("Shift+F10")
                        page.once("dialog",lambda dialog: dialog.accept())
                        page.locator('#folderMenu [data-folder-action="read"]').click()
                        expect(page.locator("#unreadCount")).to_have_text("0")
                        expect(page.locator("#folderMenu")).to_be_hidden()
                        assert page.locator("#libraryFolderNav .system-folder-link").count() == len(CATEGORIES)
                        print(f"OK [{browser_name}]: {width}px, portada, listado, navegación, búsqueda, configuración, resumen", flush=True)
                    except Exception:
                        print(f"DEBUG [{browser_name}] {width}px: JS={javascript_errors}", flush=True)
                        print("DEBUG document:", page.evaluate("() => ({hash: location.hash, ready: document.readyState, dashboardHidden: document.querySelector('#dashboardView')?.hidden, bodyClass: document.body.className, cardCount: document.querySelectorAll('#dashboardFeature .article-card').length})"), flush=True)
                        page.screenshot(path=str(output / f"fallo-{width}.png"), full_page=False)
                        raise
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        tls.cleanup()

if __name__ == "__main__":
    main()
