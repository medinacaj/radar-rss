"use strict";
/* Radar RSS — funciones editoriales y de hábito diario.
   Lo más cubierto y su radar, temas en alza, temas que sigo, «mientras no estabas»,
   resumen del día (escuchar y compartir), hilo de una historia, atajos de teclado,
   modo ligero y lectura sin conexión. Todo se calcula en el navegador con los JSON
   públicos; no hay cuentas, rastreo ni servicios externos. Usa las utilidades de app.js. */
(() => {
  const FOLLOW_KEY = 'radar-followed-topics';
  const LAST_VISIT_KEY = 'radar-last-visit';
  const SINCE_DISMISS_KEY = 'radar-since-visit-dismissed';
  const DAY = 86400000;
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
  const store = (key, value) => { try { localStorage.setItem(key, value); return true; } catch { return false; } };
  let trends = null, trendsFor = null;

  /* ---------- Utilidades ---------- */
  const within = (item, ms) => Date.now() - storyTime(item) <= ms && storyTime(item) > 0;
  function hash01(text) {
    let h = 2166136261;
    for (const ch of String(text)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
    return ((h >>> 0) % 10000) / 10000;
  }
  function eligible() { return typeof dashboardEligible === 'function' ? dashboardEligible() : state.items.slice(); }
  function mostCovered(limit, hours = 24) {
    const pool = eligible().filter(item => within(item, hours * 3600000));
    return pool.sort((a, b) => coverageOf(b) - coverageOf(a) || storyTime(b) - storyTime(a)).slice(0, limit);
  }
  function searchFor(term) {
    $('searchInput').value = term; state.search = term; state.page = 1; state.onlyNew = false;
    if (state.pageView === 'feed' && state.category === 'all') render(); else goTo('all');
  }
  function plain(text) { return String(text || '').replace(/\s+/g, ' ').trim(); }

  /* ---------- Modo ligero ---------- */
  function applyLite() { document.body.classList.toggle('lite', state.lite); }
  (function initLite() {
    const stored = storeGet('radar-lite');
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (stored === null && connection && (connection.saveData || ['slow-2g', '2g'].includes(connection.effectiveType))) {
      state.lite = true;
      setTimeout(() => actionToast('Modo ligero activado por tu conexión. Puedes cambiarlo en Configuración.'), 1200);
    }
    applyLite();
    $('settingLite').addEventListener('change', event => {
      state.lite = event.target.checked; savePref('lite', state.lite); applyLite(); render();
    });
    const baseSync = syncSettings;
    syncSettings = function () { baseSync(); $('settingLite').checked = state.lite; };
  })();

  /* ---------- Lo más cubierto + radar ---------- */
  const SVG = 'http://www.w3.org/2000/svg';
  const svgEl = (tag, attrs = {}) => {
    const node = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
    return node;
  };
  const SHORT_LABELS = ['IA', 'Tecnología', 'Mundo', 'Chile', 'Venezuela', 'Latam'];
  let tooltip = null;
  function showTip(dot, item) {
    if (!tooltip) { tooltip = mk('div', 'radar-tooltip'); tooltip.setAttribute('role', 'tooltip'); document.body.append(tooltip); }
    tooltip.replaceChildren(mk('strong', '', plain(item.title)), mk('span', '', `${sourceLabel(item.publisher || item.source)} · ${coverageOf(item)} ${coverageOf(item) === 1 ? 'medio' : 'medios'} · ${ageDate(item.published_at || item.first_seen_at)}`));
    tooltip.hidden = false;
    const r = dot.getBoundingClientRect(), w = tooltip.offsetWidth, h = tooltip.offsetHeight;
    tooltip.style.left = Math.min(window.innerWidth - w - 8, Math.max(8, r.left + r.width / 2 - w / 2)) + 'px';
    tooltip.style.top = (r.top - h - 10 > 8 ? r.top - h - 10 : r.bottom + 10) + 'px';
  }
  function hideTip() { if (tooltip) tooltip.hidden = true; }
  function highlight(id, on) {
    document.querySelectorAll(`[data-radar-id="${CSS.escape(id)}"]`).forEach(node => node.classList.toggle('is-linked', on));
  }
  function drawRadar(stories, ranked) {
    const stage = $('radarStage');
    const R = 150, svg = svgEl('svg', { viewBox: '-170 -170 340 340', class: 'radar-svg', role: 'img' });
    const cats = state.categories.length ? state.categories : [''];
    const slice = (Math.PI * 2) / cats.length;
    const defs = svgEl('defs');
    const grad = svgEl('linearGradient', { id: 'radarSweepGrad', x1: '0', y1: '0', x2: '1', y2: '0' });
    grad.append(svgEl('stop', { offset: '0', 'stop-color': 'var(--accent)', 'stop-opacity': '0' }), svgEl('stop', { offset: '1', 'stop-color': 'var(--accent)', 'stop-opacity': '.28' }));
    defs.append(grad); svg.append(defs);
    svg.append(svgEl('circle', { r: R, class: 'radar-bg' }));
    [0.25, 0.5, 0.75, 1].forEach(f => svg.append(svgEl('circle', { r: R * f, class: 'radar-ring' })));
    const edge = svgEl('text', { x: 0, y: -R - 6, class: 'radar-ring-label', 'text-anchor': 'middle' });
    edge.textContent = 'hace 24 h'; svg.append(edge);
    cats.forEach((cat, i) => {
      const a = -Math.PI / 2 + i * slice;
      svg.append(svgEl('line', { x1: 0, y1: 0, x2: Math.cos(a) * R, y2: Math.sin(a) * R, class: 'radar-spoke' }));
      const mid = a + slice / 2;
      const text = svgEl('text', { x: Math.cos(mid) * (R - 22), y: Math.sin(mid) * (R - 22) + 4, class: 'radar-sector-label', 'text-anchor': 'middle' });
      text.textContent = SHORT_LABELS[i] || categoryLabel(cat).slice(0, 10);
      svg.append(text);
    });
    if (!state.lite && !reduceMotion?.matches) {
      const sweep = svgEl('g', { class: 'radar-sweep' });
      sweep.append(svgEl('path', { d: `M0 0 L${R} 0 A${R} ${R} 0 0 0 ${Math.cos(-0.55) * R} ${Math.sin(-0.55) * R} Z`, fill: 'url(#radarSweepGrad)' }));
      sweep.append(svgEl('line', { x1: 0, y1: 0, x2: R, y2: 0, class: 'radar-sweep-line' }));
      svg.append(sweep);
    }
    const rankOf = new Map(ranked.map((item, i) => [item.id, i + 1]));
    const dots = svgEl('g', { class: 'radar-dots' });
    const ordered = stories.slice().sort((a, b) => coverageOf(a) - coverageOf(b)); // grandes encima
    for (const item of ordered) {
      const cat = (item.categories || [])[0];
      const index = Math.max(0, cats.indexOf(cat));
      const angle = -Math.PI / 2 + index * slice + (0.14 + 0.72 * hash01(item.id)) * slice;
      const age = Math.min(24, Math.max(0, (Date.now() - storyTime(item)) / 3600000));
      const dist = 12 + (age / 24) * (R - 20);
      const coverage = coverageOf(item);
      const size = 2.6 + Math.sqrt(coverage) * 1.9;
      const rank = rankOf.get(item.id);
      const g = svgEl('g', { class: 'radar-dot' + (coverage >= 3 ? ' is-strong' : '') + (rank ? ' is-ranked' : ''), transform: `translate(${(Math.cos(angle) * dist).toFixed(1)} ${(Math.sin(angle) * dist).toFixed(1)})`, 'data-radar-id': item.id });
      g.append(svgEl('circle', { r: Math.max(size, 10), class: 'radar-hit' }), svgEl('circle', { r: (rank ? Math.max(size, 10) : size).toFixed(1), class: 'radar-mark' }));
      if (rank) { const t = svgEl('text', { y: 4, class: 'radar-rank', 'text-anchor': 'middle' }); t.textContent = String(rank); g.append(t); }
      g.addEventListener('pointerenter', () => { showTip(g, item); highlight(item.id, true); });
      g.addEventListener('pointerleave', () => { hideTip(); highlight(item.id, false); });
      g.addEventListener('click', () => { hideTip(); openArticleReader(item); });
      dots.append(g);
    }
    svg.append(dots);
    svg.append(svgEl('circle', { r: 4, class: 'radar-center' }));
    const strong = stories.filter(x => coverageOf(x) >= 3).length;
    svg.setAttribute('aria-label', `Radar de las últimas 24 horas: ${stories.length} historias, ${strong} publicadas por tres o más medios. La lista numerada a continuación contiene las principales.`);
    stage.replaceChildren(svg);
    $('radarCaption').textContent = 'Cada punto es una historia: más cerca del centro, más reciente; más grande, más medios la publicaron.';
  }
  let coveredKey = '';
  function renderCovered() {
    const list = $('coveredList');
    // Evita redibujar (y reiniciar el barrido) si los datos no cambiaron.
    const rankedAll = mostCovered(90);
    const key = [state.generated, rankedAll.map(item=>item.id).join(','), state.lite, document.body.classList.contains('light')].join('|');
    if (key === coveredKey && $('radarStage').firstChild) return;
    coveredKey = key;
    const ranked = rankedAll.slice(0,6);
    const multi = ranked.filter(x => coverageOf(x) > 1);
    const shown = multi.length >= 3 ? multi : ranked;
    list.replaceChildren(...shown.map((item, i) => {
      const li = mk('li', 'covered-item'); li.dataset.radarId = item.id; li.dataset.articleId = item.id;
      const rank = mk('span', 'covered-rank', String(i + 1)); rank.setAttribute('aria-hidden', 'true');
      const body = mk('div', 'covered-body');
      const a = link(item.url, plain(item.title) || 'Sin título', 'covered-title');
      a.addEventListener('click', event => openArticleReader(item, event));
      const meta = mk('div', 'covered-meta');
      const coverage = coverageOf(item);
      const bar = mk('span', 'covered-bar'); bar.style.setProperty('--w', Math.min(100, 12 + coverage * 9) + '%');
      const count = mk('button', 'covered-count', `${coverage} ${coverage === 1 ? 'medio' : 'medios'}`); count.type = 'button';
      count.setAttribute('aria-label', `Cubierta por ${coverage} medios. Comparar titulares`);
      count.addEventListener('click', () => {
        // Pointer or assistive activation does not focus buttons on every platform.
        count.focus({preventScroll:true});
        openArticleReader(item, null, 'compare');
      });
      meta.append(bar, count, mk('span', '', `${categoryLabel((item.categories || [])[0] || '')} · ${ageDate(item.published_at || item.first_seen_at)}`));
      body.append(a, meta); li.append(rank, body);
      li.addEventListener('pointerenter', () => highlight(item.id, true));
      li.addEventListener('pointerleave', () => highlight(item.id, false));
      return li;
    }));
    if (!shown.length) list.replaceChildren(mk('li', 'covered-empty', 'Aún no hay historias en las últimas 24 horas.'));
    const radarStories = rankedAll;
    drawRadar(radarStories, shown);
  }

  /* ---------- Temas en alza y temas que sigo ---------- */
  function followed() {
    try { const v = JSON.parse(storeGet(FOLLOW_KEY) || '[]'); return Array.isArray(v) ? v.filter(x => typeof x === 'string' && x.trim()).slice(0, 12) : []; }
    catch { return []; }
  }
  function setFollowed(list) { store(FOLLOW_KEY, JSON.stringify(list.slice(0, 12))); }
  function isFollowed(term) { const key = stripAccents(term.trim()); return followed().some(x => stripAccents(x) === key); }
  function toggleFollow(term) {
    const clean = term.trim().slice(0, 40);
    if (!clean) return;
    const list = followed(), key = stripAccents(clean);
    const next = list.some(x => stripAccents(x) === key) ? list.filter(x => stripAccents(x) !== key) : [...list, clean];
    if (next.length > 12) { actionToast('Puedes seguir hasta 12 temas.'); return; }
    setFollowed(next);
    actionToast(next.length > list.length ? `Sigues «${clean}». Lo verás en el menú con sus novedades.` : `Dejaste de seguir «${clean}».`);
    render();
  }
  function topicMatches(term) {
    const key = stripAccents(term);
    return state.items.filter(item => stripAccents(`${item.title} ${item.summary || ''}`).includes(key));
  }
  function topicChip(label, count, opts = {}) {
    const chip = mk('button', 'trend-chip' + (opts.isNew ? ' is-new' : '') + (opts.followed ? ' is-followed' : ''));
    chip.type = 'button';
    chip.append(mk('span', 'trend-label', label));
    if (count) chip.append(mk('span', 'trend-count', String(count)));
    if (opts.isNew) chip.append(mk('span', 'trend-flag', 'nuevo'));
    chip.title = opts.title || `Buscar «${label}»`;
    chip.addEventListener('click', () => searchFor(label));
    return chip;
  }
  async function loadTrends() {
    if (trendsFor === state.generated) return;
    trendsFor = state.generated;
    try { trends = await dataFetch('./data/trends.json?v=' + encodeURIComponent(state.generated || '')); }
    catch { trends = null; }
    if (state.pageView === 'dashboard') renderTopics();
  }
  function renderTopics() {
    const panel = $('trendsPanel');
    const topics = Array.isArray(trends?.topics) ? trends.topics : [];
    $('trendChips').replaceChildren(...topics.map(t => topicChip(t.label, t.stories, {
      isNew: t.is_new, title: `«${t.label}»: ${t.stories} historias en 24 h de ${t.sources} fuentes` + (t.is_new ? ' (no aparecía la semana anterior)' : ` (antes ~${t.previous_daily} al día)`),
    })));
    $('trendChips').hidden = !topics.length;
    $('trendsHint').hidden = !topics.length;
    const mine = followed();
    $('followedRow').hidden = !mine.length;
    $('followedChips').replaceChildren(...mine.map(term => {
      const unread = topicMatches(term).filter(x => !state.read.has(x.id)).length;
      return topicChip(term, newsCountText(unread), { followed: true, title: `${newsUnreadText(unread)} sobre «${term}»` });
    }));
    panel.hidden = !topics.length && !mine.length;
  }
  function renderFollowedNav() {
    let section = $('followedNav');
    const mine = followed();
    if (!section) {
      section = mk('section', 'followed-nav'); section.id = 'followedNav';
      section.setAttribute('aria-labelledby', 'followedNavTitle');
      const head = mk('div', 'folder-group-head'); const h = mk('span', '', 'TEMAS QUE SIGO'); h.id = 'followedNavTitle'; head.append(h);
      section.append(head, mk('div', 'followed-nav-list'));
      const folders = document.querySelector('.source-folders-section');
      (folders || $('categoryNav')).after(section);
    }
    section.hidden = !mine.length;
    const list = section.querySelector('.followed-nav-list');
    list.replaceChildren(...mine.map(term => {
      const row = mk('div', 'followed-nav-row');
      const go = mk('button', 'nav-link'); go.type = 'button';
      const active = state.pageView === 'feed' && stripAccents(state.search.trim()) === stripAccents(term);
      go.classList.toggle('active', active); go.setAttribute('aria-current', active ? 'page' : 'false');
      const unread = topicMatches(term).filter(x => !state.read.has(x.id)).length;
      const left = mk('span', 'nav-left'); const icon = mk('span', 'nav-glyph'); icon.append(svgIcon('bell'));
      left.append(icon, mk('span', 'nav-label', term));
      go.append(left, mk('span', 'nav-count', newsCountText(unread)));
      go.title = `${newsUnreadText(unread)} sobre «${term}»`;
      go.addEventListener('click', () => searchFor(term));
      const remove = mk('button', 'followed-remove'); remove.type = 'button';
      remove.setAttribute('aria-label', `Dejar de seguir «${term}»`); remove.title = 'Dejar de seguir';
      remove.append(svgIcon('x'));
      remove.addEventListener('click', () => toggleFollow(term));
      row.append(go, remove); return row;
    }));
  }

  /* ---------- Mientras no estabas ---------- */
  function renderSinceVisit() {
    const box = $('sinceVisit');
    if (!newsCountsComplete()) { box.hidden = true; return; }
    const fresh = state.lastVisit ? eligible().filter(isNewSinceVisit) : [];
    const dismissed = storeGet(SINCE_DISMISS_KEY) === String(state.lastVisit);
    if (fresh.length < 3 || dismissed || Date.now() - state.lastVisit < 20 * 60000) { box.hidden = true; return; }
    const when = new Intl.DateTimeFormat('es-CL', { weekday: 'long', hour: '2-digit', minute: '2-digit' }).format(new Date(state.lastVisit));
    $('sinceVisitText').textContent = `${format.format(fresh.length)} noticias nuevas desde tu visita del ${when}`.replace(/\.?$/, '.');
    const byCat = state.categories.map(cat => [cat, fresh.filter(x => (x.categories || []).includes(cat)).length]).filter(([, n]) => n);
    $('sinceVisitFolders').replaceChildren(...byCat.map(([cat, n]) => {
      const b = mk('button', 'since-visit-folder'); b.type = 'button';
      b.append(mk('span', '', categoryLabel(cat)), mk('strong', '', String(n)));
      b.setAttribute('aria-label', `${n} nuevas en ${categoryLabel(cat)}`);
      b.addEventListener('click', () => { state.onlyNew = true; goTo(cat); });
      return b;
    }));
    box.hidden = false;
  }
  function saveVisit() { store(LAST_VISIT_KEY, String(Date.now())); }
  window.addEventListener('pagehide', saveVisit);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') saveVisit(); });
  $('sinceVisitShow').addEventListener('click', () => { state.onlyNew = true; goTo('all'); });
  $('sinceVisitDismiss').addEventListener('click', () => { store(SINCE_DISMISS_KEY, String(state.lastVisit)); $('sinceVisit').hidden = true; });
  $('onlyNewClear').addEventListener('click', () => { state.onlyNew = false; state.page = 1; render(); });
  $('followTopic').addEventListener('click', () => toggleFollow(state.search));

  const baseFilters = applyFilters;
  applyFilters = function (mode = state.mode) {
    const list = baseFilters(mode);
    return state.onlyNew ? list.filter(isNewSinceVisit) : list;
  };
  function updateFeedContext() {
    const term = state.search.trim();
    $('onlyNewChip').hidden = !state.onlyNew;
    const follow = $('followTopic');
    follow.hidden = term.length < 3;
    if (!follow.hidden) {
      const on = isFollowed(term);
      follow.setAttribute('aria-pressed', String(on));
      follow.classList.toggle('is-on', on);
      $('followTopicLabel').textContent = on ? `Siguiendo «${term}»` : `Seguir «${term}»`;
    }
    $('feedContext').hidden = $('onlyNewChip').hidden && follow.hidden;
  }

  /* ---------- Resumen del día ---------- */
  let speaking = false;
  function briefingData() {
    let hours = 24;
    let pool = eligible().filter(item => within(item, hours * 3600000));
    if (pool.length < 12) { hours = 48; pool = eligible().filter(item => within(item, hours * 3600000)); }
    const sections = state.categories.filter(cat => !window.RadarV12 || window.RadarV12.briefingCategories().includes(cat)).map(cat => ({
      cat, label: categoryLabel(cat),
      // Tema principal de la historia: evita que una nota aparezca en una sección ajena.
      items: pool.filter(x => (x.categories || [])[0] === cat)
        .sort((a, b) => coverageOf(b) - coverageOf(a) || storyTime(b) - storyTime(a)),
    }));
    const used = new Set();
    for (const section of sections) {
      section.items = section.items.filter(x => !used.has(x.id)).slice(0, 3);
      section.items.forEach(x => used.add(x.id));
    }
    return { hours, sections: sections.filter(s => s.items.length) };
  }
  function siteLink() { return location.origin + location.pathname + '#resumen'; }
  function briefingText(data, perSection = 2) {
    const date = new Intl.DateTimeFormat('es-CL', { day: 'numeric', month: 'long' }).format(new Date());
    const lines = [`📡 Radar RSS · Resumen del ${date}`, ''];
    for (const s of data.sections) {
      lines.push(`*${s.label}*`);
      s.items.slice(0, perSection).forEach((x, i) => {
        const c = coverageOf(x);
        lines.push(`${i + 1}. ${plain(x.title)} — ${sourceLabel(x.publisher || x.source)}${c > 1 ? ` (${c} medios)` : ''}`);
        if (safeURL(x.url)) lines.push(safeURL(x.url));
      });
      lines.push('');
    }
    lines.push(`Resumen completo: ${siteLink()}`);
    return lines.join('\n');
  }
  window.renderBriefing = function renderBriefing() {
    const data = briefingData();
    $('briefingDate').textContent = new Intl.DateTimeFormat('es-CL', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date()).toUpperCase();
    $('briefingIntro').textContent = data.hours === 24
      ? 'Las historias que más medios publicaron en las últimas 24 horas, por tema.'
      : 'Hubo poca actividad en las últimas 24 horas: se incluyen las de las últimas 48 horas.';
    const wrap = $('briefingSections');
    wrap.replaceChildren(...data.sections.map((s, si) => {
      const sec = mk('section', 'briefing-section');
      const head = mk('div', 'briefing-section-head');
      const icon = mk('span', 'briefing-section-icon'); icon.append(svgIcon(CATEGORY_ICONS[state.categories.indexOf(s.cat)] || 'grid'));
      const h = mk('h2', '', s.label); h.id = 'briefingSec' + si;
      const more = mk('button', 'briefing-more', 'Ver todo'); more.type = 'button';
      more.setAttribute('aria-label', 'Ver todas las noticias de ' + s.label);
      more.addEventListener('click', () => goTo(s.cat));
      head.append(icon, h, more); sec.setAttribute('aria-labelledby', h.id);
      const ol = mk('ol', 'briefing-list');
      s.items.forEach(item => {
        const li = mk('li', 'briefing-item' + (state.read.has(item.id) ? ' read-article' : '')); li.dataset.articleId = item.id;
        const a = link(item.url, plain(item.title) || 'Sin título', 'briefing-title');
        a.addEventListener('click', event => openArticleReader(item, event));
        const meta = mk('div', 'briefing-meta');
        const kind = kindBadge(item); if (kind) meta.append(kind);
        meta.append(mk('span', '', sourceLabel(item.publisher || item.source)), document.createTextNode(' · '), timeNode(item.published_at || item.first_seen_at));
        const c = coverageOf(item);
        if (c > 1) {
          const cb = mk('button', 'briefing-coverage', `${c} medios`); cb.type = 'button';
          cb.setAttribute('aria-label', `Cubierta por ${c} medios. Comparar titulares`);
          cb.addEventListener('click', () => openArticleReader(item, null, 'compare'));
          meta.append(document.createTextNode(' · '), cb);
        }
        li.append(a, meta);
        const summary = plain(item.summary);
        if (summary) li.append(mk('p', 'briefing-summary', summary.length > 220 ? summary.slice(0, 217) + '…' : summary));
        ol.append(li);
      });
      sec.append(head, ol); return sec;
    }));
    if (!data.sections.length) wrap.replaceChildren(mk('p', 'dashboard-empty', 'Todavía no hay suficientes noticias recientes para el resumen.'));
    $('briefingWhatsApp').href = 'https://wa.me/?text=' + encodeURIComponent(briefingText(data));
    $('briefingListen').hidden = !('speechSynthesis' in window) || speaking;
    $('briefingStop').hidden = !speaking;
  };
  function stopSpeech() {
    speaking = false;
    try { window.speechSynthesis?.cancel(); } catch { /* sin síntesis */ }
    $('briefingListen').hidden = !('speechSynthesis' in window); $('briefingStop').hidden = true;
  }
  $('briefingListen').addEventListener('click', () => {
    if (!('speechSynthesis' in window)) return;
    const data = briefingData();
    const voices = speechSynthesis.getVoices();
    const voice = voices.find(v => /^es[-_](CL|419|US|MX)/i.test(v.lang)) || voices.find(v => /^es/i.test(v.lang)) || null;
    const parts = ['Resumen del día de Radar RSS.'];
    for (const s of data.sections) {
      parts.push(`${s.label}.`);
      s.items.forEach((x, i) => parts.push(`${['Primero', 'Segundo', 'Tercero'][i] || ''}: ${plain(x.title)}. Fuente: ${sourceLabel(x.publisher || x.source)}.`));
    }
    speechSynthesis.cancel();
    parts.forEach((text, i) => {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = voice?.lang || 'es-CL'; if (voice) u.voice = voice; u.rate = 1.02;
      if (i === parts.length - 1) u.onend = stopSpeech;
      speechSynthesis.speak(u);
    });
    speaking = true; $('briefingListen').hidden = true; $('briefingStop').hidden = false; $('briefingStop').focus();
  });
  $('briefingStop').addEventListener('click', () => { stopSpeech(); $('briefingListen').focus(); });
  $('briefingCopy').addEventListener('click', async () => {
    const text = briefingText(briefingData(), 3);
    try { await navigator.clipboard.writeText(text); actionToast('Resumen copiado. Pégalo donde quieras compartirlo.'); }
    catch { window.prompt('Copia el resumen:', text); }
  });

  // Acceso «Resumen del día» en el menú lateral (fuera de #categoryNav: library.js cuenta sus botones).
  const briefingLink = mk('button', 'nav-link briefing-nav-link'); briefingLink.type = 'button';
  (() => {
    const left = mk('span', 'nav-left'), icon = mk('span', 'nav-glyph'); icon.append(svgIcon('radar'));
    left.append(icon, mk('span', 'nav-label', 'Resumen del día'));
    briefingLink.append(left, mk('span', 'nav-count', ''));
    briefingLink.addEventListener('click', () => goTo('briefing'));
    $('categoryNav').after(briefingLink);
  })();

  /* ---------- Hilo de una historia ---------- */
  const THREAD_STOP = new Set('a al con de del el en es la las lo los para por que se su un una y o sobre tras ante como mas más the of to and in on for'.split(' '));
  const tokens = text => new Set(stripAccents(text).split(/[^a-z0-9ñ]+/).filter(w => w.length > 3 && !THREAD_STOP.has(w)));
  function relatedStories(item) {
    const base = tokens(item.title); if (base.size < 3) return [];
    const exclude = new Set([item.id, ...(item.also_in || []).map(x => x.id)]);
    const t0 = storyTime(item);
    const out = [];
    for (const other of state.items) {
      if (exclude.has(other.id) || Math.abs(storyTime(other) - t0) > 10 * DAY) continue;
      const set = tokens(other.title); let shared = 0;
      for (const w of set) if (base.has(w)) shared++;
      const score = shared / (base.size + set.size - shared);
      if (shared >= 4 && score >= 0.35) out.push({ other, score });
    }
    return out.sort((a, b) => b.score - a.score).slice(0, 6).map(x => x.other).sort((a, b) => storyTime(a) - storyTime(b));
  }
  function threadSection(item) {
    const related = relatedStories(item);
    if (!related.length) return null;
    const all = [...related, item].sort((a, b) => storyTime(a) - storyTime(b));
    const days = new Set(all.map(x => new Date(storyTime(x)).toDateString())).size;
    const sec = mk('section', 'reader-thread'); sec.id = 'readerThread';
    const head = mk('div', 'reader-compare-head');
    head.append(svgIcon('timeline'), mk('h3', '', 'Seguimiento de esta historia'), mk('span', 'reader-compare-count', days > 1 ? `${days} días` : `${all.length} notas`));
    const ol = mk('ol', 'thread-list');
    const fmt = new Intl.DateTimeFormat('es-CL', { weekday: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    for (const x of all) {
      const li = mk('li', 'thread-item' + (x.id === item.id ? ' is-current' : ''));
      const when = mk('time', 'thread-when', fmt.format(new Date(storyTime(x)))); when.dateTime = new Date(storyTime(x)).toISOString();
      const body = mk('div', 'thread-body');
      if (x.id === item.id) body.append(mk('span', 'thread-title', plain(x.title)), mk('span', 'thread-meta', sourceLabel(x.publisher || x.source) + ' · estás leyendo esta'));
      else {
        const b = mk('button', 'thread-title', plain(x.title)); b.type = 'button';
        b.addEventListener('click', () => openArticleReader(x));
        body.append(b, mk('span', 'thread-meta', sourceLabel(x.publisher || x.source)));
      }
      li.append(when, body); ol.append(li);
    }
    sec.append(head, ol);
    return sec;
  }
  const baseOpen = openArticleReader;
  openArticleReader = function (item, event, ...rest) {
    baseOpen(item, event, ...rest);
    if (event && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0)) return;
    const place = () => {
      if (activeReaderItem?.id !== item.id) return;
      $('readerThread')?.remove();
      const sec = threadSection(item);
      if (sec) $('readerSummary').append(sec);
    };
    place();
    if (hasHistory() && !state.historyLoading && !state.historyFailed) void loadHistory().then(place);
  };

  /* ---------- Atajos de teclado ---------- */
  let gPending = 0;
  const typing = el => el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
  function cards() {
    const scope = state.pageView === 'dashboard' ? $('dashboardView') : state.pageView === 'briefing' ? $('briefingView') : $('articleGrid');
    return [...scope.querySelectorAll('.article-card, .briefing-item, .dashboard-recent-row, .dashboard-folder-row')].filter(el => el.offsetParent);
  }
  let kbdId = null;
  function restoreKeyboardCard() {
    // Guardar o marcar vuelve a dibujar el listado: recuperar la noticia activa del teclado.
    if (!kbdId) return;
    const el = cards().find(c => c.dataset.articleId === kbdId);
    if (!el || el.classList.contains('kbd-current')) return;
    el.classList.add('kbd-current');
    if (!document.activeElement || document.activeElement === document.body) el.querySelector('.article-title a, .briefing-title, .dashboard-recent-title')?.focus({ preventScroll: true });
  }
  function focusCard(el) {
    kbdId = el.dataset.articleId || null;
    document.querySelectorAll('.kbd-current').forEach(x => x.classList.remove('kbd-current'));
    el.classList.add('kbd-current');
    el.querySelector('.article-title a, .briefing-title, .dashboard-recent-title')?.focus({ preventScroll: true });
    el.scrollIntoView({ block: 'nearest', behavior: reduceMotion?.matches ? 'auto' : 'smooth' });
  }
  document.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || typing(document.activeElement)) return;
    if (document.querySelector('dialog[open]') || document.body.classList.contains('nav-open')) return;
    const key = event.key;
    if (gPending && Date.now() - gPending < 1200) {
      gPending = 0;
      const target = { i: 'home', r: 'briefing', t: 'all' }[key];
      if (target) { event.preventDefault(); goTo(target); }
      return;
    }
    if (key === 'g') { gPending = Date.now(); return; }
    if (key === '?') { event.preventDefault(); $('shortcutsDialog').showModal(); return; }
    if (!['j', 'k', 'o', 's', 'm'].includes(key)) return;
    const list = cards(); if (!list.length) return;
    const current = document.activeElement?.closest?.('.article-card, .briefing-item, .dashboard-recent-row, .dashboard-folder-row');
    const index = current ? list.indexOf(current) : -1;
    if (key === 'j' || key === 'k') {
      event.preventDefault();
      const next = key === 'j' ? Math.min(list.length - 1, index + 1) : Math.max(0, index < 0 ? 0 : index - 1);
      focusCard(list[next]); return;
    }
    if (!current) return;
    event.preventDefault();
    if (key === 'o') current.querySelector('.article-title a, .briefing-title, .dashboard-recent-title')?.click();
    if (key === 's') {
      const save = current.querySelector('.article-save');
      if (save) save.click(); else actionToast('Abre la noticia para guardarla.');
    }
    if (key === 'm' && current.dataset.articleId) {
      const id = current.dataset.articleId, next = !state.read.has(id);
      markRead(id, next); actionToast(next ? 'Marcada como leída.' : 'Marcada como no leída.');
    }
  });
  $('closeShortcuts').addEventListener('click', () => $('shortcutsDialog').close());
  $('shortcutsDialog').addEventListener('click', e => { if (e.target === $('shortcutsDialog')) $('shortcutsDialog').close(); });

  /* ---------- Integración con el render ---------- */
  const baseNavigate = navigateFromHash;
  navigateFromHash = function () {
    if (window.speechSynthesis && speaking) stopSpeech();
    const hash = decodeRouteHash();
    if (!hash || hash === 'inicio' || hash === 'resumen') state.onlyNew = false;
    baseNavigate();
    briefingLink.classList.toggle('active', state.pageView === 'briefing');
    briefingLink.setAttribute('aria-current', state.pageView === 'briefing' ? 'page' : 'false');
  };
  const baseRender = render;
  render = function () {
    baseRender();
    restoreKeyboardCard();
    updateFeedContext();
    renderFollowedNav();
    if (state.ready && state.pageView === 'dashboard') {
      renderSinceVisit();
      renderCovered(); renderTopics(); void loadTrends();
    }
  };

  window.addEventListener('radar-preferences-imported',()=>{
    state.lite=storeGet('radar-lite')==='true';
    applyLite();syncSettings();render();
  });

  /* ---------- Sin conexión ---------- */
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(location.hostname))) {
    window.addEventListener('load', () => { navigator.serviceWorker.register('./sw.js').catch(error => console.warn('Radar RSS sin conexión no disponible:', error)); });
  }
  window.addEventListener('offline', () => actionToast('Sin conexión: puedes seguir leyendo lo ya cargado y tus guardadas.'));
  window.addEventListener('online', () => actionToast('Conexión recuperada.'));
})();
