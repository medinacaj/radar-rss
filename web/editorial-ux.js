"use strict";
/* Reuse the feed, briefing and reader; keep editorial evidence attributable. */
(() => {
  const model = window.RadarEditorial;
  if (!model) return;
  const labels = {news:'Noticia', opinion:'Opinión', analysis:'Análisis', press_release:'Comunicado', unknown:'Sin clasificar'};
  let selectedType = 'all', currentDigest = [], speaking = false;
  const select = mk('select'); select.id = 'editorialType';
  select.setAttribute('aria-label','Tipo editorial');
  select.title = 'Tipo indicado por el editor. Sin clasificar significa que el RSS no lo especifica.';
  select.append(new Option('Todos los tipos','all'));
  Object.entries(labels).forEach(([value,label]) => select.append(new Option(label,value)));
  const field = mk('label','editorial-type-field');
  field.append(mk('span','editorial-type-label','Tipo'),select);
  function placeType() {
    const target = window.innerWidth <= 640 ? $('feedFilterFields') : $('feedHeaderControls');
    if (target && field.parentNode !== target) target.append(field);
  }
  function clearType() { selectedType = 'all'; select.value = 'all'; }
  select.addEventListener('change', () => { selectedType = select.value; state.page = 1; render(); });
  $('feedClearFilters')?.addEventListener('click', clearType, true);
  document.addEventListener('click',event => {
    if (event.target.closest('.feed-empty-action')?.textContent === 'Limpiar filtros') clearType();
  },true);
  window.addEventListener('resize', placeType); placeType();

  function allowedStories(items,mode = 'all') {
    const muted = state.mutedKeywords.split(',').map(word => word.trim()).filter(word => word.length > 1);
    // Guardadas deliberately remains readable after a source is hidden.
    return model.filterSources(items,mode === 'saved' ? [] : state.hiddenSources,state.sources,muted);
  }
  const eligibleBase = dashboardEligible;
  dashboardEligible = function(...args) {
    return allowedStories(eligibleBase(...args)).filter(item =>
      (!state.hideRead || !state.read.has(item.id)) && (!window.RadarV12 || window.RadarV12.dashboardMatch(item)));
  };
  const filtersBase = applyFilters;
  applyFilters = function(mode = state.mode,...args) {
    let items = allowedStories(filtersBase(mode,...args),mode);
    const scope = window.RadarLibrary?.getFeedFilters()?.folder;
    const group = scope && window.RadarLibrary?.getSourceGroups().find(group => group.key === (scope.kind === 'manual' ? 'manual:' : 'default:') + scope.id);
    if (group) items = items.filter(item => (item.source_ids || []).some(id => group.ids.includes(id)));
    if (state.feed) items = items.filter(item => (item.source_ids || []).includes(state.feed));
    return model.groupStories(selectedType === 'all' ? items : items.filter(item => model.contentType(item) === selectedType));
  };
  // Marking a grouped card means marking every attributable visible member.
  // Core functions still own persistence, revisions, one redraw and batch Undo.
  function expandMembers(items) {
    const mode = state.pageView === 'feed' && state.mode === 'saved' ? 'saved' : 'all';
    const input = mode === 'saved' ? [...state.items,...(window.RadarLibrary?.getSavedStories() || [])] : state.items;
    const groups = model.groupStories(allowedStories(input,mode));
    const byId = new Map();
    for (const group of groups) for (const id of [group.id,...(group.editorial_member_ids || []),...(group.also_in || []).map(variant => variant.id)]) {
      if (id) byId.set(id,group);
    }
    const ids = new Set();
    for (const item of items) {
      if (!item?.id) continue;
      const group = byId.get(item.id);
      ids.add(item.id);
      for (const id of group?.editorial_member_ids || []) if (id) ids.add(id);
      for (const variant of group?.also_in || []) if (variant.id) ids.add(variant.id);
      if (group?.id) ids.add(group.id);
    }
    return [...ids].map(id => ({id}));
  }
  const markReadBase = markRead;
  markRead = function(id,value,options={}) { return markReadBase(id,value,expandMembers([{id}]).map(item => item.id),options); };
  const markArticlesBase = markArticlesRead;
  markArticlesRead = function(items) { return markArticlesBase(expandMembers(items)); };
  const emptyBase = emptyState;
  emptyState = function(...args) {
    const node = emptyBase(...args);
    if (selectedType !== 'all' && state.items.length) {
      const button = mk('button','settings-secondary feed-empty-action','Ver todos los tipos'); button.type = 'button';
      button.addEventListener('click',()=>{clearType(); state.page = 1; render();});
      (node.querySelector('.feed-empty-actions') || node).append(button);
    }
    return node;
  };
  function badge(item) {
    const kind = model.contentType(item), label = labels[kind];
    const node = mk('span','editorial-type-badge' + (kind === 'unknown' ? ' is-unknown' : ''),label);
    node.dataset.contentType = kind;
    node.title = kind === 'unknown' ? 'El editor no incluye un tipo de artículo explícito en el RSS.'
      : 'Tipo de este artículo indicado por el editor: ' + (item.content_type_label || label);
    return node;
  }
  const cardBase = card;
  card = function(item,...args) {
    const node = cardBase(item,...args);
    node.dataset.contentType = model.contentType(item);
    if (node.dataset.contentType !== 'unknown') node.querySelector('.article-kicker')?.append(badge(item));
    return node;
  };
  const readerBase = openArticleReader;
  openArticleReader = function(item,event,...args) {
    const result = readerBase(item,event,...args);
    if ($('articleReaderDialog')?.open && activeReaderItem === item) {
      $('readerMeta')?.querySelector('.editorial-type-badge')?.remove();
      $('readerMeta')?.append(badge(item));
    }
    return result;
  };
  function eligible() {
    // These are the existing source, keyword, age and Mi Radar preferences.
    const items = dashboardEligible().filter(item => !state.hideRead || !state.read.has(item.id));
    return items;
  }
  function briefingPool() {
    const allowed = window.RadarV12?.briefingCategories() || state.categories;
    return eligible().filter(item => (item.categories || []).some(category => allowed.includes(category)));
  }
  function openSequence(items,item,event,target) {
    if (window.RadarReaderExperience?.openSequence) return window.RadarReaderExperience.openSequence(items,item,event,target);
    return openArticleReader(item,event,target);
  }
  function metadata(item) {
    const meta = mk('div','briefing-meta');
    meta.append(mk('span','',sourceLabel(item.publisher || item.source)), document.createTextNode(' · '),
      timeNode(item.published_at || item.first_seen_at),document.createTextNode(' · '));
    const count = coverageOf(item);
    if (count > 1) {
      const compare = mk('button','briefing-coverage',count + ' medios'); compare.type = 'button';
      compare.setAttribute('aria-label',`Cubierta por ${count} medios. Comparar titulares`);
      compare.addEventListener('click',()=>openSequence(currentDigest.slice(),item,null,'compare')); meta.append(compare);
    } else meta.append(mk('span','','1 medio'));
    meta.append(badge(item));
    return meta;
  }
  function digestRow(item) {
    const row = mk('li','briefing-item' + (state.read.has(item.id) ? ' read-article' : ''));
    row.dataset.articleId = item.id;
    const category = mk('span','editorial-story-category',categoryLabel((item.categories || [])[0] || ''));
    const title = link(item.url,item.title || 'Sin título','briefing-title');
    title.addEventListener('click',event=>visitArticle(item,event));
    title.addEventListener('auxclick',event=>{if(event.button===1)visitArticle(item,event);});
    const meta=metadata(item);
    if(state.read.has(item.id))meta.append(mk('span','experience-read-state','Leída'));
    row.append(category,title,meta);
    const summary = String(item.summary || '').trim();
    if (state.showSummaries && summary && summary !== String(item.title || '').trim()) {
      row.append(mk('p','briefing-summary',summary.length > 220 ? summary.slice(0,217) + '…' : summary));
    }
    return row;
  }
  function digestText() {
    const date = new Intl.DateTimeFormat('es-CL',{day:'numeric',month:'long'}).format(new Date());
    const lines = ['Radar RSS · Resumen del ' + date,''];
    currentDigest.forEach((item,index) => {
      lines.push(`${index + 1}. ${item.title} — ${sourceLabel(item.publisher || item.source)} · ${shortDate(item.published_at || item.first_seen_at)} · ${coverageOf(item)} ${coverageOf(item) === 1 ? 'medio' : 'medios'}`);
      if (safeURL(item.url)) lines.push(safeURL(item.url));
      lines.push('');
    });
    lines.push('Resumen completo: ' + location.origin + location.pathname + '#resumen');
    return lines.join('\n');
  }
  function stopSpeaking() {
    speaking = false;
    try { window.speechSynthesis?.cancel(); } catch { /* optional browser feature */ }
    if ($('briefingListen')) $('briefingListen').hidden = !('speechSynthesis' in window);
    if ($('briefingStop')) $('briefingStop').hidden = true;
  }
  // Existing handlers close over the old per-category selection. Capture these
  // actions so the spoken, copied and shared versions match the visible digest.
  $('briefingCopy')?.addEventListener('click',async event => {
    event.stopImmediatePropagation();
    try { await navigator.clipboard.writeText(digestText()); actionToast('Resumen copiado.'); }
    catch { window.prompt('Copia el resumen:',digestText()); }
  },true);
  $('briefingListen')?.addEventListener('click',event => {
    event.stopImmediatePropagation();
    if (!('speechSynthesis' in window) || !currentDigest.length) return;
    stopSpeaking();
    const utterance = new SpeechSynthesisUtterance(digestText()); utterance.lang = 'es-CL';
    utterance.onend = stopSpeaking; utterance.onerror = stopSpeaking;
    speaking = true; $('briefingListen').hidden = true; $('briefingStop').hidden = false;
    $('briefingStop').focus(); window.speechSynthesis.speak(utterance);
  },true);
  $('briefingStop')?.addEventListener('click',event => {
    event.stopImmediatePropagation(); stopSpeaking(); $('briefingListen').focus();
  },true);
  window.addEventListener('hashchange',stopSpeaking);
  window.addEventListener('pagehide',stopSpeaking);
  $('v12BriefingScope')?.addEventListener('change',stopSpeaking,true);
  window.renderBriefing = function() {
    $('briefingDate').textContent = new Intl.DateTimeFormat('es-CL',{weekday:'long',day:'numeric',month:'long'}).format(new Date()).toUpperCase();
    currentDigest = model.selectDigest(briefingPool(),Date.now());
    const expanded = currentDigest.some(item => Date.now() - storyTime(item) > 86400000);
    $('briefingIntro').textContent = `Hasta siete historias de tus secciones, con fuentes y cobertura. ${expanded ? 'Se incluyen las últimas 48 horas por baja actividad reciente.' : 'Últimas 24 horas.'}`;
    const section = mk('section','briefing-section editorial-digest');
    section.setAttribute('aria-label','Selección de historias recientes');
    const list = mk('ol','briefing-list editorial-digest-list'); list.append(...currentDigest.map(digestRow));
    section.append(list);
    $('briefingSections').replaceChildren(currentDigest.length ? section : mk('p','dashboard-empty','No hay historias recientes con tus preferencias actuales.'));
    $('briefingWhatsApp').href = 'https://wa.me/?text=' + encodeURIComponent(digestText());
    $('briefingListen').hidden = !('speechSynthesis' in window) || speaking;
    $('briefingListen').disabled = !currentDigest.length;
    $('briefingStop').hidden = !speaking;
    const note = $('briefingView')?.querySelector('.briefing-note');
    if (note) note.textContent = 'Selección automática por cobertura, actualidad y variedad de secciones. Los titulares y extractos pertenecen a cada medio; Radar no los reescribe.';
  };

  const localSection = mk('section','dashboard-panel editorial-local'); localSection.id = 'editorialLocal';
  localSection.setAttribute('aria-labelledby','editorialLocalTitle'); localSection.hidden = true;
  const head = mk('div','dashboard-panel-head'), heading = mk('h2','','Cerca de ti'); heading.id = 'editorialLocalTitle';
  head.append(heading); localSection.append(head,mk('p','editorial-local-intro','Chile, Concepción y Monagas según tus intereses.'));
  const localList = mk('div','editorial-local-list'); localSection.append(localList);
  $('homeLatest')?.after(localSection);
  function localInterests(items) {
    const pins = window.RadarExperience?.getPinnedDestinations() || [];
    const categories = pins.filter(value => /^0[478]\s*-/.test(value));
    const folderPins = pins.filter(value => value.startsWith('carpeta/')).map(value => 'manual:' + value.slice(8));
    const groups = window.RadarLibrary?.getSourceGroups() || [];
    const sources = new Set(groups.filter(group => folderPins.includes(group.key)).flatMap(group => group.ids));
    if (!categories.length && !sources.size) return items;
    return items.filter(item => (item.categories || []).some(category => categories.includes(category)) ||
      (item.source_ids || []).some(id => sources.has(id)));
  }
  const dashboardBase = renderDashboard;
  renderDashboard = function(...args) {
    const result = dashboardBase(...args), items = eligible();
    const placed = new Set([...document.querySelectorAll('#dashboardFeature [data-article-id], #dashboardRecent [data-article-id]')].map(node => node.dataset.articleId));
    const remaining = model.groupStories(items).filter(item => !placed.has(item.id) &&
      !(item.also_in || []).some(variant => placed.has(variant.id)));
    const selected = model.selectLocal(localInterests(remaining),undefined,Date.now());
    localSection.hidden = !selected.length;
    localList.replaceChildren(...selected.map(item => {
      const row = headlineRow(item,'dashboard-recent-row editorial-local-row');
      const original = row.querySelector('.dashboard-recent-title');
      if (original) {
        const title = original.cloneNode(true); original.replaceWith(title);
        title.addEventListener('click',event=>openSequence(selected.slice(),item,event));
      }
      row.prepend(mk('span','editorial-story-category',categoryLabel((item.categories || [])[0] || '')));
      return row;
    }));
    return result;
  };
  window.addEventListener('radar-experience-changed',()=>{ if (state.pageView === 'dashboard') renderDashboard(); });
  function updateType() {
    placeType();
    if (selectedType === 'all' || state.pageView !== 'feed') return;
    const region = $('feedActiveFilters'), chips = $('feedFilterChips');
    if (!region || !chips) return;
    const chip = mk('button','feed-filter-chip','Tipo: ' + labels[selectedType] + ' ×'); chip.type = 'button';
    chip.dataset.filter = 'content-type'; chip.setAttribute('aria-label','Quitar filtro: tipo ' + labels[selectedType]);
    chip.addEventListener('click',()=>{clearType(); state.page = 1; render(); (window.innerWidth<=640?$('feedFiltersToggle'):select).focus();});
    chips.append(chip); region.hidden = false;
    if ($('feedClearFilters')) $('feedClearFilters').hidden = false;
    const count = chips.childElementCount;
    if ($('feedFiltersCount')) { $('feedFiltersCount').textContent = String(count); $('feedFiltersCount').hidden = false; }
    $('feedFiltersToggle')?.setAttribute('aria-label',`Filtros · ${count} activos`);
    $('filterSummary').textContent += ' · Tipo: ' + labels[selectedType];
  }
  const renderBase = render;
  render = function(...args) { const result = renderBase(...args); updateType(); return result; };
  if (state.ready) render();
})();
