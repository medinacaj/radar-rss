"use strict";
// Radar-RSS: interfaz pública sin autenticación y sin HTML sin sanear de fuentes externas.
const $ = (id) => document.getElementById(id);
const format = new Intl.NumberFormat('es-CL');
function storeGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
// El tema sigue al sistema; una elección explícita (claro/oscuro/sistema) siempre prevalece.
// Versiones anteriores guardaban "light" en cada visita aunque nadie lo eligiera,
// por eso solo se respeta lo guardado cuando existe la marca de elección explícita.
const THEME_EXPLICIT_KEY='radar-theme-explicit';
function initialTheme(){
  const saved=storeGet('radar-theme');
  if(storeGet(THEME_EXPLICIT_KEY)==='true'&&['system','light','dark'].includes(saved))return saved;
  return 'system';
}
const state = {
  sources: [], categories: [], items: [], health: [], healthCheckedAt:null, generated: null,
  feedMeta:null,historyLoaded:false,historyLoading:false,historyFailed:false,
  pageView: 'dashboard', category: 'all', feed: '', mode: 'all', layout: storeGet('radar-layout') === 'list' ? 'list' : 'cards',
  theme: initialTheme(),
  search: '', page: 1, ready: false,
  density: storeGet('radar-density') === 'compact' ? 'compact' : 'comfortable',
  columns: ['auto','2','3','4','5','6'].includes(storeGet('radar-columns')) ? storeGet('radar-columns') : 'auto',
  pageSize: [12,24,36,60].includes(Number(storeGet('radar-page-size'))) ? Number(storeGet('radar-page-size')) : 36,
  maxAge: [0,1,7,30,90].includes(Number(storeGet('radar-max-age'))) ? Number(storeGet('radar-max-age')) : 0,
  fontSize: storeGet('radar-font') === 'large' ? 'large' : 'normal',
  cardTitleSize: Number.isInteger(Number(storeGet('radar-card-title-size'))) && Number(storeGet('radar-card-title-size'))>=14 && Number(storeGet('radar-card-title-size'))<=22 ? Number(storeGet('radar-card-title-size')) : 16,
  showImages: storeGet('radar-show-images') !== 'false',
  showSummaries: storeGet('radar-show-summaries') !== 'false',
  hideRead: storeGet('radar-hide-read') === 'true',
  newTab: storeGet('radar-new-tab') !== 'false',
  sort: ['newest','oldest','source'].includes(storeGet('radar-sort')) ? storeGet('radar-sort') : 'newest',
  startMode: ['all','unread','saved'].includes(storeGet('radar-start-mode')) ? storeGet('radar-start-mode') : 'all',
  mutedKeywords: (storeGet('radar-keywords') || '').slice(0,600),
  hiddenSources: safeStoredSet('radar-hidden-sources'),
  saved: safeStoredSet('radar-saved'), read: safeStoredSet('radar-read'),
  lite: storeGet('radar-lite') === 'true',
  lastVisit: Number(storeGet('radar-last-visit')) || 0, onlyNew: false
};

const VECTOR_PATHS={
  'bookmark-filled':'<path d="M6 5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16l-6-4-6 4Z" fill="currentColor"/>',
  folder:'<path d="M3 8V6a2 2 0 0 1 2-2h4l3 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" fill="currentColor" fill-opacity=".2"/><path d="M3 10h18"/>',
  leaf:'<path d="M20 3c-9 0-16 4-16 11a6 6 0 0 0 6 6c7 0 10-8 10-17Z" fill="currentColor" fill-opacity=".2"/><path d="m4 21 10-11m-5 6v-5m0 5h5"/>',
  landmark:'<path d="M3 9 12 4l9 5Z" fill="currentColor" fill-opacity=".3"/><path d="M5 10v8m5-8v8m4-8v8m5-8v8M3 21h18"/>',
  mountain:'<path d="m2 20 7-14 5 9 3-5 5 10Z" fill="currentColor" fill-opacity=".2"/><path d="m6.5 11 2.5 2 2.5-2"/><circle cx="18" cy="5" r="2" fill="currentColor" stroke="none"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="4" fill="currentColor" fill-opacity=".18"/><path d="M8 3v4m8-4v4M3 11h18"/><rect x="8" y="14" width="3" height="3" rx="1" fill="currentColor" stroke="none"/>',
  home:'<path d="M4 10.5 12 4l8 6.5v8A1.5 1.5 0 0 1 18.5 20h-13A1.5 1.5 0 0 1 4 18.5z" fill="currentColor" fill-opacity=".18"/><path d="M9 20v-6h6v6"/>',
  newspaper:'<rect x="3" y="4" width="18" height="16" rx="4" fill="currentColor" fill-opacity=".18"/><path d="M7 8h4v4H7z" fill="currentColor" stroke="none"/><path d="M14 8h3m-3 4h3M7 16h10"/>',
  brain:'<path d="m12 3 2.7 5.8L21 12l-6.3 3.2L12 21l-2.7-5.8L3 12l6.3-3.2Z" fill="currentColor" fill-opacity=".2"/><path d="M19 3v4m-2-2h4"/>',
  cpu:'<rect x="5" y="5" width="14" height="14" rx="4" fill="currentColor" fill-opacity=".2"/><rect x="9" y="9" width="6" height="6" rx="1.5"/><path d="M9 2v3m6-3v3M9 19v3m6-3v3M2 9h3m-3 6h3m14-6h3m-3 6h3"/>',
  globe:'<circle cx="12" cy="12" r="9" fill="currentColor" fill-opacity=".18"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6.5a16 16 0 0 0 14 0M5 17.5a16 16 0 0 1 14 0"/>',
  map:'<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  flag:'<path d="M5 21V4c5-4 9 4 15 0v11c-6 4-10-4-15 0" fill="currentColor" fill-opacity=".2"/><path d="M5 9c5-4 9 4 15 0"/>',
  compass:'<circle cx="12" cy="12" r="9" fill="currentColor" fill-opacity=".18"/><path d="m16 8-2 6-6 2 2-6z" fill="currentColor" fill-opacity=".35"/>',
  rss:'<circle cx="5" cy="19" r="1.5" fill="currentColor" stroke="none"/><path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke-linecap="round"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
  settings:'<path d="M4 7h16M4 17h16"/><rect x="7" y="4" width="4" height="6" rx="2" fill="currentColor"/><rect x="14" y="14" width="4" height="6" rx="2" fill="currentColor"/>',
  sun:'<circle cx="12" cy="12" r="4" fill="currentColor" fill-opacity=".25"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  moon:'<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11Z" fill="currentColor" fill-opacity=".25"/><path d="M18 3v4m-2-2h4"/>',
  external:'<path d="M12 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7M13 3h8v8M10 14 21 3"/>',
  'arrow-right':'<path d="M4 12h16m-7-7 7 7-7 7"/>',
  'arrow-up':'<path d="M12 20V4M5 11l7-7 7 7"/>',
  'arrow-down':'<path d="M12 4v16M5 13l7 7 7-7"/>',
  'chevron-down':'<path d="m6 9 6 6 6-6"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5M5.5 9A7.5 7.5 0 0 1 19 7l1 5M4 12l1 5a7.5 7.5 0 0 0 13.5-2"/>',
  check:'<circle cx="12" cy="12" r="9" fill="currentColor" fill-opacity=".14" stroke="none"/><path d="m7 12 3.5 3.5L17 9"/>',
  bookmark:'<path d="M6 5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16l-6-4-6 4Z" fill="currentColor" fill-opacity=".18"/>',
  share:'<path d="M6 13v6a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-6M12 15V3m-4 4 4-4 4 4"/>',
  undo:'<path d="M3 7v6h6M3 13a9 9 0 1 0 3-7"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  x:'<path d="M18 6 6 18M6 6l12 12"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  menu:'<rect x="3" y="4" width="18" height="16" rx="4" fill="currentColor" fill-opacity=".18"/><path d="M9 4v16m4-11h4m-4 6h4"/>',
  more:'<circle cx="5" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="19" cy="12" r="1.3" fill="currentColor"/>',
  layers:'<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
  trending:'<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  radar:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12 18.4 5.6"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  volume:'<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>',
  pause:'<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
  stop:'<rect x="6" y="6" width="12" height="12" rx="2"/>',
  message:'<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>',
  copy:'<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  bell:'<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
  keyboard:'<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  sparkle:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" fill="currentColor" fill-opacity=".2"/>',
  timeline:'<path d="M12 3v18"/><circle cx="12" cy="7" r="2"/><circle cx="12" cy="17" r="2"/><path d="M14 7h6M4 17h6"/>'
};
const CATEGORY_ICONS=['brain','cpu','globe','mountain','flag','compass','landmark','leaf'];
function svgIcon(name){
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('width','20');svg.setAttribute('height','20');
 svg.setAttribute('stroke','currentColor');svg.setAttribute('fill','none');
 svg.setAttribute('stroke-width','1.8');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');
 svg.setAttribute('aria-hidden','true');svg.classList.add('ui-icon');
 svg.innerHTML=VECTOR_PATHS[name]||VECTOR_PATHS.newspaper;
 return svg;
}
function hydrateIcons(){document.querySelectorAll('[data-icon]').forEach(node=>node.replaceChildren(svgIcon(node.dataset.icon)));}

const CATEGORY_LABELS = ['Inteligencia Artificial', 'Tecnología', 'Internacionales', 'Chile', 'Venezuela', 'Latinoamérica'];

