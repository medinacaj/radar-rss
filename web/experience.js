"use strict";
/* Reading preferences use the existing settings schema. Only pinned destinations
   add browser-local data; no requests, duplicated navigation tree or telemetry. */
(() => {
  function effectiveColumns(width,titleSize,fontSize,requested,gap=20){
    const size=Math.max(14,Math.min(22,Number(titleSize)||16));
    const minimum=280+Math.max(0,size-16)*14+(fontSize==='large'?40:0);
    const fitting=Math.max(1,Math.floor((Math.max(0,Number(width)||0)+gap)/(minimum+gap)));
    const chosen=requested==='auto'?6:Math.max(1,Math.min(6,Number(requested)||1));
    return Math.min(chosen,fitting);
  }
  const profiles={
    visual:{layout:'cards',density:'comfortable',showImages:true,showSummaries:true},
    compact:{layout:'cards',density:'compact',showImages:false,showSummaries:true},
    headlines:{layout:'list',density:'compact',showImages:false,showSummaries:false}
  };
  function profileSettings(profile,current){return {...current,...(profiles[profile]||{})};}
  function normalizePreferences(value){
    const input=value&&typeof value==='object'&&!Array.isArray(value)?value.pinnedDestinations:null;
    return {pinnedDestinations:Array.isArray(input)?[...new Set(input.filter(item=>
      typeof item==='string'&&item.trim()===item&&item.length>0&&item.length<=150&&
      !['__proto__','prototype','constructor'].includes(item)&&!/[\u0000-\u001f]/.test(item)
    ))].slice(0,25):[]};
  }
  if(typeof module!=='undefined'&&module.exports){
    module.exports={effectiveColumns,profileSettings,normalizePreferences};
    return;
  }
  const get=id=>document.getElementById(id);
  if(!get('articleGrid')||get('readingProfile'))return;
  const KEY='radar-experience-v1';
  const read=()=>{try{return normalizePreferences(JSON.parse(localStorage.getItem(KEY)||'null'));}catch{return normalizePreferences(null);}};
  let preferences=read();
  const groups=()=>window.RadarLibrary?.getSourceGroups?.()||[];
  const destination=group=>group.key.startsWith('manual:')?'carpeta/'+group.key.slice(7):group.key.slice(8);
  const validDestinations=()=>new Set(groups().map(destination));
  function getPinnedDestinations(){
    const valid=validDestinations();
    return preferences.pinnedDestinations.filter(item=>valid.has(item));
  }
  function storePreferences(value){
    const clean=normalizePreferences(value);
    // A failed write leaves both the saved and live preferences unchanged.
    localStorage.setItem(KEY,JSON.stringify(clean));
    preferences=clean;
  }
  window.RadarExperience=Object.freeze({getPinnedDestinations});
  window.RadarLibrary?.registerBackupModule?.('experiencePreferences',{
    validate:normalizePreferences,
    export:()=>({pinnedDestinations:getPinnedDestinations()}),
    restore(value,options={}){if(options.persist===false)preferences=normalizePreferences(value);else storePreferences(value);decorateNavigation();},
    reset(){
      localStorage.removeItem(KEY);
      preferences=normalizePreferences(null);decorateNavigation();
    }
  });

  const profileLabel=mk('label','experience-profile');
  profileLabel.append(mk('span','','Lectura'));
  const profile=mk('select');profile.id='readingProfile';profile.setAttribute('aria-label','Perfil de lectura');
  for(const [id,label] of [['visual','Visual'],['compact','Compacto'],['headlines','Solo titulares'],['custom','Personalizado']]){
    profile.append(new Option(label,id));
  }
  profileLabel.append(profile);
  document.querySelector('.display-controls')?.prepend(profileLabel);
  const columnStatus=mk('output','experience-column-status');columnStatus.id='effectiveColumns';
  columnStatus.setAttribute('aria-live','polite');columnStatus.setAttribute('aria-atomic','true');
  columnStatus.setAttribute('aria-label','Columnas visibles');
  get('cardsColumnsControl')?.after(columnStatus);
  const columnToggle=get('columnsToggle');
  if(columnToggle&&!columnToggle.querySelector('.experience-columns-label')){
    const label=mk('span','experience-columns-label','Columnas');
    columnToggle.prepend(label);
  }
  const listButton=document.querySelector('[data-view="list"]');
  if(listButton)listButton.append(mk('span','experience-action-label','Lista'));

  profile.addEventListener('change',()=>{
    if(!profiles[profile.value])return;
    Object.assign(state,profileSettings(profile.value,state));
    for(const [key,field] of [['layout','layout'],['density','density'],['show-images','showImages'],['show-summaries','showSummaries']])savePref(key,state[field]);
    state.page=1;applyDisplaySettings();render();syncSettings();
  });
  function syncProfile(){
    profile.value=Object.entries(profiles).find(([,value])=>
      Object.entries(value).every(([key,setting])=>state[key]===setting))?.[0]||'custom';
    profile.querySelector('[value="custom"]').disabled=true;
  }
  function syncColumns(){
    const grid=get('articleGrid');
    if(!grid)return;
    const width=grid.getBoundingClientRect().width;
    if(!width)return;
    const gap=parseFloat(getComputedStyle(grid).columnGap)||20;
    const count=state.layout==='list'?1:effectiveColumns(width,state.cardTitleSize,state.fontSize,state.columns,gap);
    const raw=String(count);
    if(grid.style.getPropertyValue('--experience-columns')!==raw)grid.style.setProperty('--experience-columns',raw);
    document.body.dataset.effectiveColumns=raw;
    columnStatus.hidden=state.layout==='list';
    const text=count+' '+(count===1?'columna':'columnas')+(state.columns==='auto'?' · Auto':Number(state.columns)!==count?' · '+state.columns+' elegidas':'');
    if(columnStatus.textContent!==text)columnStatus.textContent=text;
    columnStatus.title='Se adaptan al espacio y al tamaño de letra. Tu elección de columnas se conserva.';
    const header=document.querySelector('.topbar');
    if(header){
      const style=getComputedStyle(header);
      const top=style.position==='sticky'?header.getBoundingClientRect().height+(parseFloat(style.top)||0)+8:8;
      document.body.style.setProperty('--experience-sticky-top',top+'px');
    }
  }
  const baseDisplay=applyDisplaySettings;
  applyDisplaySettings=function(...args){const result=baseDisplay.apply(this,args);syncProfile();syncColumns();return result;};

  function labelAction(button,text){
    if(!button||button.querySelector('.experience-action-label'))return;
    button.append(mk('span','experience-action-label',text));
  }
  function decorateCard(node){
    labelAction(node.querySelector('.article-save'),state.saved.has(node.dataset.articleId)?'Guardada':'Guardar');
    labelAction(node.querySelector('.article-more'),'Más');
    labelAction(node.querySelector('.article-read-toggle'),state.read.has(node.dataset.articleId)?'Sin leer':'Marcar leída');
    return node;
  }
  const baseCard=card;
  card=function(...args){return decorateCard(baseCard.apply(this,args));};
  // Cards already rendered while the deferred scripts were being loaded.
  document.querySelectorAll('.article-card').forEach(decorateCard);

  const nav=get('libraryFolderNav');
  const searchWrap=mk('div','experience-library-search');
  const searchLabel=mk('label','','Buscar carpetas y fuentes');searchLabel.htmlFor='sidebarLibrarySearch';
  const searchRow=mk('div','experience-search-row');
  const search=mk('input');search.id='sidebarLibrarySearch';search.type='search';
  search.placeholder='Nombre de carpeta o medio';search.autocomplete='off';search.maxLength=90;
  search.setAttribute('aria-controls','libraryFolderNav sidebarSourceResults');
  const clearSearch=mk('button','','Borrar');clearSearch.type='button';clearSearch.hidden=true;
  clearSearch.setAttribute('aria-label','Borrar búsqueda de carpetas y fuentes');
  searchRow.append(search,clearSearch);
  const results=mk('div','experience-source-results');results.id='sidebarSourceResults';results.hidden=true;
  const searchStatus=mk('p','experience-search-status');searchStatus.id='sidebarLibrarySearchStatus';
  searchStatus.setAttribute('role','status');searchStatus.hidden=true;
  search.setAttribute('aria-describedby',searchStatus.id);
  searchWrap.append(searchLabel,searchRow,results,searchStatus);
  nav?.before(searchWrap);
  let searchExpanded=null;
  let pendingSource=null;
  const fold=text=>String(text||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
  function selectSource(id){
    pendingSource=id;state.mode='all';state.page=1;
    // Route before applying the existing source selector, since route changes reset it.
    if(location.hash==='#noticias'){goTo('all');applyPendingSource();}
    else goTo('all');
  }
  function applyPendingSource(){
    if(!pendingSource)return;
    const id=pendingSource;pendingSource=null;
    if(!state.sources.some(source=>source.id===id&&!state.hiddenSources.has(id)))return;
    state.feed=id;fillSelect();render();
    get('feedHeading')?.focus({preventScroll:true});
  }
  window.addEventListener('hashchange',applyPendingSource);
  function filterNavigation(){
    if(!nav)return;
    const query=fold(search.value.trim());
    clearSearch.hidden=!query;
    const toggle=get('sourceFoldersToggle');
    if(query&&searchExpanded===null){
      searchExpanded=!nav.hidden;
      if(nav.hidden)toggle?.click();
    }else if(!query&&searchExpanded!==null){
      const restore=searchExpanded;searchExpanded=null;
      if(nav.hidden===restore)toggle?.click();
    }
    let folders=0;
    for(const row of nav.querySelectorAll(':scope > .folder-entry')){
      const ownName=row.querySelector('.nav-label')?.textContent||'';
      const matches=!query||fold(ownName).includes(query);
      row.classList.toggle('experience-search-hidden',!matches);
      if(matches&&!row.hidden)folders+=1;
    }
    results.replaceChildren();results.hidden=!query;
    searchStatus.hidden=!query;
    if(!query)return;
    const sources=state.sources.filter(source=>!state.hiddenSources.has(source.id)&&fold(source.name).includes(query));
    for(const source of sources.slice(0,30)){
      const button=mk('button','experience-source-result');button.type='button';
      button.dataset.sourceId=source.id;
      button.append(mk('span','',sourceLabel(source.name)),mk('small','','Ver noticias'));
      button.addEventListener('click',()=>selectSource(source.id));results.append(button);
    }
    searchStatus.textContent=folders+' '+(folders===1?'carpeta':'carpetas')+' · '+sources.length+' '+(sources.length===1?'fuente':'fuentes')+(sources.length>30?' · Se muestran 30 fuentes. Afina la búsqueda.':'');
  }
  search.addEventListener('input',filterNavigation);
  clearSearch.addEventListener('click',()=>{search.value='';filterNavigation();search.focus({preventScroll:true});});
  search.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&search.value){event.preventDefault();event.stopPropagation();clearSearch.click();}
  });
  function togglePinned(value,button){
    const pinned=getPinnedDestinations();
    const next=pinned.includes(value)?pinned.filter(item=>item!==value):[...pinned,value];
    if(next.length>25){actionToast('Puedes fijar hasta 25 carpetas.');return;}
    try{storePreferences({pinnedDestinations:next});}
    catch{actionToast('No se pudieron guardar los favoritos. Revisa el espacio de este navegador.');return;}
    decorateNavigation();button.focus({preventScroll:true});
    window.dispatchEvent(new Event('radar-experience-changed'));
  }
  function decorateNavigation(){
    if(!nav)return;
    const currentGroups=groups(),pinned=new Set(getPinnedDestinations());
    const rows=[...nav.querySelectorAll(':scope > .folder-entry')];
    for(const row of rows){
      const link=row.querySelector('.nav-link');
      const group=link?.dataset.destination?currentGroups.find(group=>group.key==='default:'+link.dataset.destination):
        currentGroups.find(group=>group.key==='manual:'+link?.querySelector('.nav-label')?.textContent);
      if(!group)continue;
      const value=destination(group);
      let pin=row.querySelector('.experience-pin');
      if(!pin){
        pin=mk('button','experience-pin');pin.type='button';
        pin.addEventListener('click',event=>{event.stopPropagation();togglePinned(pin.dataset.destination,pin);});
        row.append(pin);
      }
      pin.dataset.destination=value;
      const selected=pinned.has(value);
      pin.textContent=selected?'Fijada':'Fijar';pin.setAttribute('aria-pressed',String(selected));
      const label=(selected?'Desfijar carpeta: ':'Fijar carpeta: ')+group.name;
      pin.title=label;pin.setAttribute('aria-label',label);
      row.classList.toggle('experience-pinned',selected);
    }
    // Move existing nodes, retaining their listeners, menus and current navigation.
    const sorted=[...rows].sort((a,b)=>Number(b.classList.contains('experience-pinned'))-Number(a.classList.contains('experience-pinned')));
    sorted.forEach((row,index)=>{if(nav.children[index]!==row)nav.insertBefore(row,nav.children[index]||null);});
    filterNavigation();
  }
  let navigationFrame=0;
  function scheduleNavigation(){
    if(navigationFrame)return;
    navigationFrame=requestAnimationFrame(()=>{navigationFrame=0;decorateNavigation();});
  }
  // Library read counters can replace manual rows independently of a full render.
  if(nav)new MutationObserver(scheduleNavigation).observe(nav,{childList:true});
  const baseBuildNav=buildNav;
  buildNav=function(...args){const result=baseBuildNav.apply(this,args);decorateNavigation();return result;};
  const baseRender=render;
  render=function(...args){const result=baseRender.apply(this,args);syncProfile();syncColumns();decorateNavigation();return result;};
  const baseMarkRead=markRead;
  markRead=function(...args){
    const result=baseMarkRead.apply(this,args);
    for(const node of document.querySelectorAll('.article-card')){
      const label=node.querySelector('.article-read-toggle .experience-action-label');
      if(label)label.textContent=state.read.has(node.dataset.articleId)?'Sin leer':'Marcar leída';
    }
    return result;
  };
  let columnFrame=0;
  const scheduleColumns=()=>{if(!columnFrame)columnFrame=requestAnimationFrame(()=>{columnFrame=0;syncColumns();});};
  if(typeof ResizeObserver!=='undefined'){
    const observer=new ResizeObserver(scheduleColumns);
    observer.observe(get('articleGrid'));
    const header=document.querySelector('.topbar');if(header)observer.observe(header);
  }
  window.addEventListener('resize',scheduleColumns,{passive:true});
  window.addEventListener('radar-sidebar-visibility-change',scheduleColumns);
  window.addEventListener('radar-preferences-imported',()=>{syncProfile();syncColumns();decorateNavigation();});
  window.addEventListener('storage',event=>{if(event.key===KEY){preferences=read();decorateNavigation();}});
  syncProfile();syncColumns();decorateNavigation();
})();