function safeStoredSet(key) {
  try {
    const data = JSON.parse(storeGet(key) || '[]');
    return new Set(Array.isArray(data) ? data.filter(x => typeof x === 'string').slice(key === 'radar-read' ? -5000 : -4000) : []);
  } catch { return new Set(); }
}
function persist(key, values) {
  try { localStorage.setItem(key, JSON.stringify([...values].slice(key === 'radar-read' ? -5000 : -4000))); } catch { /* modo privado o almacenamiento bloqueado */ }
}
function safeURL(raw) {
  try { const u = new URL(raw); return ['https:', 'http:'].includes(u.protocol) ? u.href : null; }
  catch { return null; }
}
function mk(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined && value !== null) node.textContent = value;
  return node;
}
function link(url, label, className = '') {
  const node = mk('a', className, label);
  node.href = safeURL(url) || '#';
  node.target = '_blank';
  node.rel = 'noopener noreferrer external';
  node.referrerPolicy = 'no-referrer';
  return node;
}
function ageDate(input) {
  if (!input) return 'Sin fecha';
  const dt = new Date(input);
  if (Number.isNaN(dt.getTime())) return 'Sin fecha';
  const minutes = Math.max(0, (Date.now() - dt.getTime()) / 60000);
  if (minutes < 1) return 'Ahora';
  if (minutes < 60) return `Hace ${Math.floor(minutes)} min`;
  const hours = minutes / 60;
  if (hours < 24) return `Hace ${Math.floor(hours)} h`;
  if (hours < 48) return 'Ayer';
  const days = hours / 24;
  if (days < 7) return `Hace ${Math.floor(days)} días`;
  return new Intl.DateTimeFormat('es-CL', { day: 'numeric', month: 'short', year: 'numeric' }).format(dt);
}
function timeNode(input, className='') {
  const node = mk('time', className, ageDate(input));
  const dt = new Date(input || '');
  if (!Number.isNaN(dt.getTime())) {
    node.dateTime = dt.toISOString();
    node.title = new Intl.DateTimeFormat('es-CL', { dateStyle: 'full', timeStyle: 'short' }).format(dt);
  }
  return node;
}
function shortDate(input) {
  if (!input) return '—';
  const date = new Date(input);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('es-CL', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date);
}
function stripAccents(s) { return String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
// Los prefijos del OPML (MEDIO, REGIONAL, OFICIAL, SÁTIRA…) organizan las suscripciones.
// En pantalla se muestra el nombre limpio y, cuando informa al lector, un sello aparte.
const SOURCE_PREFIX=/^\s*(MEDIO|REGIONAL|OFICIAL|SÁTIRA|SATIRA|ANÁLISIS|ANALISIS|TENDENCIA|TÉCNICO|TECNICO|VIDEO|IMPACTO|RADAR)\s*[—–-]\s*/i;
const SOURCE_KINDS={OFICIAL:['Oficial','Fuente oficial: comunicado de un organismo público o empresa'],
  'SÁTIRA':['Sátira','Medio humorístico: el contenido no es una noticia real'],SATIRA:['Sátira','Medio humorístico: el contenido no es una noticia real'],
  'ANÁLISIS':['Análisis','Análisis u opinión especializada'],ANALISIS:['Análisis','Análisis u opinión especializada'],
  VIDEO:['Video','Contenido en video']};
function sourceLabel(name, fallback='Fuente RSS') {
  const raw=String(name||'').trim();
  const cleaned=raw.replace(SOURCE_PREFIX,'').trim();
  return cleaned||raw||fallback;
}
function sourceKind(...names){
  for(const name of names){
    const match=String(name||'').match(SOURCE_PREFIX);
    const kind=match&&SOURCE_KINDS[match[1].toUpperCase()];
    if(kind)return {label:kind[0],hint:kind[1],key:kind[0].normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()};
  }
  return null;
}
function kindBadge(item){
  const kind=sourceKind(item.source,item.publisher);
  if(!kind)return null;
  const badge=mk('span','source-kind kind-'+kind.key,kind.label);badge.title=kind.hint;
  return badge;
}
// Cobertura: número de fuentes distintas que publicaron la misma historia.
function coverageOf(item){
  if(Number.isFinite(item?.coverage)&&item.coverage>0)return item.coverage;
  const ids=new Set(item?.source_ids||[]);
  for(const alt of (Array.isArray(item?.also_in)?item.also_in:[]))ids.add(alt.source_id||alt.publisher||alt.url);
  return Math.max(1,ids.size);
}
function storyTime(item){
  const t=new Date(item?.published_at||item?.first_seen_at||0).getTime();
  return Number.isFinite(t)?t:0;
}
// «Mientras no estabas»: noticias que Radar vio por primera vez después de tu última visita.
function isNewSinceVisit(item){
  if(!state.lastVisit)return false;
  const seen=new Date(item?.first_seen_at||0).getTime();
  return Number.isFinite(seen)&&seen>state.lastVisit;
}
function categoryLabel(cat) {
  const idx = state.categories.indexOf(cat);
  return idx >= 0 ? (CATEGORY_LABELS[idx] || cat.replace(/^\d+\s*-\s*/, '')) : String(cat || 'Noticias');
}
const browserTheme = window.matchMedia?.('(prefers-color-scheme: light)');
function setTheme(theme, explicit=false) {
  state.theme = ['light','dark','system'].includes(theme) ? theme : 'system';
  const light=state.theme==='light' || (state.theme==='system' && Boolean(browserTheme?.matches));
  document.body.classList.toggle('light',light);
  $('themeGlyph').replaceChildren(svgIcon(light?'moon':'sun'));
  $('themeToggle').setAttribute('aria-label',light?'Cambiar a modo oscuro':'Cambiar a modo claro');
  $('themeToggle').title=light?'Modo oscuro':'Modo claro';
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',light?'#f3f7f7':'#111e29');
  if(explicit){
    try{localStorage.setItem('radar-theme',state.theme);localStorage.setItem(THEME_EXPLICIT_KEY,'true');}catch{}
  }
}
function setColumns(value){
  state.columns=['auto','2','3','4','5','6'].includes(value)?value:'auto';
  savePref('columns',state.columns);
  applyDisplaySettings();
  $('settingColumns').value=state.columns;
}
function syncColumnsControl(){
  $('columnsCurrent').textContent=state.columns==='auto'?'Auto':state.columns;
  $('columnsToggle').title=state.columns==='auto'?'Tarjetas · columnas automáticas':'Tarjetas · '+state.columns+' columnas';
  $('columnsToggle').setAttribute('aria-label',state.columns==='auto'?'Configurar columnas automáticas':'Configurar '+state.columns+' columnas');
  document.querySelectorAll('#columnsMenu [data-columns]').forEach(option=>{
    const active=option.dataset.columns===state.columns;
    option.setAttribute('aria-checked',String(active));
    option.classList.toggle('selected',active);
  });
}

function closeColumnsMenu(restoreFocus=false){
  const menu=$('columnsMenu');
  if(menu.hidden)return;
  menu.hidden=true;
  $('columnsToggle').setAttribute('aria-expanded','false');
  if(restoreFocus)$('columnsToggle').focus();
}
function openColumnsMenu(focusOption=false){
  const menu=$('columnsMenu');
  menu.hidden=false;
  $('columnsToggle').setAttribute('aria-expanded','true');
  syncColumnsControl();
  if(focusOption){
    (menu.querySelector('[aria-checked="true"]')||menu.querySelector('[data-columns]'))?.focus();
  }
}
function chooseColumns(value){
  if(state.layout!=='cards'){
    state.layout='cards';state.page=1;progressiveLoads=0;
    savePref('layout',state.layout);
  }
  setColumns(value);render();
  closeColumnsMenu(true);
}
function initColumnsMenu(){
  const toggle=$('columnsToggle'),menu=$('columnsMenu');
  const entries=[...menu.querySelectorAll('button[data-columns]')];
  toggle.addEventListener('click',()=>{
    if(menu.hidden)openColumnsMenu(false);else closeColumnsMenu();
  });
  toggle.addEventListener('keydown',event=>{
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();openColumnsMenu(true);
      if(event.key==='ArrowUp')entries[entries.length-1].focus();
    }
  });
  entries.forEach((button,index)=>{
    button.addEventListener('click',()=>chooseColumns(button.dataset.columns));
    button.addEventListener('keydown',event=>{
      if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
        event.preventDefault();
        const next=event.key==='Home'?0:event.key==='End'?entries.length-1:
          (index+(event.key==='ArrowDown'?1:-1)+entries.length)%entries.length;
        entries[next].focus();
      }else if(event.key==='Escape'){
        event.preventDefault();closeColumnsMenu(true);
      }else if(event.key==='Tab')closeColumnsMenu();
    });
  });
  document.addEventListener('pointerdown',event=>{
    if(!event.target.closest('#cardsColumnsControl'))closeColumnsMenu();
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!menu.hidden){event.preventDefault();closeColumnsMenu(true);}
  });
  document.addEventListener('focusin',event=>{
    if(!menu.hidden&&!event.target.closest('#cardsColumnsControl'))closeColumnsMenu();
  });
}
function applyDisplaySettings() {
  document.body.classList.toggle('compact',state.density==='compact');
  document.body.classList.toggle('font-large',state.fontSize==='large');
  document.body.dataset.cardTitleSize=String(state.cardTitleSize);
  document.body.classList.toggle('hide-images',!state.showImages);
  document.body.classList.toggle('hide-summaries',!state.showSummaries);
  document.body.dataset.columns=state.columns;
  document.body.classList.toggle('layout-list',state.layout==='list');
  syncColumnsControl();
}
function downloadText(name,body,mime) {
  const obj=URL.createObjectURL(new Blob([body],{type:mime}));
  const a=document.createElement('a');a.href=obj;a.download=name;document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(obj),2000);
}
function escapeXML(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));}
function savePref(key,value) {try{localStorage.setItem('radar-'+key,String(value));}catch{}}
function selectedTab(name) {
  document.querySelectorAll('[data-settings-tab]').forEach(x=>{
    const active=x.dataset.settingsTab===name;x.classList.toggle('active',active);x.setAttribute('aria-selected',String(active));
  });
  document.querySelectorAll('[data-settings-pane]').forEach(x=>{const active=x.dataset.settingsPane===name;x.classList.toggle('active',active);x.hidden=!active;});
  const scroll=$('settingsPages');
  if(scroll)scroll.scrollTop=0;
  if(name==='health')renderFeedHealth();
  if(name==='data')updateDataCounts();
  if(name==='sources')renderSettingsSources();
}
function updateDataCounts(){
  $('dataSavedCount').textContent=state.saved.size;
  $('dataReadCount').textContent=state.read.size;
  $('dataMutedCount').textContent=state.sources.filter(source=>state.hiddenSources.has(source.id)).length;
}
function renderFeedHealth(){
  const total=state.health.length,ok=state.health.filter(x=>x.state==='ok').length,
    empty=state.health.filter(x=>x.state==='empty').length,
    broken=state.health.filter(x=>x.state==='error').length,
    stale=state.health.filter(x=>x.state==='stale').length;
  $('healthSummary').textContent=total?`${ok} de ${total} fuentes se leyeron bien · ${broken} no disponibles · ${empty} sin noticias · ${stale} sin novedades hace más de un año`+(state.healthCheckedAt?' · Chequeo: '+shortDate(state.healthCheckedAt):''):'';
  const list=$('healthFeedList');list.replaceChildren();
  const issues=state.health.filter(x=>x.state!=='ok');
  if(!issues.length){list.append(mk('p','setting-hint',total?'Sin incidencias detectadas en la última actualización.':'Aún no hay un diagnóstico disponible.'));return;}
  for(const source of issues){
    const row=mk('div','health-row');
    const heading=mk('strong','',sourceLabel(source.name,'Fuente'));
    const meta=mk('small','',feedProblemLabel(source));
    const detail=mk('span','',friendlyFeedProblem(source));
    if(source.error)detail.title='Detalle técnico: '+source.error;
    row.append(heading,meta,detail);
    const catalog=state.sources.find(item=>item.id===source.id),url=RadarSourceTools.feedKey(catalog?.url);
    if(url){const a=link(url,url,'source-rss-url');a.referrerPolicy='no-referrer';row.append(a);}
    list.append(row);
  }
}
function settingsSourceGroups(){
  return window.RadarLibrary?.getSourceGroups?.()||state.categories.map(category=>({key:'default:'+category,name:categoryLabel(category),ids:state.sources.filter(source=>source.category===category).map(source=>source.id)}));
}
function renderCategoryToggles(){
  const area=$('settingsCategories');area.replaceChildren();
  for(const group of settingsSourceGroups()){
    const ids=new Set(group.ids),sources=state.sources.filter(x=>ids.has(x.id));
    const visible=sources.filter(x=>!state.hiddenSources.has(x.id)).length;
    const btn=mk('button','settings-category-toggle',`${group.name} · ${visible}/${sources.length}`);
    btn.type='button';btn.dataset.sourceGroup=group.key;
    btn.setAttribute('aria-label',`${visible===sources.length?'Ocultar':'Mostrar'} las fuentes de ${group.name}`);
    btn.disabled=!sources.length;
    btn.addEventListener('click',()=>{
      const allVisible=sources.every(x=>!state.hiddenSources.has(x.id));
      if(allVisible) sources.forEach(x=>state.hiddenSources.add(x.id));
      else sources.forEach(x=>state.hiddenSources.delete(x.id));
      persist('radar-hidden-sources',state.hiddenSources);
      state.page=1;refreshFeedUI();renderSettingsSources();
      area.querySelector(`[data-source-group="${CSS.escape(group.key)}"]`)?.focus({preventScroll:true});
    });area.append(btn);
  }
}
function refreshFeedUI() {
  if (state.feed && state.hiddenSources.has(state.feed)) state.feed='';
  fillSelect(); buildNav(); render();
}
function syncSettings() {
  $('settingTheme').value=state.theme;
  $('settingLayout').value=state.layout;
  $('settingColumns').value=state.columns;
  $('settingDensity').value=state.density;
  $('settingPageSize').value=String(state.pageSize);
  $('settingAge').value=String(state.maxAge);
  $('settingFont').value=state.fontSize;
  $('settingCardTitleSize').value=String(state.cardTitleSize);
  $('cardTitleSizeValue').textContent=state.cardTitleSize+' px';
  $('settingImages').checked=state.showImages;
  $('settingSummaries').checked=state.showSummaries;
  $('settingSort').value=state.sort;
  $('settingStartMode').value=state.startMode;
  $('settingHideRead').checked=state.hideRead;
  $('settingNewTab').checked=state.newTab;
  $('settingKeywords').value=state.mutedKeywords;
  renderSettingsSources();
  updateDataCounts();
  selectedTab('appearance');
}
function renderSettingsSources() {
  const focusRow=document.activeElement?.closest('#settingsSources [data-source-id]');
  const focusId=focusRow?.dataset.sourceId;
  const focusSelector=document.activeElement?.matches('select')?'.library-source-folder':document.activeElement?.matches('.source-row-actions button')?'.'+document.activeElement.className.split(' ')[0]:'input[type="checkbox"]';
  const groups=settingsSourceGroups(),foldersById=new Map();
  for(const group of groups)for(const id of group.ids){
    if(!foldersById.has(id))foldersById.set(id,[]);
    foldersById.get(id).push(group.name);
  }
  const list=$('settingsSources'); list.replaceChildren();
  const ordered=RadarSourceTools.filterSources(state.sources,{
    query:$('settingsSourceSearch').value,visibility:$('settingsSourceVisibility').value,
    status:$('settingsSourceStatus').value,type:$('settingsSourceType').value,
    hiddenIds:state.hiddenSources,healthById:new Map(state.health.map(row=>[row.id,row])),foldersById
  }).sort((a,b)=>a.name.localeCompare(b.name,'es')||a.id.localeCompare(b.id));
  let displayed=0;
  for (const source of ordered) {
    displayed++;
    const label=mk('label','settings-source-row');
    label.dataset.sourceId=source.id;
    const checkbox=document.createElement('input'); checkbox.type='checkbox'; checkbox.checked=!state.hiddenSources.has(source.id);
    checkbox.setAttribute('aria-label','Mostrar '+source.name);
    const line=mk('span','settings-source-details'); line.append(mk('span','settings-source-name',sourceLabel(source.name)),mk('small','source-original-category',categoryLabel(source.category)));
    label.append(checkbox,line); list.append(label);
    checkbox.addEventListener('change',()=>{
      if (checkbox.checked) state.hiddenSources.delete(source.id); else state.hiddenSources.add(source.id);
      persist('radar-hidden-sources',state.hiddenSources);
      state.page=1; refreshFeedUI();
      renderSettingsSources();
    });
  }
  updateSettingsSourceCount(displayed);
  if(!displayed){const empty=mk('p','setting-hint','No hay fuentes con estos filtros. Prueba otra búsqueda o selecciona Todas las fuentes.');empty.id='sourceSearchEmpty';list.append(empty);}
  renderCategoryToggles();
  if(focusId)queueMicrotask(()=>{
    const row=list.querySelector(`[data-source-id="${CSS.escape(focusId)}"]`);
    (row?.querySelector(focusSelector)||$('settingsSourceSearch')).focus({preventScroll:true});
  });
}
function updateSettingsSourceCount(visibleInSearch) {
  const visible=state.sources.filter(x=>!state.hiddenSources.has(x.id)).length;
  $('settingsSourceCount').textContent=`${visible} visibles de ${state.sources.length} en el catálogo · ${visibleInSearch} resultados`;

}
function initSettingsHandlers(){
  const dialog=$('settingsDialog');
  $('settingsButton').addEventListener('click',()=>{
    syncSettings();dialog.showModal();
    $('settingsPages').scrollTop=0;
  });
  $('closeSettings').addEventListener('click',()=>dialog.close());
  $('settingsDone').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  document.querySelectorAll('[data-settings-tab]').forEach(el=>el.addEventListener('click',()=>selectedTab(el.dataset.settingsTab)));
  $('settingTheme').addEventListener('change',e=>setTheme(e.target.value,true));
  browserTheme?.addEventListener?.('change',()=>{if(state.theme==='system')setTheme('system');});
  $('settingLayout').addEventListener('change',e=>{state.layout=e.target.value;savePref('layout',state.layout);state.page=1;applyDisplaySettings();render();});
  $('settingColumns').addEventListener('change',e=>setColumns(e.target.value));
  $('settingDensity').addEventListener('change',e=>{state.density=e.target.value;savePref('density',state.density);applyDisplaySettings();});
  $('settingFont').addEventListener('change',e=>{state.fontSize=e.target.value;savePref('font',state.fontSize);applyDisplaySettings();});
  $('settingCardTitleSize').addEventListener('input',e=>{
    const size=Number(e.target.value);
    if(!Number.isInteger(size)||size<14||size>22)return;
    state.cardTitleSize=size;
    savePref('card-title-size',size);
    $('cardTitleSizeValue').textContent=size+' px';
    applyDisplaySettings();
  });
  $('settingPageSize').addEventListener('change',e=>{state.pageSize=Number(e.target.value);savePref('page-size',state.pageSize);state.page=1;render();});
  $('settingAge').addEventListener('change',e=>{state.maxAge=Number(e.target.value);savePref('max-age',state.maxAge);state.page=1;render();});
  for(const [id,key,field] of [['settingImages','show-images','showImages'],['settingSummaries','show-summaries','showSummaries']]){
    $(id).addEventListener('change',e=>{state[field]=e.target.checked;savePref(key,state[field]);applyDisplaySettings();});
  }
  $('settingHideRead').addEventListener('change',e=>{state.hideRead=e.target.checked;savePref('hide-read',state.hideRead);state.page=1;render();});
  $('settingNewTab').addEventListener('change',e=>{state.newTab=e.target.checked;savePref('new-tab',state.newTab);render();});
  $('settingSort').addEventListener('change',e=>{state.sort=e.target.value;savePref('sort',state.sort);state.page=1;render();});
  $('settingStartMode').addEventListener('change',e=>{state.startMode=e.target.value;savePref('start-mode',state.startMode);state.mode=state.startMode;state.page=1;render();});
  $('settingKeywords').addEventListener('input',e=>{state.mutedKeywords=e.target.value.slice(0,600);savePref('keywords',state.mutedKeywords);state.page=1;render();});
  $('settingsSourceSearch').addEventListener('input',()=>renderSettingsSources());
  for(const id of ['settingsSourceVisibility','settingsSourceStatus','settingsSourceType'])$(id).addEventListener('change',()=>renderSettingsSources());
  $('showAllSources').addEventListener('click',()=>{state.hiddenSources.clear();persist('radar-hidden-sources',state.hiddenSources);state.page=1;refreshFeedUI();renderSettingsSources();});
  $('exportOPML').addEventListener('click',()=>{
    downloadText('radar-rss-mis-fuentes.opml',RadarSourceTools.buildOPML(settingsSourceGroups(),state.sources,state.hiddenSources),'application/xml;charset=utf-8');
  });
  $('exportSourceCatalog').addEventListener('click',()=>{
    const groups=settingsSourceGroups(),health=new Map(state.health.map(row=>[row.id,row]));
    const rows=state.sources.map(source=>({id:source.id,name:source.name,rss:source.url,website:source.website,
      folders:groups.filter(group=>group.ids.includes(source.id)).map(group=>group.name).join(' | ')||'Sin carpeta',
      visible:!state.hiddenSources.has(source.id),type:RadarSourceTools.sourceKind(source)==='radar'?'RADAR · Google Noticias':'RSS directo',status:RadarSourceTools.healthState(health.get(source.id))}));
    downloadText('radar-rss-catalogo.csv',RadarSourceTools.buildCSV(rows),'text/csv;charset=utf-8');
  });
  $('exportData').addEventListener('click',()=>{
    const data={format:'radar-rss-settings-v2',exported_at:new Date().toISOString(),preferences:{theme:state.theme,layout:state.layout,columns:state.columns,density:state.density,pageSize:state.pageSize,maxAge:state.maxAge,fontSize:state.fontSize,cardTitleSize:state.cardTitleSize,showImages:state.showImages,showSummaries:state.showSummaries,hideRead:state.hideRead,newTab:state.newTab,sort:state.sort,startMode:state.startMode,mutedKeywords:state.mutedKeywords},hiddenSources:[...state.hiddenSources],saved:[...state.saved],read:[...state.read]};
    downloadText('radar-rss-preferencias.json',JSON.stringify(data,null,2),'application/json;charset=utf-8');
    $('dataNotice').textContent='Archivo de respaldo generado.';
  });
  $('importData').addEventListener('change',async e=>{
    const file=e.target.files?.[0];e.target.value='';if(!file)return;
    if(file.size>1_000_000){$('dataNotice').textContent='El archivo supera el límite de 1 MB.';return;}
    try{
      const data=JSON.parse(await file.text());if(data.format!=='radar-rss-settings-v2'||typeof data.preferences!=='object')throw Error('Formato incompatible');
      const p=data.preferences,select=(key,allowed,def)=>allowed.includes(p[key])?p[key]:def;
      state.theme=select('theme',['system','light','dark'],'system');state.layout=select('layout',['cards','list'],'cards');state.columns=select('columns',['auto','2','3','4','5','6'],'auto');state.density=select('density',['comfortable','compact'],'comfortable');
      state.pageSize=select('pageSize',[12,24,36,60],36);state.maxAge=select('maxAge',[0,1,7,30,90],0);state.fontSize=select('fontSize',['normal','large'],'normal');state.cardTitleSize=Number.isInteger(p.cardTitleSize)&&p.cardTitleSize>=14&&p.cardTitleSize<=22?p.cardTitleSize:16;
      for(const field of ['showImages','showSummaries','hideRead','newTab'])if(typeof p[field]==='boolean')state[field]=p[field];
      state.sort=select('sort',['newest','oldest','source'],'newest');state.startMode=select('startMode',['all','unread','saved'],'all');state.mutedKeywords=typeof p.mutedKeywords==='string'?p.mutedKeywords.slice(0,600):'';
      const valid=new Set(state.sources.map(x=>x.id));
      for(const [k,key,onlyValid] of [['hiddenSources','radar-hidden-sources',true],['saved','radar-saved',false],['read','radar-read',false]]){
        state[k]=new Set((Array.isArray(data[k])?data[k]:[]).filter(x=>typeof x==='string'&&x.length<150&&(!onlyValid||valid.has(x))).slice(k==='read'?-20000:-4000));persist(key,state[k]);
      }
      for(const [key,value] of [['layout',state.layout],['columns',state.columns],['theme',state.theme],['density',state.density],['font',state.fontSize],['card-title-size',state.cardTitleSize],['page-size',state.pageSize],['max-age',state.maxAge],['show-images',state.showImages],['show-summaries',state.showSummaries],['hide-read',state.hideRead],['new-tab',state.newTab],['sort',state.sort],['start-mode',state.startMode],['keywords',state.mutedKeywords]])savePref(key,value);
      state.mode=state.startMode;state.page=1;setTheme(state.theme,true);applyDisplaySettings();refreshFeedUI();syncSettings();selectedTab('data');$('dataNotice').textContent='Preferencias y datos importados correctamente.';
    }catch{$('dataNotice').textContent='No se pudo importar. Utiliza un respaldo JSON generado por Radar-RSS.';}
  });
  $('clearRead').addEventListener('click',()=>{if(confirm('¿Borrar el historial de lectura de este navegador?')){state.read.clear();persist('radar-read',state.read);state.page=1;render();updateDataCounts();$('dataNotice').textContent='Historial borrado.';}});
  $('clearSaved').addEventListener('click',()=>{if(confirm('¿Vaciar los artículos guardados en este navegador?')){state.saved.clear();persist('radar-saved',state.saved);state.page=1;render();updateDataCounts();$('dataNotice').textContent='Guardadas vaciadas.';}});
  $('resetSettings').addEventListener('click',()=>{
    if(!confirm('¿Restablecer las preferencias? Tus artículos leídos y guardados no se borrarán.'))return;
    let agendaResetFailed=false;
    try{if(window.RadarAgenda)window.RadarAgenda.restorePreferences({...window.RadarAgenda.exportPreferences(),view:'list'});}catch{agendaResetFailed=true;}
    for(const key of ['layout','columns','theme','density','font','card-title-size','page-size','max-age','show-hero','show-images','show-summaries','hide-read','new-tab','sort','start-mode','keywords','hidden-sources','sidebar-width','theme-explicit','lite']){try{localStorage.removeItem('radar-'+key);}catch{}}
    state.theme=initialTheme();state.layout='cards';state.columns='auto';state.density='comfortable';state.fontSize='normal';state.cardTitleSize=16;state.pageSize=36;state.maxAge=0;
    state.showImages=true;state.showSummaries=true;state.hideRead=false;state.newTab=true;state.sort='newest';state.startMode='all';state.mode='all';state.mutedKeywords='';state.hiddenSources.clear();state.page=1;
    state.lite=false;savePref('lite',false);document.body.classList.remove('lite');
    for(const id of ['settingsSourceVisibility','settingsSourceStatus','settingsSourceType'])$(id).value='all';
    setTheme(state.theme);applyDisplaySettings();$('settingsSourceSearch').value='';refreshFeedUI();syncSettings();selectedTab('data');$('dataNotice').textContent=agendaResetFailed?'Preferencias restablecidas. No se pudo guardar la vista de agenda; tus actividades se conservan.':'Preferencias restablecidas.';
    window.dispatchEvent(new Event('radar-sidebar-pref-sync'));
  });
}
function buildNav() {
  const nav=$('categoryNav');
  nav.replaceChildren();
  const core=[{id:'home',label:'Inicio'},{id:'all',label:'Noticias'},{id:'agenda',label:'Agenda'}];
  const folders=state.categories.map(id=>({id,label:categoryLabel(id)}));
  const sourceFolderNav=document.getElementById('libraryFolderNav');
  if(sourceFolderNav)sourceFolderNav.replaceChildren();
  function addRow(entry,index,parent){
    const active=entry.id==='home'?state.pageView==='dashboard':entry.id==='agenda'?state.pageView==='agenda':
      state.pageView==='feed'&&state.category===entry.id;
    const isFolder=!['home','all','agenda'].includes(entry.id);
    const button=mk('button','nav-link'+(active?' active':'')+(isFolder?' system-folder-link':''));
    button.type='button';button.dataset.destination=entry.id;
    if(isFolder){const topic=state.categories.indexOf(entry.id);if(topic>=0)button.dataset.topic=String(topic+1);}
    button.setAttribute('aria-current',active?'page':'false');
    button.title=entry.label;
    if(isFolder)button.setAttribute('aria-label','Carpeta de fuentes: '+entry.label);
    const symbol=mk('span','nav-glyph');
    symbol.append(svgIcon(entry.id==='home'?'home':entry.id==='all'?'newspaper':entry.id==='agenda'?'calendar':CATEGORY_ICONS[state.categories.indexOf(entry.id)]||'folder'));
    const left=mk('span','nav-left');
    left.append(symbol,mk('span','nav-label',entry.label));
    const sources=entry.id==='all'?state.sources.filter(s=>!state.hiddenSources.has(s.id)):
      state.sources.filter(s=>s.category===entry.id&&!state.hiddenSources.has(s.id));
    button.append(left,mk('span','nav-count',['home','agenda'].includes(entry.id)?'':String(sources.length)));
    button.addEventListener('click',()=>goTo(entry.id));
    parent.append(button);
  }
  core.forEach((entry,index)=>addRow(entry,index,nav));
  if(sourceFolderNav){
    folders.forEach((entry,index)=>addRow(entry,index+2,sourceFolderNav));
  }else if(folders.length){
    // Respaldo visual si el módulo de biblioteca no está disponible.
    const section=mk('section','source-folders-section');
    section.append(mk('div','folder-group-head','CARPETAS DE FUENTES'));
    const list=mk('div','library-system-folders');
    folders.forEach((entry,index)=>addRow(entry,index+2,list));
    section.append(list);nav.append(section);
  }
  renderTopicRail();
}
// Compatibility anchor for progressive modules; navigation lives in the sidebar.
function renderTopicRail(){
 const rail=$('topicRail');
 if(rail){rail.replaceChildren();rail.hidden=true;}
}
const MOBILE_NAV=window.matchMedia('(max-width: 950px)');
const SIDEBAR_COLLAPSED_KEY='radar-sidebar-collapsed';
function setNavOpen(open,restoreFocus=true,persistDesktop=false){
  const sidebar=$('appSidebar'),page=document.querySelector('.page');
  if(!sidebar||!page)return;
  const mobile=MOBILE_NAV.matches,wasOpen=document.body.classList.contains('nav-open');
  if(!mobile&&persistDesktop){
    try{localStorage.setItem(SIDEBAR_COLLAPSED_KEY,String(!open));}catch{}
    document.body.classList.toggle('sidebar-collapsed',!open);
  }else if(!mobile){
    document.body.classList.toggle('sidebar-collapsed',storeGet(SIDEBAR_COLLAPSED_KEY)==='true');
  }
  const visible=mobile?Boolean(open):!document.body.classList.contains('sidebar-collapsed');
  document.body.classList.toggle('nav-open',mobile&&visible);
  $('menuToggle').setAttribute('aria-expanded',String(visible));
  $('menuToggle').setAttribute('aria-label',visible?'Ocultar menú':'Mostrar menú');
  $('sidebarBackdrop').hidden=!(mobile&&visible);
  sidebar.inert=!visible;
  page.inert=mobile&&visible;
  window.dispatchEvent(new Event('radar-sidebar-visibility-change'));
  if(mobile&&visible){sidebar.setAttribute('aria-modal','true');sidebar.setAttribute('role','dialog');}
  else{sidebar.removeAttribute('aria-modal');sidebar.removeAttribute('role');}
  if(mobile&&visible&&!wasOpen){
    (sidebar.querySelector('.sidebar-section-toggle')||$('menuClose'))?.focus({preventScroll:true});
  }else if(!visible&&restoreFocus&&(wasOpen||sidebar.contains(document.activeElement))){
    $('menuToggle').focus({preventScroll:true});
  }
}
function initMobileNav(){
  $('menuToggle').addEventListener('click',()=>{
    const open=MOBILE_NAV.matches?document.body.classList.contains('nav-open'):!document.body.classList.contains('sidebar-collapsed');
    setNavOpen(!open,true,true);
  });
  $('menuClose').addEventListener('click',()=>setNavOpen(false,true,true));
  $('sidebarBackdrop').addEventListener('click',()=>setNavOpen(false));
  document.addEventListener('keydown',event=>{
    if(!MOBILE_NAV.matches||!document.body.classList.contains('nav-open')||document.querySelector('dialog[open]'))return;
    if(event.key==='Escape'){event.preventDefault();setNavOpen(false);return;}
    if(event.key==='Tab'){
      const sidebar=$('appSidebar');
      const focusable=[...sidebar.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex="0"]')]
        .filter(node=>node.getClientRects().length&&!node.closest('[hidden]'));
      const first=focusable[0],last=focusable.at(-1);
      if(!first)return;
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
  const sync=()=>setNavOpen(false,false);
  MOBILE_NAV.addEventListener?.('change',sync);
  window.addEventListener('storage',event=>{if(event.key===SIDEBAR_COLLAPSED_KEY)sync();});
  sync();
}
function goTo(target){
  const hash=target==='home'?'#inicio':target==='all'?'#noticias':target==='briefing'?'#resumen':target==='agenda'?'#agenda':'#categoria/'+encodeURIComponent(target);
  if(window.location.hash===hash)navigateFromHash();
  else window.location.hash=hash;
}
function decodeRouteHash(raw=window.location.hash){
  try{return decodeURIComponent(String(raw).replace(/^#/,''));}catch{return '';}
}
function navigateFromHash(){
  closeColumnsMenu();closeCardMenu();setNavOpen(false,false);
  const hash=decodeRouteHash();
  state.pageView=(!hash||hash==='inicio')?'dashboard':hash==='resumen'?'briefing':hash==='agenda'?'agenda':'feed';
  state.category=hash.startsWith('categoria/')&&state.categories.includes(hash.slice(10))?hash.slice(10):'all';
  state.feed='';
  state.page=1;progressiveLoads=0;
  baseDescription=null;
  updateHeader();buildNav();fillSelect();
  $('dashboardView').hidden=state.pageView!=='dashboard';
  $('feedView').hidden=state.pageView!=='feed';
  $('briefingView').hidden=state.pageView!=='briefing';
  $('agendaView').hidden=state.pageView!=='agenda';
  document.body.classList.toggle('on-dashboard',state.pageView==='dashboard');
  document.body.classList.toggle('on-briefing',state.pageView==='briefing');
  document.body.classList.toggle('on-agenda',state.pageView==='agenda');
  render();
}
function fillSelect() {
  const select = $('sourceSelect'); const old = state.feed; select.replaceChildren();
  const defaultOpt = document.createElement('option'); defaultOpt.value=''; defaultOpt.textContent='Todas las fuentes'; select.append(defaultOpt);
  state.sources.filter(x => !state.hiddenSources.has(x.id) && (state.category === 'all' || x.category === state.category))
    .sort((a,b) => a.name.localeCompare(b.name,'es'))
    .forEach(x => { const option=document.createElement('option'); option.value=x.id; option.textContent=x.name; select.append(option); });
  select.value = old && [...select.options].some(x => x.value === old) ? old : '';
  state.feed = select.value;
}
// Contadores contextuales del selector; excluyen únicamente el propio filtro fuente.
// Se derivan de los artículos ya cargados, sin nuevas consultas a los medios.
function updateSourceCounts(){
  const select=$('sourceSelect');
  if(!select||select.options.length<2)return;
  const selected=state.feed;
  let eligible;
  try{
    state.feed='';
    eligible=applyFilters();
  }finally{
    state.feed=selected;
  }
  const counts=new Map();
  for(const item of eligible){
    for(const id of new Set(Array.isArray(item.source_ids)?item.source_ids:[])){
      counts.set(id,(counts.get(id)||0)+1);
    }
  }
  const sourceNames=new Map(state.sources.map(source=>[source.id,sourceLabel(source.name)]));
  for(const option of [...select.options].slice(1)){
    const amount=counts.get(option.value)||0;
    const amountText=state.mode==='saved'?format.format(amount):newsCountText(amount);
    option.textContent=`${sourceNames.get(option.value)||option.textContent} (${amountText})`;
    option.title=state.mode==='saved'||newsCountsComplete()?`${amountText} noticias con los filtros actuales`
      :newsCountsUnavailable()?'Total no disponible con los filtros actuales':'Calculando noticias con los filtros actuales';
  }
}
function updateHeader() {
  const name = state.category === 'all' ? 'Todas las noticias' : categoryLabel(state.category);
  $('feedHeading').textContent = name;
  $('topbarSection').textContent = state.pageView === 'dashboard' ? 'Inicio' : state.pageView === 'agenda' ? 'Agenda' : state.pageView === 'briefing' ? 'Resumen del día' : name;
  $('sectionEyebrow').textContent = state.category === 'all' ? 'SELECCIÓN EDITORIAL' : 'EXPLORAR CATEGORÍA';
  $('feedDescription').textContent = state.category === 'all' ? 'Titulares y novedades de todas las fuentes.' : `Noticias recientes de ${name}.`;
}
// Mientras hay una búsqueda, la descripción muestra los resultados; al borrarla se
// recupera la descripción de la sección (incluidas las de carpetas personales).
let baseDescription=null;
function describeSearch(query,count){
  const node=$('feedDescription');
  if(query){
    if(baseDescription===null)baseDescription=node.textContent;
    node.textContent=state.mode==='saved'||newsCountsComplete()
      ?`${format.format(count)} ${count===1?'resultado':'resultados'} para «${query}»`
      :`${newsCountsUnavailable()?'Total no disponible':'Buscando en todo el archivo'} para «${query}»`;
  }else if(baseDescription!==null){
    node.textContent=baseDescription;baseDescription=null;
  }
}
// Traducción de errores técnicos del recolector a frases comprensibles.
function friendlyFeedProblem(source){
  const raw=String(source?.error||'');
  if(source?.state==='stale')return 'El medio no publica en su RSS desde hace más de un año.';
  if(source?.state==='empty')return 'El RSS respondió, pero sin noticias.';
  if(/\b(401|403)\b|Forbidden/i.test(raw))return 'El medio no permite la lectura automática de su RSS.';
  if(/\b(404|410)\b|Not Found/i.test(raw))return 'La dirección del RSS ya no existe.';
  if(/\b429\b/.test(raw))return 'El medio limitó las consultas; se reintentará en la próxima revisión.';
  if(/\b5\d\d\b/.test(raw))return 'El sitio del medio tuvo un error temporal.';
  if(/demasiado grande/i.test(raw))return 'El RSS es demasiado pesado para procesarlo.';
  if(/no válido|interpretables|XML/i.test(raw))return 'El RSS tiene un formato que no se pudo leer.';
  if(/Timeout|timed out|Connection|SSL|Name or service|resolve/i.test(raw))return 'El sitio no respondió a tiempo.';
  if(/no público|no autorizado|redirecci/i.test(raw))return 'El RSS redirige a una dirección no permitida.';
  return 'No se pudo leer en la última revisión.';
}
function feedProblemLabel(source){
  return source.state==='stale'?'Sin novedades':source.state==='empty'?'Sin noticias':'No disponible';
}
// Avisos discretos y descartables. La preferencia solo es local a este navegador.
function openFeedHealth() {
  const modal=$('feedHealthDialog');
  const list=$('feedHealthIssues');
  const issues=state.health.filter(x=>x.state!=='ok');
  const ok=state.health.filter(x=>x.state==='ok').length;
  const errors=issues.filter(x=>x.state==='error').length;
  const empty=issues.filter(x=>x.state==='empty').length;
  const stale=issues.filter(x=>x.state==='stale').length;
  $('feedHealthOverview').textContent=state.health.length
    ? `${ok} de ${state.health.length} fuentes se leyeron bien en la última revisión.`+(issues.length?` ${issues.length} no ${issues.length===1?'estuvo disponible':'estuvieron disponibles'}; el resto de las noticias no se ve afectado.`:'')
    : 'Todavía no hay datos de la última revisión.';
  list.replaceChildren();
  if(!issues.length){
    list.append(mk('p','feed-health-empty',state.health.length?'No hay incidencias pendientes.':'El diagnóstico estará disponible después de recopilar los feeds.'));
  }else{
    for(const source of issues){
      const row=mk('article','feed-health-item');
      const head=mk('div','feed-health-item-head');
      head.append(mk('strong','',sourceLabel(source.name)),mk('span','feed-health-status',feedProblemLabel(source)));
      row.append(head,mk('p','feed-health-error',friendlyFeedProblem(source)));
      const extra=[];
      if(source.last_success_at)extra.push('Última lectura correcta: '+shortDate(source.last_success_at));
      if(source.error)extra.push('Detalle técnico: '+source.error);
      if(extra.length)row.append(mk('p','feed-health-tech',extra.join(' · ')));
      const catalog=state.sources.find(item=>item.id===source.id);
      const original=RadarSourceTools.feedKey(catalog?.url||source.url||source.xmlUrl||source.xml_url||'');
      if(original){
        const a=link(original,'Consultar fuente RSS','feed-health-source-link');a.append(svgIcon('external'));
        row.append(a);
      }
      list.append(row);
    }
  }
  if(!modal.open)modal.showModal();
}
function showFeedNotice(message, signature, details) {
  const banner=$('statusBanner');
  $('statusMessage').textContent=message;
  $('statusDetails').hidden=!details;
  banner.dataset.signature=signature;
  banner.hidden=Boolean(signature && storeGet('radar-dismissed-health-notice-v1')===signature);
}
function statusSummary() {
  const banner=$('statusBanner');
  const indicator=$('feedHealthIndicator');
  const section=$('sidebarFeedHealth');
  banner.hidden=true;
  indicator.hidden=true;
  section.hidden=true;
  if (!state.ready) {
    showFeedNotice('No se pudieron cargar las noticias. Revisa tu conexión y vuelve a intentarlo en unos minutos.', 'load-error', false);
    return;
  }
  if (!state.generated && !state.items.length) {
    showFeedNotice('Todavía no hay noticias: la primera recopilación aún no termina.', 'awaiting-first-run', false);
    return;
  }
  // Las fuentes caídas no impiden leer el resto: se informa solo en el menú lateral
  // (y en Configuración), sin avisos sobre las noticias.
  const issues=state.health.filter(x=>x.state==='error'||x.state==='stale');
  if (!issues.length) return;
  $('feedHealthCount').textContent=String(issues.length);
  const label=issues.length===1?'fuente no disponible':'fuentes no disponibles';
  indicator.querySelector('.health-indicator-label').textContent=label;
  indicator.setAttribute('aria-label',`${issues.length} ${label}. Ver detalles`);
  indicator.title='Ver qué fuentes no se pudieron leer en la última revisión';
  indicator.hidden=false;
  section.hidden=false;
}
function applyFilters(mode=state.mode) {
  // (library.js reemplaza esta función; el filtro «solo nuevas» se aplica en features.js)
  const query=stripAccents(state.search.trim());
  const blocked=state.mutedKeywords.split(',').map(w=>stripAccents(w.trim())).filter(w=>w.length>1).slice(0,30);
  const filtered=state.items.filter(item=>{
    if(state.category!=='all'&&!(item.categories||[]).includes(state.category))return false;
    if(!(item.source_ids||[]).some(id=>!state.hiddenSources.has(id)))return false;
    if(state.feed&&!(item.source_ids||[]).includes(state.feed))return false;
    if(state.maxAge){const t=new Date(item.published_at).getTime();if(!Number.isFinite(t)||(Date.now()-t)>state.maxAge*86400000)return false;}
    if(mode==='saved'&&!state.saved.has(item.id))return false;
    if(mode==='unread'&&state.read.has(item.id))return false;
    if(state.hideRead&&mode!=='saved'&&state.read.has(item.id))return false;
    const haystack=stripAccents([item.title,item.summary,item.publisher,item.source].join(' '));
    if(query&&!haystack.includes(query))return false;
    if(blocked.some(x=>haystack.includes(x)))return false;
    return true;
  });
  if(state.sort==='oldest')filtered.sort((a,b)=>new Date(a.published_at||a.first_seen_at)-new Date(b.published_at||b.first_seen_at));
  else if(state.sort==='source')filtered.sort((a,b)=>String(a.publisher||a.source||'').localeCompare(String(b.publisher||b.source||''),'es'));
  return filtered;
}

// La portada utiliza las noticias realmente recopiladas. No inventa puntuaciones
// de popularidad ni presenta la recencia como una clasificación editorial.
function dashboardEligible(){
  const words=state.mutedKeywords.split(',').map(w=>stripAccents(w.trim())).filter(w=>w.length>1).slice(0,30);
  return state.items.filter(item=>{
    if(!(item.source_ids||[]).some(id=>!state.hiddenSources.has(id)))return false;
    if(window.RadarV12 && !window.RadarV12.dashboardMatch(item))return false;
    if(state.maxAge){
      const date=new Date(item.published_at).getTime();
      if(!Number.isFinite(date)||(Date.now()-date)>state.maxAge*86400000)return false;
    }
    const text=stripAccents([item.title,item.summary,item.publisher,item.source].join(' '));
    return !words.some(word=>text.includes(word));
  }).sort((a,b)=>new Date(b.published_at||b.first_seen_at||0)-new Date(a.published_at||a.first_seen_at||0));
}
// Pulso: noticias por hora en las últimas 24 horas (barras mínimas, sin librerías).
function activitySpark(items){
  const now=Date.now(),buckets=new Array(24).fill(0);
  for(const item of items){
    const age=(now-storyTime(item))/3600000;
    if(age>=0&&age<24)buckets[23-Math.floor(age)]++;
  }
  const total=buckets.reduce((a,b)=>a+b,0),max=Math.max(1,...buckets);
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox','0 0 72 20');svg.setAttribute('width','72');svg.setAttribute('height','20');
  svg.setAttribute('class','activity-spark');svg.setAttribute('role','img');
  svg.setAttribute('aria-label',`${total} noticias en las últimas 24 horas`);
  const title=document.createElementNS(ns,'title');title.textContent=`${total} noticias en las últimas 24 horas (una barra por hora)`;svg.append(title);
  buckets.forEach((count,i)=>{
    const h=count?Math.max(2,Math.round(count/max*18)):1;
    const bar=document.createElementNS(ns,'rect');
    bar.setAttribute('x',String(i*3));bar.setAttribute('y',String(20-h));bar.setAttribute('width','2');bar.setAttribute('height',String(h));bar.setAttribute('rx','1');
    if(!count)bar.setAttribute('class','is-empty');
    svg.append(bar);
  });
  return svg;
}
function headlineRow(item,className='dashboard-recent-row'){
  const row=mk('div',className+(state.read.has(item.id)?' read-article':''));
  row.dataset.articleId=item.id;
  const title=link(item.url,item.title||'Sin título','dashboard-recent-title');
  title.addEventListener('click',event=>openArticleReader(item,event));
  const info=mk('span','dashboard-recent-meta');
  const kind=kindBadge(item);if(kind)info.append(kind,document.createTextNode(' '));
  info.append(mk('span','',sourceLabel(item.publisher||item.source)),document.createTextNode(' · '),timeNode(item.published_at));
  const coverage=coverageOf(item);
  if(coverage>1)info.append(document.createTextNode(' · '),mk('span','row-coverage',`${coverage} medios`));
  row.append(title,info);
  return row;
}
// A single selection powers Inicio. No hidden folder/saved feeds are built here.
function homepageHeadline(item){
  const row=headlineRow(item);row.classList.add('dashboard-latest-card');
  const topic=state.categories.indexOf((item.categories||[])[0]);
  if(topic>=0)row.dataset.topic=String(topic+1);
  row.prepend(mk('span','latest-category',categoryLabel((item.categories||[])[0]||'')));
  const summary=String(item.summary||'').replace(/\s+/g,' ').trim();
  if(state.showSummaries&&summary&&summary!==String(item.title||'').trim()){
    row.querySelector('.dashboard-recent-title').after(mk('p','latest-summary',summary.length>150?summary.slice(0,147)+'…':summary));
  }
  return row;
}
function selectInternationalLead(items,now=Date.now()){
  const international=items.filter(item=>(item.categories||[]).some(cat=>cat.startsWith('03 -')));
  const recent=international.filter(item=>{const age=now-storyTime(item);return age>=0&&age<=86400000;});
  if(!recent.length)return international.reduce((best,item)=>!best||storyTime(item)>storyTime(best)?item:best,null);
  // Only the collector's outlet count is a coverage signal; RSS query ids are not.
  const coverage=item=>Number.isInteger(item.coverage)&&item.coverage>0?item.coverage:1;
  return recent.reduce((best,item)=>!best||coverage(item)>coverage(best)||
    coverage(item)===coverage(best)&&storyTime(item)>storyTime(best)?item:best,null);
}
function renderDashboard(){
  const feature=$('dashboardFeature'),recent=$('dashboardRecent');
  if(!feature||!recent)return;
  const items=dashboardEligible(),chosen=[],seenCategories=new Set();
  // Keep an international lead only among sources/categories the reader allows.
  const international=selectInternationalLead(items);
  if(international){chosen.push(international);seenCategories.add((international.categories||[])[0]||'');}
  for(const item of items){
    const category=(item.categories||[])[0]||'';
    if(chosen.some(row=>row.id===item.id)||seenCategories.has(category))continue;
    chosen.push(item);seenCategories.add(category);
    if(chosen.length>=8)break;
  }
  for(const item of items){
    if(chosen.length>=8)break;
    if(!chosen.some(row=>row.id===item.id))chosen.push(item);
  }
  $('homeLatest').hidden=chosen.length<2;
  feature.replaceChildren(chosen.length?card(chosen[0]):mk('p','dashboard-empty','No hay noticias con tus preferencias actuales.'));
  recent.replaceChildren(...chosen.slice(1).map(homepageHeadline));
}

function emptyState(filtered) {
  const isEmpty = !state.items.length;
  if (!isEmpty && state.search.trim() && state.mode!=='saved' && state.historyLoading) {
    const el = mk('div','empty-state');
    const symbol=mk('div','empty-icon');symbol.append(svgIcon('search'));
    el.append(symbol, mk('h3','','Buscando en noticias anteriores…'), mk('p','','Revisamos el archivo completo de los últimos 45 días.'));
    return el;
  }
  if (!isEmpty && state.search.trim() && state.mode!=='saved' && newsCountsUnavailable()) {
    const el = mk('div','empty-state');
    const symbol=mk('div','empty-icon');symbol.append(svgIcon('search'));
    el.append(symbol, mk('h3','','No se pudo completar la búsqueda'),
      mk('p','','No pudimos revisar todo el archivo. Reintenta cargar el historial o pulsa actualizar para completar la búsqueda.'));
    return el;
  }
  if (!isEmpty && state.search.trim()) {
    const el = mk('div','empty-state');
    const symbol=mk('div','empty-icon');symbol.append(svgIcon('search'));
    const clear=mk('button','settings-secondary','Borrar búsqueda');clear.type='button';
    clear.addEventListener('click',()=>{$('searchInput').value='';state.search='';state.page=1;render();$('searchInput').focus();});
    el.append(symbol, mk('h3','',`Sin resultados para «${state.search.trim()}»`),
      mk('p','',state.category==='all'?'Prueba con otras palabras o revisa la ortografía.':'Prueba en «Todas las noticias» o con otras palabras.'), clear);
    return el;
  }
  const el = mk('div','empty-state');
  const symbol=mk('div','empty-icon');symbol.append(svgIcon(isEmpty?'rss':'search'));
  el.append(symbol,
    mk('h3','',isEmpty ? 'Esperando las primeras noticias' : 'No hay noticias con estos filtros'),
    mk('p','',isEmpty ? 'Aún no se han cargado noticias. Revisa el estado de las fuentes RSS o vuelve a intentarlo después de la próxima actualización.' : 'Prueba otra categoría o fuente, desmarca tus filtros o busca con otros términos.'));
  return el;
}
let actionToastTimer,actionToastVersion=0;
function actionToast(message,{undo}={}){
  const toast=$('actionToast');
  toast.textContent=message;
  toast.hidden=false;
  const version=++actionToastVersion;
  let undoAvailable=typeof undo==='function';
  if(undoAvailable){
    const button=mk('button','toast-undo','Deshacer');button.type='button';
    button.addEventListener('click',()=>{
      if(!undoAvailable||version!==actionToastVersion)return;
      undoAvailable=false;
      window.clearTimeout(actionToastTimer);
      undo(button);
    });
    toast.append(button);
  }
  window.clearTimeout(actionToastTimer);
  actionToastTimer=window.setTimeout(()=>{undoAvailable=false;toast.hidden=true;},undoAvailable?8000:3200);
}
async function shareArticle(item) {
  const url=safeURL(item.url);
  if(!url){actionToast('Esta noticia no tiene un enlace válido.');return;}
  if(typeof navigator.share==='function'){
    try{
      await navigator.share({title:item.title||'Noticia',url});
      return;
    }catch(error){
      if(error?.name==='AbortError')return; // El usuario canceló el panel nativo.
    }
  }
  try{
    if(navigator.clipboard?.writeText) await navigator.clipboard.writeText(url);
    else {
      const input=document.createElement('textarea');
      input.value=url;input.readOnly=true;input.style.position='fixed';input.style.opacity='0';
      document.body.append(input);input.select();
      const copied=document.execCommand('copy');input.remove();
      if(!copied)throw new Error('No se pudo copiar automáticamente');
    }
    actionToast('Enlace de la noticia copiado. Ya puedes compartirlo.');
  }catch {
    // Fallback visible para navegadores que bloquean el portapapeles.
    window.prompt('Copia el enlace de la noticia:',url);
  }
}
function articleAction(iconName,label,extraClass=''){
 const button=mk('button','article-action'+(extraClass?' '+extraClass:''));button.type='button';
 button.title=label;button.setAttribute('aria-label',label);
 const symbol=mk('span','article-action-icon');symbol.setAttribute('aria-hidden','true');symbol.append(svgIcon(iconName));
 button.append(symbol,mk('span','article-action-label',label));return button;
}

let activeReaderItem=null;
function syncReaderActions(){
  if(!activeReaderItem)return;
  const saved=state.saved.has(activeReaderItem.id);
  $('readerSaveLabel').textContent=saved?'Quitar guardado':'Guardar';
  $('readerSave').classList.toggle('is-saved',saved);
  $('readerSave').setAttribute('aria-pressed',String(saved));
}
// «Cómo lo cuenta cada medio»: titulares de la misma historia agrupados por región.
function compareSection(item){
  const others=Array.isArray(item.also_in)?item.also_in.filter(x=>safeURL(x.url)):[];
  if(!others.length)return null;
  const entries=[{publisher:item.publisher||item.source,source:item.source,title:item.title,url:item.url,
    category:(item.categories||[])[0],published_at:item.published_at,lead:true},...others];
  const section=mk('section','reader-compare');section.id='readerCompare';
  section.setAttribute('aria-labelledby','readerCompareTitle');
  const head=mk('div','reader-compare-head');
  const h=mk('h3','','Cómo lo cuenta cada medio');h.id='readerCompareTitle';
  head.append(svgIcon('layers'),h,mk('span','reader-compare-count',`${coverageOf(item)} medios`));
  section.append(head);
  const withTitles=entries.filter(x=>String(x.title||'').trim()).length;
  if(withTitles<2)section.append(mk('p','reader-compare-note','Esta historia se agrupó antes de que Radar guardara los titulares de cada medio; se muestran solo los enlaces.'));
  const groups=new Map();
  for(const entry of entries.slice(0,13)){
    const kind=sourceKind(entry.source,entry.publisher);
    const key=kind?.label==='Oficial'?'Fuentes oficiales':categoryLabel(entry.category||'')||'Otros medios';
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(entry);
  }
  for(const [label,list] of groups){
    const group=mk('div','reader-compare-group');
    group.append(mk('h4','',label));
    const ul=mk('ul','');
    for(const entry of list){
      const li=mk('li','');
      const a=link(entry.url,String(entry.title||'').trim()||sourceLabel(entry.publisher,'Ver en el medio'),'reader-compare-link');
      const meta=mk('span','reader-compare-meta');
      meta.append(mk('strong','',sourceLabel(entry.publisher,'Otro medio')));
      if(entry.published_at)meta.append(document.createTextNode(' · '),timeNode(entry.published_at));
      if(entry.lead)meta.append(mk('span','reader-compare-lead','esta vista previa'));
      li.append(a,meta);ul.append(li);
    }
    group.append(ul);section.append(group);
  }
  section.append(mk('p','reader-compare-note','Titulares tal como los publicó cada medio. Radar no valora ni reescribe su contenido.'));
  return section;
}
function openArticleReader(item,event,focusTarget){
  if(event){
    // Ctrl/Cmd/middle-click still opens the original source using native browser behavior.
    if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||event.button!==0)return;
    event.preventDefault();
  }
  const dialog=$('articleReaderDialog');
  activeReaderItem=item;
  $('readerTitle').textContent=item.title||'Noticia sin título';
  $('readerCategory').textContent=categoryLabel((item.categories||[])[0]||'');
  const meta=$('readerMeta');meta.replaceChildren(
    mk('strong','',sourceLabel(item.publisher||item.source)),
    mk('span','',ageDate(item.published_at))
  );
  const cover=$('readerCover');cover.replaceChildren();cover.hidden=!state.showImages||state.lite||!safeURL(item.image);
  if(!cover.hidden){
    const image=mk('img');image.src=item.image;image.alt='Imagen ilustrativa de la noticia';
    image.referrerPolicy='no-referrer';
    image.addEventListener('error',()=>{cover.hidden=true;},{once:true});
    cover.append(image);
  }
  const summary=$('readerSummary');summary.replaceChildren();
  const description=String(item.summary||'').trim();
  summary.append(mk('p','',description||'Esta fuente solo publica un titular o un extracto breve. Abre el medio original para leer la noticia completa.'));
  const comparison=compareSection(item);
  if(comparison)summary.append(comparison);
  const url=safeURL(item.url);
  const source=$('readerOpenOriginal');source.href=url||'#';
  source.setAttribute('aria-disabled',String(!url));
  source.tabIndex=url?0:-1;
  source.target=state.newTab?'_blank':'_self';
  $('readerOpenOriginal').querySelector('.reader-open-hint').textContent=state.newTab?'en otra pestaña':'en esta pestaña';
  syncReaderActions();
  if(!dialog.open)dialog.showModal();
  dialog.querySelector('.reader-scroll')?.scrollTo?.({top:0});
  if(focusTarget==='compare'){
    requestAnimationFrame(()=>{const target=$('readerCompare');if(target){target.scrollIntoView({block:'start'});target.querySelector('h3')?.setAttribute('tabindex','-1');target.querySelector('h3')?.focus({preventScroll:true});}});
  }
  markRead(item.id,true);
}
function initArticleReader(){
  const dialog=$('articleReaderDialog');
  $('readerClose').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
  dialog.addEventListener('close',()=>{activeReaderItem=null;});
  $('readerSave').addEventListener('click',()=>{
    if(!activeReaderItem)return;
    const id=activeReaderItem.id;
    if(state.saved.has(id))state.saved.delete(id);else state.saved.add(id);
    persist('radar-saved',state.saved);
    syncReaderActions();
    render();
    actionToast(state.saved.has(id)?'Noticia guardada':'Noticia retirada de guardadas');
  });
  $('readerShare').addEventListener('click',()=>{if(activeReaderItem)void shareArticle(activeReaderItem);});
  $('readerOpenOriginal').addEventListener('click',event=>{
    if(!activeReaderItem||!safeURL(activeReaderItem.url)){event.preventDefault();return;}
    markRead(activeReaderItem.id,true);
  });
}
// Los medios que no envían fotografías reciben una cubierta editorial
// claramente tipográfica: nunca se presenta una ilustración como foto real.
function editorialCover(item) {
  const tile=mk('a','article-cover-placeholder');
  tile.href=safeURL(item.url)||'#';tile.target=state.newTab?'_blank':'_self';tile.rel='noopener noreferrer external';tile.referrerPolicy='no-referrer';
  tile.tabIndex=-1;tile.addEventListener('click',event=>openArticleReader(item,event));
  tile.setAttribute('aria-hidden','true');
  const wrap=mk('div','article-cover-placeholder-inner');
  const source=sourceLabel(item.publisher||item.source,'Medio de noticias');
  const sourceName=mk('span','article-cover-publisher',source);
  const note=mk('span','article-cover-note','Vista previa');
  wrap.append(svgIcon('newspaper'),sourceName,note);
  tile.append(wrap);
  return tile;
}
// Tarjeta: el título y la imagen abren la vista previa; Guardar queda a mano y
// el resto de acciones vive en un menú "⋯" para no repetir cuatro botones por tarjeta.
function card(item) {
  const isRead=state.read.has(item.id);
  const hasImage=Boolean(safeURL(item.image))&&!state.lite&&state.showImages;
  const el=mk('article','article-card '+(isRead?'read-article':'unread-card')+(hasImage?'':' no-cover'));el.dataset.articleId=item.id;
  const allowPreview=!state.lite&&state.showImages;
  if(hasImage){
    const cover=mk('a','cover'); cover.href=safeURL(item.url)||'#';cover.target=state.newTab?'_blank':'_self';cover.rel='noopener noreferrer external';cover.referrerPolicy='no-referrer';
    cover.tabIndex=-1;cover.setAttribute('aria-hidden','true');
    cover.addEventListener('click',event=>openArticleReader(item,event));
    const img=document.createElement('img');img.src=item.image;img.alt='';img.loading='lazy';img.decoding='async';img.referrerPolicy='no-referrer';
    img.addEventListener('error',()=>{
      cover.remove();
      el.classList.add('no-cover');
      if(allowPreview && !el.querySelector('.article-cover-placeholder'))
        el.prepend(editorialCover(item));
    },{once:true});
    cover.append(img);el.append(cover);
  } else if(allowPreview) {
    el.append(editorialCover(item));
  }
  const category=(item.categories||[])[0]||'';
  const topic=state.categories.indexOf(category);
  if(topic>=0)el.dataset.topic=String(topic+1);
  const content=mk('div','article-content');
  const title=mk('h3','article-title');
  const titleLink=link(item.url,item.title||'Sin título');
  titleLink.addEventListener('click',event=>openArticleReader(item,event));
  title.append(titleLink);
  const kicker=mk('div','article-kicker');
  kicker.append(mk('span','article-category',categoryLabel(category)));
  if(isNewSinceVisit(item)){const fresh=mk('span','article-new','Nueva');fresh.title='Publicada desde tu última visita';kicker.append(fresh);}
  content.append(kicker,title);
  const summary=String(item.summary||'').trim();
  if(summary&&state.showSummaries){
    content.append(mk('p','article-excerpt',summary));
  }else if(!summary){
    el.classList.add('no-excerpt');
  }
  const coverage=coverageOf(item);
  if(coverage>1){
    const others=Array.isArray(item.also_in)?item.also_in:[];
    const also=mk('button','article-also'+(coverage>=5?' is-wide':''));also.type='button';
    also.append(svgIcon('layers'),mk('span','',`${coverage} medios`));
    also.title='Cubierta por '+coverage+' medios'+(others.length?': '+others.slice(0,8).map(x=>sourceLabel(x.publisher,'Otro medio')).join(' · '):'')+'. Ver cómo lo cuenta cada uno.';
    also.setAttribute('aria-label',`Cubierta por ${coverage} medios. Comparar titulares`);
    also.addEventListener('click',()=>openArticleReader(item,null,'compare'));
    content.append(also);
  }
  const footer=mk('div','article-footer');
  const meta=mk('div','article-meta');
  const kind=kindBadge(item);
  if(kind)meta.append(kind);
  meta.append(mk('span','publisher',sourceLabel(item.publisher||item.source)),timeNode(item.published_at));
  const actions=mk('div','article-actions');
  actions.setAttribute('role','group');actions.setAttribute('aria-label','Acciones de esta noticia');
  const saved=state.saved.has(item.id);
  const save=mk('button','article-action article-save'+(saved?' saved':''));save.type='button';
  const saveLabel=saved?'Quitar de guardadas':'Guardar para después';
  save.title=saveLabel;save.setAttribute('aria-label',saveLabel+': '+(item.title||'noticia'));save.setAttribute('aria-pressed',String(saved));
  save.append(svgIcon(saved?'bookmark-filled':'bookmark'));
  save.addEventListener('click',()=>{
    if(state.saved.has(item.id))state.saved.delete(item.id);else state.saved.add(item.id);
    persist('radar-saved',state.saved);
    render();
    actionToast(state.saved.has(item.id)?'Noticia guardada.':'Noticia quitada de guardadas.');
  });
  const more=mk('button','article-action article-more');more.type='button';
  more.title='Más acciones';more.setAttribute('aria-label','Más acciones: '+(item.title||'noticia'));
  more.setAttribute('aria-haspopup','menu');more.setAttribute('aria-expanded','false');more.setAttribute('aria-controls','cardMenu');
  more.append(svgIcon('more'));
  more.addEventListener('click',()=>toggleCardMenu(item,more));
  // La acción de lectura es visible sin abrir el menú de tres puntos.
  const read=mk('button','article-action article-read-toggle');
  read.type='button';
  const readLabel=isRead?'Marcar como no leída':'Marcar como leída';
  read.title=readLabel;
  read.setAttribute('aria-label',readLabel+': '+(item.title||'noticia'));
  read.setAttribute('aria-pressed',String(isRead));
  read.append(svgIcon(isRead?'undo':'check'));
  read.addEventListener('click',()=>{
    const next=!state.read.has(item.id);
    markRead(item.id,next);
    actionToast(next?'Marcada como leída.':'Marcada como no leída.');
  });
  more.setAttribute('aria-keyshortcuts','Shift+F10');
  el.addEventListener('contextmenu',event=>{
    event.preventDefault();
    closeCardMenu();
    toggleCardMenu(item,more,{x:event.clientX,y:event.clientY});
  });
  el.addEventListener('keydown',event=>{
    if(event.key==='ContextMenu'||(event.shiftKey&&event.key==='F10')){
      event.preventDefault();
      closeCardMenu();
      toggleCardMenu(item,more);
    }
  });
  actions.append(read,save,more);
  footer.append(meta,actions);
  content.append(footer);
  el.append(content);return el;
}
let cardMenuItem=null,cardMenuAnchor=null;
function closeCardMenu(restoreFocus=false){
  const menu=$('cardMenu');
  if(!menu||menu.hidden)return;
  menu.hidden=true;
  cardMenuAnchor?.setAttribute('aria-expanded','false');
  if(restoreFocus&&cardMenuAnchor?.isConnected)cardMenuAnchor.focus();
  cardMenuItem=null;cardMenuAnchor=null;
}
function toggleCardMenu(item,anchor,point=null){
  const menu=$('cardMenu');
  if(!menu.hidden&&cardMenuAnchor===anchor){closeCardMenu(true);return;}
  closeCardMenu();
  cardMenuItem=item;cardMenuAnchor=anchor;
  const isRead=state.read.has(item.id);
  $('cardMenuReadLabel').textContent=isRead?'Marcar como no leída':'Marcar como leída';
  menu.querySelector('[data-card-action="read"] .ui-icon-slot').replaceChildren(svgIcon(isRead?'undo':'check'));
  const open=$('cardMenuOpen'),url=safeURL(item.url);
  open.hidden=!url;open.href=url||'#';
  menu.hidden=false;anchor.setAttribute('aria-expanded','true');
  const r=anchor.getBoundingClientRect(),w=menu.offsetWidth,h=menu.offsetHeight;
  const atCursor=point&&point.x>0&&point.y>0;
  const left=atCursor?point.x: r.right-w;
  const top=atCursor?point.y+4:r.bottom+6;
  menu.style.left=Math.max(8,Math.min(left,window.innerWidth-w-8))+'px';
  menu.style.top=Math.max(8,Math.min(top,window.innerHeight-h-8))+'px';
  // El foco del menú fijo no debe desplazar la página y cerrarlo inmediatamente.
  menu.querySelector('[role="menuitem"]:not([hidden])')?.focus({preventScroll:true});
}
function initCardMenu(){
  const menu=$('cardMenu');
  const entries=()=>[...menu.querySelectorAll('[role="menuitem"]:not([hidden])')];
  menu.addEventListener('click',event=>{
    const target=event.target.closest('[data-card-action]');
    if(!target||!cardMenuItem)return;
    const item=cardMenuItem,action=target.dataset.cardAction;
    if(action==='share'){closeCardMenu(true);void shareArticle(item);}
    else if(action==='read'){const next=!state.read.has(item.id);closeCardMenu(true);if(next)markArticlesRead([item]);else{markRead(item.id,false);actionToast('Marcada como no leída.');}}
    else if(action==='open'){markRead(item.id,true);closeCardMenu();}
  });
  menu.addEventListener('keydown',event=>{
    const list=entries(),index=list.indexOf(document.activeElement);
    if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
      event.preventDefault();
      const next=event.key==='Home'?0:event.key==='End'?list.length-1:(index+(event.key==='ArrowDown'?1:-1)+list.length)%list.length;
      list[next]?.focus();
    }else if(event.key==='Escape'){event.preventDefault();closeCardMenu(true);}
    else if(event.key==='Tab')closeCardMenu();
  });
  document.addEventListener('pointerdown',event=>{if(!event.target.closest('#cardMenu,.article-more'))closeCardMenu();});
  window.addEventListener('resize',()=>closeCardMenu(),{passive:true});
  // Cerrar solo cuando la persona inicia el desplazamiento. Un evento scroll
  // causado por foco/Playwright puede ocurrir entre abrir el menú y pulsar una acción.
  window.addEventListener('wheel',()=>closeCardMenu(),{passive:true});
  document.addEventListener('touchmove',()=>closeCardMenu(),{passive:true});
}
// Una revisión por ID impide que Deshacer borre una marca manual posterior.
const readRevisions=new Map();
function markRead(id,value){
  const original=state.read.has(id);
  if(value)state.read.add(id);else state.read.delete(id);
  if(original===value)return;
  readRevisions.set(id,(readRevisions.get(id)||0)+1);
  const active=document.activeElement;
  const returnFocus=active?.classList?.contains('article-read-toggle')===true;
  persist('radar-read',state.read);
  // Renderiza tarjetas, pestañas, filtros y contadores desde un único estado.
  // La biblioteca restaura los indicadores de las seis carpetas en su wrapper.
  render();
  if(returnFocus){
    const target=[...document.querySelectorAll('#articleGrid .article-card, #dashboardFeature .article-card')]
      .find(el=>el.dataset.articleId===id)?.querySelector('.article-read-toggle');
    (target||$('articleGrid').querySelector('.article-read-toggle')||document.querySelector('.mode-tab.active'))?.focus({preventScroll:true});
  }
}
function markArticlesRead(items){
  const focusOrigin=document.activeElement;
  const readSet=state.read;
  const changed=[];
  for(const item of items){
    const id=item?.id;
    if(typeof id!=='string'||!id||state.read.has(id))continue;
    state.read.add(id);
    const revision=(readRevisions.get(id)||0)+1;
    readRevisions.set(id,revision);changed.push({id,revision});
  }
  if(!changed.length){actionToast('No había noticias pendientes.');return 0;}
  persist('radar-read',state.read);render();
  actionToast(changed.length===1?'1 noticia marcada como leída.':format.format(changed.length)+' noticias marcadas como leídas.',{
    undo:undoButton=>{
      const restoreFocus=document.activeElement===undoButton;
      let reverted=0;
      for(const {id,revision} of changed){
        if(state.read!==readSet||readRevisions.get(id)!==revision||!state.read.has(id))continue;
        state.read.delete(id);readRevisions.set(id,revision+1);reverted++;
      }
      if(reverted){persist('radar-read',state.read);render();}
      actionToast(reverted?'Se deshizo la marca de lectura.':'No quedan marcas de este lote por deshacer.');
      // El mensaje retira Deshacer del DOM. Devolver su foco al control estable
      // del lote sin interferir con otro diálogo o una acción de foco posterior.
      if(restoreFocus&&focusOrigin?.isConnected&&!focusOrigin.disabled&&
        !focusOrigin.matches?.(':disabled')&&!focusOrigin.closest('[hidden],[inert]')&&
        !document.querySelector('dialog[open]')&&
        (document.activeElement===undoButton||document.activeElement===document.body)){
        focusOrigin.focus({preventScroll:true});
      }
    }
  });
  return changed.length;
}
function render() {
  const filtered=applyFilters(), visible=filtered.slice(0,state.page*state.pageSize);
  updateSourceCounts();
  $('visibleCount').textContent=state.mode==='saved'||newsCountsComplete()
    ?`${format.format(filtered.length)} ARTÍCULOS`
    :newsCountsUnavailable()?'TOTAL NO DISPONIBLE':'CALCULANDO TOTAL…';
  $('markAllVisible').disabled=!visible.some(item=>!state.read.has(item.id));
  const unreadSummary=newsCountsComplete()?`${format.format(applyFilters('unread').length)} sin leer con estos filtros`
    :newsCountsUnavailable()?'total no disponible':'calculando total del archivo…';
  $('filterSummary').textContent=`${format.format(visible.length)} visibles · ${unreadSummary}`;
  const modeCounts={
    all:state.mode==='all'?filtered.length:applyFilters('all').length,
    unread:state.mode==='unread'?filtered.length:applyFilters('unread').length,
    saved:state.mode==='saved'?filtered.length:applyFilters('saved').length
  };
  for(const [mode,id,label] of [
    ['all','allCount','Todas'],
    ['unread','unreadCount','Sin leer'],
    ['saved','savedCount','Guardadas']
  ]){
    const count=modeCounts[mode];
    $(id).textContent=mode==='saved'?format.format(count):newsCountText(count);
    const button=document.querySelector(`.mode-tab[data-mode="${mode}"]`);
    const basis=mode==='saved'?'guardadas disponibles':'noticias disponibles';
    button.title=mode==='saved'||newsCountsComplete()
      ?`${label}: ${format.format(count)} ${basis}. Los contadores respetan los filtros activos.`
      :`${label}: ${newsCountsUnavailable()?'total no disponible':'calculando el total del archivo'}.`;
    button.setAttribute('aria-label',button.title);
  }
  const query=state.search.trim();
  describeSearch(query,filtered.length);
  // Complete the archive in the background so every count uses real articles.
  if(state.ready&&hasHistory()&&!state.historyLoading&&!state.historyFailed&&state.feedMeta.generated_at===state.generated)void loadHistory();
  const grid=$('articleGrid'); grid.className='article-grid'+(state.layout === 'list'?' list-view':'');
  // La portada y el resumen tienen sus propios componentes: no construir
  // tarjetas ocultas en cada pulsación o actualización de esos paneles.
  if(state.pageView==='feed'){
    if (!visible.length) grid.replaceChildren(emptyState(filtered));
    else grid.replaceChildren(...visible.map(card));
    $('loadMore').hidden=visible.length>=filtered.length;
    updateHistoryButton();
  }else if(grid.childElementCount){
    grid.replaceChildren();
    $('loadMore').hidden=true;
  }
  document.querySelectorAll('.mode-tab').forEach(button=>button.classList.toggle('active',button.dataset.mode === state.mode));
  document.querySelectorAll('.view-button').forEach(button=>button.classList.toggle('active',button.dataset.view === state.layout));
  document.body.classList.toggle('layout-list',state.layout==='list');
  syncColumnsControl();
  if(state.pageView==='dashboard')renderDashboard();
  if(state.pageView==='briefing'&&typeof renderBriefing==='function')renderBriefing();
}

let historyRequest=null;
let historyAbort=null;
function historyFiles(){return (Array.isArray(state.feedMeta?.archive_files)?state.feedMeta.archive_files:[]).filter(x=>/^archive-\d{2}\.json$/.test(x)).slice(0,32);}
function hasHistory(){return !state.historyLoaded&&historyFiles().length>0;}
function newsCountsComplete(){
  const meta=state.feedMeta,files=meta?.archive_files;
  return state.ready&&!!meta&&meta.generated_at===state.generated
    &&Number.isSafeInteger(meta.total_articles)&&meta.total_articles===state.items.length
    &&Array.isArray(files)&&files.length===historyFiles().length&&new Set(files).size===files.length
    &&!hasHistory();
}
function newsCountsUnavailable(){return state.ready&&(state.historyFailed||!state.feedMeta||state.feedMeta.generated_at!==state.generated||(!hasHistory()&&!newsCountsComplete()));}
function newsCountText(count){return newsCountsComplete()?format.format(count):newsCountsUnavailable()?'—':'…';}
function newsUnreadText(count){return newsCountsComplete()?`${format.format(count)} noticias sin leer`:newsCountsUnavailable()?'total no disponible':'calculando noticias sin leer';}
function updateHistoryButton(){
  $('loadMore').disabled=state.historyLoading;
  if(state.historyLoading){$('loadMore').hidden=false;$('loadMore').disabled=true;$('loadMore').textContent='Cargando historial…';}
  else if(hasHistory()&&state.pageView==='feed'){
    $('loadMore').hidden=false;$('loadMore').disabled=false;
    $('loadMore').replaceChildren(mk('span','',state.historyFailed?'Reintentar historial':'Cargar noticias anteriores'),svgIcon('arrow-down'));
  }else $('loadMore').replaceChildren(mk('span','','Cargar más noticias'),svgIcon('arrow-down'));
}
async function loadHistory(){
  if(!hasHistory()||historyRequest||state.feedMeta.generated_at!==state.generated)return historyRequest;
  const manifest=state.feedMeta;
  const controller=new AbortController();historyAbort=controller;
  state.historyFailed=false;state.historyLoading=true;updateHistoryButton();
  historyRequest=(async()=>{
    try{
      // Limitar las descargas simultáneas: 16 fragmentos pueden agotar memoria
      // y conexiones en móviles; mantener el orden y validar todo antes de aplicar.
      const files=historyFiles(),docs=new Array(files.length);
      let next=0;
      async function worker(){
        while(next<files.length){
          const i=next++;
          docs[i]=await dataFetch('./data/'+files[i],{signal:controller.signal});
        }
      }
      const workers=Array.from({length:Math.min(3,files.length)},()=>worker());
      try{await Promise.all(workers);}
      catch(error){controller.abort();await Promise.allSettled(workers);throw error;}
      if(manifest!==state.feedMeta)return;
      const items=new Map(state.items.map(x=>[x.id,x]));
      for(const doc of docs){
        if(doc.generated_at!==manifest.generated_at||!Array.isArray(doc.items))throw Error('Archivo de historial incompatible');
        for(const article of doc.items)if(article&&typeof article.id==='string'&&!items.has(article.id))items.set(article.id,article);
      }
      state.items=[...items.values()].sort((a,b)=>String(b.published_at||b.first_seen_at||'').localeCompare(String(a.published_at||a.first_seen_at||'')));
      state.historyLoaded=true;
    }catch(error){if(manifest===state.feedMeta){console.warn('Historial RSS:',error);state.historyFailed=true;actionToast('No fue posible cargar noticias anteriores.');}}
    finally{state.historyLoading=false;historyRequest=null;historyAbort=null;render();}
  })();
  return historyRequest;
}

const NEWS_SNAPSHOT_KEY='radar-last-visible-news-v1';
function publishNewRSSNews(previousIds=null){
  // IDs publicados, no acciones de lectura o cambios de filtros.
  const current=state.items.slice(0,300).filter(item=>item&&typeof item.id==='string'&&item.id);
  let known=previousIds;
  if(known===null){
    try{
      const stored=JSON.parse(localStorage.getItem(NEWS_SNAPSHOT_KEY)||'null');
      known=Array.isArray(stored)?new Set(stored.filter(id=>typeof id==='string')):null;
    }catch{known=null;}
  }
  try{localStorage.setItem(NEWS_SNAPSHOT_KEY,JSON.stringify(current.map(item=>item.id)));}
  catch(error){console.warn('Radar-RSS: instantánea local no disponible.',error);}
  if(!known||!known.size||!current.length)return;
  const added=current.filter(item=>!known.has(item.id));
  if(!added.length)return;
  // Emitir después del render, cuando las carpetas y tarjetas ya están montadas.
  window.requestAnimationFrame(()=>window.dispatchEvent(new CustomEvent(
    'radar:news-added',{detail:{items:added}}
  )));
}

// Comprobación LOCAL de publicaciones nuevas: cada 15 min.
// La recopilación de RSS de origen sigue cada tres horas por GitHub Actions.
const CHECK_INTERVAL_MS=15*60*1000;
let nextCheckAt=Date.now()+CHECK_INTERVAL_MS;
let checkStartedAt=Date.now();
let checkTimer=null;
let feedRefreshBusy=false;
let bootBusy=false;
let pendingPublication=null;
function freshnessLabel(){
  if(!state.generated)return state.ready?'Sin sincronizar':'Cargando…';
  const age=ageDate(state.generated);
  return age==='Ahora'?'Actualizado ahora':'Actualizado '+age.charAt(0).toLowerCase()+age.slice(1);
}
function updateScheduleProgress(){
  $('lastUpdate').textContent=feedRefreshBusy?'Buscando novedades…':freshnessLabel();
  const exact=state.generated?' Última recopilación: '+shortDate(state.generated)+'.':'';
  const description='Radar-RSS busca noticias nuevas cada 15 minutos; los medios se recopilan aproximadamente cada 3 horas.'+exact;
  $('refreshCycle').title=description;
  $('lastUpdate').title=description;
  $('refreshNow').disabled=feedRefreshBusy||bootBusy;
  $('refreshNow').setAttribute('aria-busy',String(feedRefreshBusy||bootBusy));
  $('refreshNowLabel').textContent=feedRefreshBusy?'Buscando…':bootBusy?'Cargando…':'Actualizar';
}
function refreshFeedback(message,status='success'){
  $('refreshStatus').textContent=message;
  $('refreshStatus').dataset.state=status;
}
function scheduleNextCheck(){
  window.clearTimeout(checkTimer);
  checkStartedAt=Date.now();
  nextCheckAt=checkStartedAt+CHECK_INTERVAL_MS;
  checkTimer=window.setTimeout(()=>{void refreshPublishedData();},CHECK_INTERVAL_MS);
  updateScheduleProgress();
}
// Comprueba si GitHub Pages publicó datos nuevos, sin descargar directamente las fuentes.
async function refreshPublishedData({manual=false}={}){
  if(feedRefreshBusy||bootBusy)return;
  if((!state.ready&&!manual)||document.hidden){scheduleNextCheck();return;}
  feedRefreshBusy=true;updateScheduleProgress();
  if(manual)refreshFeedback('Comprobando publicaciones…','loading');
  else refreshFeedback('','idle');
  const controller=new AbortController();
  const timeout=window.setTimeout(()=>controller.abort(),15_000);
  const options={signal:controller.signal,fresh:manual};
  try{
    const meta=await dataFetch('./data/meta.json?check='+Date.now(),options);
    const generatedTime=typeof meta?.generated_at==='string'?Date.parse(meta.generated_at):NaN;
    if(!Number.isFinite(generatedTime))throw Error('Fecha de publicación RSS incompatible');
    if(pendingPublication&&generatedTime<=Date.parse(pendingPublication.meta.generated_at)){
      if(manual){applyPendingPublication();refreshFeedback('Noticias actualizadas.');}
      return;
    }
    if(meta.generated_at===state.generated){
      if(!newsCountsComplete()&&!state.historyLoading){
        state.feedMeta=meta;state.historyLoaded=false;state.historyFailed=false;render();
      }
      if(manual)refreshFeedback('No hay novedades publicadas.');
      return;
    }
    if(generatedTime<=Date.parse(state.generated)){
      if(manual)refreshFeedback('No hay una publicación más reciente disponible.');
      return;
    }
    const [sources,latest,status]=await Promise.all([
      dataFetch('./data/sources.json?check='+Date.now(),options),
      dataFetch('./data/latest.json?check='+Date.now(),options),
      dataFetch('./data/status.json?check='+Date.now(),options)
    ]);
    // latest y status llevan la misma generación del manifiesto. sources no
    // publica sello temporal; se valida su estructura antes de aceptar el lote.
    if(latest?.generated_at!==meta.generated_at||status?.checked_at!==meta.generated_at||
      !Array.isArray(latest.items)||!latest.items.every(item=>item&&typeof item.id==='string'&&item.id&&
        [item.source_ids,item.categories].every(values=>values===undefined||Array.isArray(values)&&values.every(value=>typeof value==='string')))||
      !Array.isArray(sources?.sources)||!sources.sources.every(source=>source&&typeof source.id==='string'&&
        typeof source.name==='string'&&typeof source.category==='string')||
      !Array.isArray(sources.categories)||!sources.categories.every(category=>typeof category==='string')||
      !Array.isArray(status.feeds)||!status.feeds.every(feed=>feed&&typeof feed.id==='string')||
      !Array.isArray(meta.archive_files)||!meta.archive_files.every(file=>/^archive-\d{2}\.json$/.test(file))){
      throw Error('Publicación RSS incompatible');
    }
    pendingPublication={meta,sources,latest,status};
    if(manual){applyPendingPublication();refreshFeedback('Noticias actualizadas.');return;}
    const previousIds=new Set(state.items.map(item=>item.id));
    const added=new Set(latest.items.filter(item=>!previousIds.has(item.id)).map(item=>item.id)).size;
    $('publicationMessage').textContent=added?`Hay ${format.format(added)} ${added===1?'noticia nueva':'noticias nuevas'}`:'Hay una actualización disponible';
    $('publicationNotice').hidden=false;
  }catch(error){
    const timedOut=controller.signal.aborted;
    controller.abort();
    console.warn('Comprobación RSS:',error);
    if(manual)refreshFeedback(timedOut?'La comprobación tardó demasiado. Vuelve a intentar.':'No se pudo actualizar. Revisa tu conexión y vuelve a intentar.','error');
  }
  finally{window.clearTimeout(timeout);feedRefreshBusy=false;scheduleNextCheck();}
}

function applyPendingPublication(){
  if(!pendingPublication)return;
  const {meta,sources,latest,status}=pendingPublication;
  const previousIds=new Set(state.items.map(item=>item.id));
  // Cambiar todo antes de renderizar; cualquier descarga antigua de historial
  // queda invalidada por la identidad de feedMeta sin cerrar el lector abierto.
  state.sources=sources.sources;state.categories=sources.categories;
  state.items=latest.items;state.health=status.feeds;state.healthCheckedAt=status.checked_at||null;
  state.feedMeta=meta;state.generated=meta.generated_at;
  state.ready=true;
  state.historyLoaded=false;state.historyFailed=false;
  historyAbort?.abort();pendingPublication=null;
  $('publicationNotice').hidden=true;
  updateScheduleProgress();
  buildNav();fillSelect();updateHeader();statusSummary();render();
  if($('settingsDialog').open){renderSettingsSources();renderFeedHealth();updateDataCounts();}
  publishNewRSSNews(previousIds);
}

async function dataFetch(path, options={}) {
  const response = await fetch(path,{cache:options.fresh?'no-store':'no-cache',signal:options.signal});
  if (!response.ok) throw new Error(`HTTP ${response.status} al abrir ${path}`);
  return response.json();
}
async function boot() {
  bootBusy=true;updateScheduleProgress();
  const controller=new AbortController();
  const timeout=window.setTimeout(()=>controller.abort(),15_000);
  const options={signal:controller.signal};
  setTheme(state.theme);
  applyDisplaySettings();
  state.mode=state.startMode;
  try {
    const [sources, articles, status] = await Promise.all([
      dataFetch('./data/sources.json',options), dataFetch('./data/latest.json',options), dataFetch('./data/status.json',options)
    ]);
    state.sources=Array.isArray(sources.sources)?sources.sources:[];
    state.categories=Array.isArray(sources.categories)?sources.categories:[];
    state.items=Array.isArray(articles.items)?articles.items:[];
    state.health=Array.isArray(status.feeds)?status.feeds:[];state.healthCheckedAt=status.checked_at||null;
    state.generated=articles.generated_at;
    try{state.feedMeta=await dataFetch('./data/meta.json',options);}catch{state.feedMeta=null;state.historyLoaded=true;}
    state.ready=true;
    updateScheduleProgress();

  } catch(err) {
    state.ready=false;
    console.error('Carga de fuentes:',err);
  } finally {
    window.clearTimeout(timeout);controller.abort();
    bootBusy=false;updateScheduleProgress();
  }
  statusSummary(); navigateFromHash();
  if(state.ready)publishNewRSSNews();
}
let progressiveLoads=0;
function initSocialNavigation(){
 const back=$('backTop');back.addEventListener('click',()=>window.scrollTo({top:0,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'}));
 window.addEventListener('scroll',()=>{back.hidden=window.scrollY<600;},{passive:true});
 if('IntersectionObserver' in window){
  const observer=new IntersectionObserver(entries=>{
   // Reintentar no es paginar: el botón debe quedarse quieto hasta recuperar el archivo.
   if(!entries.some(entry=>entry.isIntersecting)||state.pageView!=='feed'||state.historyFailed||state.historyLoading||window.scrollY<350||progressiveLoads>=3||$('loadMore').hidden)return;
   progressiveLoads++;state.page+=1;render();
  },{rootMargin:'250px 0px'});
  observer.observe($('loadMore'));
 }
}
function initHandlers() {
 initSocialNavigation();
 initArticleReader();
 initMobileNav();
 initCardMenu();
  window.setInterval(updateScheduleProgress,30_000);
  scheduleNextCheck();
  $('refreshNow').addEventListener('click',()=>{void refreshPublishedData({manual:true});});
  $('publicationApply').addEventListener('click',applyPendingPublication);
  window.addEventListener('focus',()=>{if(document.visibilityState==='visible'&&Date.now()>=nextCheckAt){void refreshPublishedData();}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){if(Date.now()>=nextCheckAt){void refreshPublishedData();}else{updateScheduleProgress();}}});
  // Resolver la función en cada cambio: library.js y features.js la amplían después de cargar app.js.
  window.addEventListener('hashchange',()=>navigateFromHash());
  $('feedHealthIndicator').addEventListener('click',openFeedHealth);
  $('statusDetails').addEventListener('click',openFeedHealth);
  $('statusDismiss').addEventListener('click',()=>{
    const banner=$('statusBanner');
    try{localStorage.setItem('radar-dismissed-health-notice-v1',banner.dataset.signature||'');}catch{}
    banner.hidden=true;
  });
  const feedHealthDialog=$('feedHealthDialog');
  $('closeFeedHealth').addEventListener('click',()=>feedHealthDialog.close());
  $('doneFeedHealth').addEventListener('click',()=>feedHealthDialog.close());
  feedHealthDialog.addEventListener('click',e=>{if(e.target===feedHealthDialog)feedHealthDialog.close();});
  document.querySelectorAll('.mode-tab').forEach(button=>button.addEventListener('click',()=>{state.mode=button.dataset.mode;state.page=1;progressiveLoads=0;render();}));
  initColumnsMenu();
  document.querySelector('.view-button[data-view="list"]').addEventListener('click',()=>{
    closeColumnsMenu();
    state.layout='list';state.page=1;progressiveLoads=0;
    savePref('layout',state.layout);applyDisplaySettings();render();
  });
  $('sourceSelect').addEventListener('change',e=>{state.feed=e.target.value;state.page=1;progressiveLoads=0;render();});
  $('searchInput').addEventListener('input',e=>{
    state.search=e.target.value;state.page=1;progressiveLoads=0;
    // Desde la portada, buscar lleva al listado completo con los resultados.
    if(state.search.trim()&&state.pageView!=='feed'){goTo('all');return;}
    render();
  });
  // En móvil el buscador se despliega bajo la barra para no ocupar espacio fijo.
  $('searchToggle').addEventListener('pointerdown',e=>e.preventDefault());
  $('searchToggle').addEventListener('click',()=>{
    const open=!document.body.classList.contains('search-open');
    document.body.classList.toggle('search-open',open);
    $('searchToggle').setAttribute('aria-expanded',String(open));
    if(open)$('searchInput').focus();
  });
  $('searchInput').addEventListener('blur',()=>{
    if(!$('searchInput').value.trim()){document.body.classList.remove('search-open');$('searchToggle').setAttribute('aria-expanded','false');}
  });
  $('searchInput').addEventListener('keydown',e=>{
    if(e.key==='Escape'&&e.target.value){e.preventDefault();e.target.value='';state.search='';state.page=1;render();}
  });
  $('loadMore').addEventListener('click',()=>{if(hasHistory()&&(state.historyFailed||state.page*state.pageSize>=applyFilters().length)){void loadHistory();return;}state.page+=1;render();});
  $('themeToggle').addEventListener('click',()=>setTheme(document.body.classList.contains('light')?'dark':'light',true));
  $('markAllVisible').addEventListener('click',()=>{markArticlesRead(applyFilters().slice(0,state.page*state.pageSize));});
  const dialog=$('aboutDialog');
  const open=e=>{if(e)e.preventDefault();dialog.showModal();};
  $('footerInfo').addEventListener('click',open);
  $('closeAbout').addEventListener('click',()=>dialog.close()); $('dialogAccept').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target === dialog) dialog.close();});
  initSettingsHandlers();
  document.addEventListener('keydown',e=>{if(e.key==='/' && !e.ctrlKey && !e.metaKey && !e.altKey && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName) && !document.querySelector('dialog[open]') && !document.body.classList.contains('nav-open')){e.preventDefault();$('searchInput').focus();}});
}
hydrateIcons(); initHandlers(); updateScheduleProgress(); boot();
