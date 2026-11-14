"use strict";
/* Visible, reversible feed filters. Preferences stay local to this browser. */
(() => {
  const feed=document.getElementById('feedView');
  const bar=feed?.querySelector('.filter-bar');
  const controls=feed?.querySelector('.filter-controls');
  if(!bar||!controls||document.getElementById('feedActiveFilters'))return;
  const get=id=>document.getElementById(id);
  const region=mk('div','feed-active-filters');region.id='feedActiveFilters';
  // Legacy chip nodes remain available to extensions, but never duplicate
  // the sidebar controls or create an extra row above the news.
  region.hidden=true;region.setAttribute('aria-hidden','true');
  const chips=mk('div','feed-filter-chips');chips.id='feedFilterChips';
  const clear=mk('button','feed-clear-filters','Limpiar filtros');clear.id='feedClearFilters';clear.type='button';
  clear.title='Quitar búsqueda, fuente, fecha, estado, carpeta, región, etiqueta y solo nuevas. Conserva las preferencias de lectura.';
  const scope=mk('p','feed-filter-scope','Conserva las preferencias: ocultar leídas, fuentes ocultas y palabras silenciadas.');
  scope.id='feedFilterScope';clear.setAttribute('aria-describedby',scope.id);
  region.append(chips,scope);bar.after(region);

  const library=()=>window.RadarLibrary?.getFeedFilters()||{folder:null,tag:''};
  const geo=()=>window.RadarV12?.getFeedGeo()||{id:'all',label:''};
  const hasScope=()=>Boolean(library().folder||state.category!=='all'||geo().id!=='all');
  function refresh(focus=false){
    state.page=1;render();
    if(focus){
      const target=window.innerWidth<=640
        ? (panel.open?get('feedFiltersDone'):get('feedFiltersToggle'))
        : optionsSummary;
      target?.focus({preventScroll:true});
    }
  }
  function clearSearch(){state.search='';get('searchInput').value='';}
  function clearAge(){state.maxAge=0;savePref('max-age',0);if(get('settingAge'))get('settingAge').value='0';if(get('v12Date'))get('v12Date').value='0';}
  function openPreference(tab,id){
    syncSettings();selectedTab(tab);
    const dialog=get('settingsDialog');if(dialog&&!dialog.open)dialog.showModal();
    get(id)?.scrollIntoView({block:'nearest',behavior:'auto'});get(id)?.focus({preventScroll:true});
  }
  function clearScope(preserveSource=true){
    const source=preserveSource?state.feed:'';
    const restore=()=>{state.feed=source;fillSelect();refresh();};
    if(location.hash==='#noticias'){goTo('all');restore();}
    else {window.addEventListener('hashchange',restore,{once:true});goTo('all');}
  }
  function clearFilters(){
    const scoped=hasScope();
    clearSearch();state.feed='';get('sourceSelect').value='';clearAge();state.mode='all';state.onlyNew=false;
    window.RadarLibrary?.clearTagFilter();
    if(scoped)clearScope(false);else refresh(true);
  }
  clear.addEventListener('click',clearFilters);
  function filters(){
    const active=[];
    const add=(id,label,remove,preference=false)=>active.push({id,label,remove,preference});
    if(state.search.trim())add('search','Búsqueda: '+state.search.trim(),()=>{clearSearch();refresh(true);});
    if(state.feed){const source=state.sources.find(item=>item.id===state.feed);add('source','Fuente: '+sourceLabel(source?.name||state.feed),()=>{state.feed='';get('sourceSelect').value='';refresh(true);});}
    if(state.maxAge&&state.mode!=='saved')add('age',state.maxAge===1?'Últimas 24 horas':'Últimos '+state.maxAge+' días',()=>{clearAge();refresh(true);});
    if(state.mode!=='all')add('mode',state.mode==='saved'?'Guardadas':'Sin leer',()=>{state.mode='all';refresh(true);});
    const current=library();
    if(current.folder)add('folder','Carpeta: '+current.folder.label,()=>clearScope());
    else if(state.category!=='all')add('folder','Carpeta: '+categoryLabel(state.category),()=>clearScope());
    const place=geo();if(place.id!=='all')add('region','Región: '+place.label,()=>clearScope());
    if(current.tag)add('tag','Etiqueta: '+current.tag,()=>{window.RadarLibrary?.clearTagFilter();refresh(true);});
    if(state.onlyNew)add('only-new','Solo nuevas desde tu visita',()=>{state.onlyNew=false;refresh(true);});
    if(state.hideRead&&state.mode!=='saved')add('hide-read','Ocultar leídas',()=>openPreference('reading','settingHideRead'),true);
    if(state.hiddenSources.size&&state.mode!=='saved')add('hidden-sources',state.hiddenSources.size+' fuentes ocultas',()=>openPreference('sources','settingsSourceSearch'),true);
    if(state.mutedKeywords.split(',').some(word=>word.trim().length>1))add('keywords','Palabras silenciadas',()=>openPreference('reading','settingKeywords'),true);
    return active;
  }

  // One set of controls: compact sidebar disclosure on desktop, existing sheet on mobile.
  const headerControls=mk('div','feed-header-controls');headerControls.id='feedHeaderControls';
  headerControls.setAttribute('role','group');headerControls.setAttribute('aria-label','Fuentes y presentación de noticias');
  const sidebar=get('sidebarCoreContent');
  const coreSection=get('sidebarCoreSection');
  const primaryNav=get('categoryNav');
  const modes=feed.querySelector('.mode-tabs');
  // One navigation: Noticias already opens "Todas"; only unread/saved need links.
  if(primaryNav&&modes){
    modes.id='sidebarReadingModes';
    const allMode=modes.querySelector('[data-mode="all"]');
    if(allMode){allMode.hidden=true;allMode.setAttribute('aria-hidden','true');allMode.tabIndex=-1;}
    for(const mode of ['unread','saved']){
      const button=modes.querySelector('[data-mode="'+mode+'"]');
      if(!button)continue;
      const count=button.querySelector('.mode-tab-count');
      const label=mode==='unread'?'Sin leer':'Guardadas';
      const glyph=mk('span','nav-glyph');glyph.append(svgIcon(mode==='unread'?'mail':'bookmark'));
      const left=mk('span','nav-left');left.append(glyph,mk('span','nav-label',label));
      button.classList.add('nav-link','reader-mode-link');
      if(count){count.classList.add('nav-count');button.replaceChildren(left,count);}
      else button.replaceChildren(left);
    }
    primaryNav.insertBefore(modes,primaryNav.querySelector('[data-destination="agenda"]'));
  }
  const readingNav=mk('section','sidebar-reading sidebar-tools');
  readingNav.setAttribute('aria-labelledby','sidebarReadingHeading');
  const readingHead=mk('h3','sidebar-reading-title');readingHead.id='sidebarReadingHeading';
  const readingToggle=mk('button','sidebar-section-toggle sidebar-reading-toggle');
  readingToggle.type='button';readingToggle.id='sidebarReadingToggle';
  readingToggle.setAttribute('aria-controls','sidebarReadingContent');
  const readingTitle=mk('span','','HERRAMIENTAS');
  const readingChevron=mk('span','sidebar-section-chevron');
  readingChevron.setAttribute('aria-hidden','true');
  readingToggle.append(readingTitle,readingChevron);
  readingHead.append(readingToggle);
  const readingContent=mk('div','sidebar-reading-content');readingContent.id='sidebarReadingContent';
  const setReadingExpanded=value=>{
    readingContent.hidden=!value;
    readingToggle.setAttribute('aria-expanded',String(value));
    readingToggle.setAttribute('aria-label',value?'Contraer herramientas':'Expandir herramientas');
  };
  // Tools must remain discoverable even on Inicio, Resumen and Agenda.
  // Respect an explicit collapse; otherwise show the available actions by default.
  const savedReadingOpen=typeof storeGet==='function'?storeGet('radar-tools-open'):null;
  let narrowTools=window.innerWidth<=640;
  setReadingExpanded(narrowTools||savedReadingOpen!=='false');
  window.addEventListener('resize',()=>{
    const narrow=window.innerWidth<=640;
    if(narrow===narrowTools)return;
    narrowTools=narrow;
    setReadingExpanded(narrow||storeGet('radar-tools-open')!=='false');
  });
  readingToggle.addEventListener('click',()=>{
    const expanded=readingContent.hidden;
    setReadingExpanded(expanded);
    savePref('tools-open',expanded);
  });
  readingNav.append(readingHead,readingContent);
  if(sidebar){
    // Folders stay immediately after Principal; tools follow, with no repeated reading links.
    get('sidebarNavigation')?.append(readingNav);
  }
  if(modes){
    modes.addEventListener('click',event=>{
      const button=event.target.closest('.mode-tab');
      if(!button)return;
      if(window.location.hash!=='#noticias')goTo('all');
      if(window.innerWidth<=950)setNavOpen(false);
    });
  }
  const options=mk('details','sidebar-feed-options');options.id='sidebarFeedOptions';
  const optionsSummary=mk('summary','','Filtrar noticias');
  optionsSummary.setAttribute('aria-label','Mostrar filtros de noticias');
  const optionsBody=mk('div','sidebar-feed-options-body');
  options.append(optionsSummary,optionsBody);
  optionsBody.append(headerControls);
  readingContent.append(options);
  const source=get('sourceSelect')?.closest('label');
  const display=controls.querySelector('.display-controls');
  const presentation=mk('details','presentation-control');presentation.id='presentationControl';
  const presentationSummary=mk('summary','','Vista y columnas');presentationSummary.id='presentationSummary';
  const presentationBody=mk('div','presentation-controls-body');
  presentation.append(presentationSummary,presentationBody);
  if(source)headerControls.append(source);
  if(display){presentationBody.append(display);readingContent.append(presentation);}
  presentation.addEventListener('keydown',event=>{
    if(window.innerWidth>640&&event.key==='Escape'&&presentation.open){event.preventDefault();event.stopPropagation();closeColumnsMenu(false);presentation.open=false;presentationSummary.focus();}
  });
  // Close after the target's click; pointerdown would collapse this inline menu
  // before pointerup and make buttons further down the sidebar miss activation.
  document.addEventListener('click',event=>{
    if(presentation.open&&!presentation.contains(event.target)&&window.innerWidth>640)presentation.open=false;
  });
  const advanced=get('feedAdvanced');
  const reading=document.querySelector('[data-settings-pane="reading"]');
  if(advanced&&reading){
    const section=mk('section','settings-feed-actions');
    section.append(mk('h4','','Filtros y acciones de noticias'));
    const content=advanced.querySelector('.feed-advanced-content');
    if(content)section.append(...content.children);
    reading.prepend(section);advanced.remove();
  }

  const toggle=mk('button','feed-filters-toggle');toggle.id='feedFiltersToggle';toggle.type='button';
  toggle.setAttribute('aria-controls','feedFilterPanel');toggle.setAttribute('aria-expanded','false');
  const toggleLabel=mk('span','','Filtros');
  const count=mk('span','feed-filters-count');count.id='feedFiltersCount';toggle.append(toggleLabel,count);
  const panel=mk('dialog','feed-filter-panel');panel.id='feedFilterPanel';panel.hidden=true;
  panel.setAttribute('aria-labelledby','feedFiltersTitle');
  const panelHead=mk('div','feed-sheet-head'),panelTitle=mk('h2','','Filtros de noticias');panelTitle.id='feedFiltersTitle';
  const panelClose=mk('button','feed-sheet-close','Cerrar');panelClose.id='feedFiltersClose';panelClose.type='button';
  panelClose.setAttribute('aria-label','Cerrar filtros');panelHead.append(panelTitle,panelClose);
  const fields=mk('div','feed-sheet-fields');fields.id='feedFilterFields';
  const done=mk('button','feed-sheet-done','Ver noticias');done.id='feedFiltersDone';done.type='button';
  panel.append(panelHead,fields,done);
  readingContent.append(toggle);document.body.append(panel);
  const densityToggle=mk('button','feed-density-toggle','Compacto');
  densityToggle.id='feedDensityToggle';densityToggle.type='button';
  densityToggle.title='Alternar entre espaciado cómodo y compacto';
  function syncDensity(){
    const compact=state.density==='compact';
    densityToggle.setAttribute('aria-pressed',String(compact));
    densityToggle.setAttribute('aria-label',compact?'Usar espaciado cómodo':'Usar espaciado compacto');
  }
  densityToggle.addEventListener('click',()=>{
    state.density=state.density==='compact'?'comfortable':'compact';
    savePref('density',state.density);
    applyDisplaySettings();syncSettings();render();
  });
  presentationBody.append(densityToggle);
  const tag=get('libraryTagFilter')?.closest('label');
  if(tag)optionsBody.append(tag);
  // Clear stays in the existing filters group, not in a second toolbar.
  optionsBody.append(clear);
  const movable=[source,presentation,tag,densityToggle,clear].filter(Boolean);
  const homes=movable.map(element=>{
    const anchor=mk('span','feed-control-anchor');anchor.hidden=true;element.before(anchor);
    return {element,anchor};
  });
  let mobile=false,expanded=false,desktopAdvancedOpen=Boolean(advanced?.open);
  function setExpanded(value){
    expanded=Boolean(mobile&&value);
    toggle.setAttribute('aria-expanded',String(expanded));
    if(expanded){panel.hidden=false;if(!panel.open){presentation.open=true;panel.showModal();panelClose.focus();}}
    else{if(panel.open)panel.close();panel.hidden=true;}
  }
  panelClose.addEventListener('click',()=>setExpanded(false));
  done.addEventListener('click',()=>setExpanded(false));
  panel.addEventListener('close',()=>{
    if(panel.open)return;
    expanded=false;panel.hidden=true;toggle.setAttribute('aria-expanded','false');
    if(mobile)toggle.focus({preventScroll:true});
  });
  function placeControls(){
    const next=window.innerWidth<=640;
    if(next!==mobile){
      mobile=next;
      if(mobile){
        desktopAdvancedOpen=Boolean(advanced?.open);
        homes.forEach(({element})=>fields.append(element));
        presentation.open=true;
        if(advanced)advanced.open=true;
      }else{
        homes.forEach(({element,anchor})=>anchor.after(element));
        presentation.open=false;
        if(advanced)advanced.open=desktopAdvancedOpen;
        expanded=false;
      }
    }
    // The sidebar is shared by all routes, so never show an empty Tools section.
    options.hidden=mobile;
    presentation.hidden=false;
    toggle.hidden=!mobile;setExpanded(expanded);
  }
  // Keep an empty mobile search field from collapsing between pointerdown
  // and click and moving this control away from the pointer.
  toggle.addEventListener('pointerdown',event=>{if(event.button===0)event.preventDefault();});
  toggle.addEventListener('click',()=>{setExpanded(!expanded);if(!expanded)toggle.focus({preventScroll:true});});
  panel.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&expanded){setExpanded(false);toggle.focus({preventScroll:true});event.stopPropagation();}
  });
  window.addEventListener('resize',placeControls);

  const emptyPrevious=emptyState;
  emptyState=function(...args){
    // Preserve the existing loading and initial-ingestion states.
    if(!state.items.length||state.mode!=='saved'&&(state.historyLoading||newsCountsUnavailable()))return emptyPrevious(...args);
    const el=mk('div','empty-state feed-empty-state');
    const heading=mk('h3','feed-empty-title');
    const hint=mk('p','feed-empty-hint');
    const actions=mk('div','feed-empty-actions');
    const action=(label,callback)=>{const button=mk('button','settings-secondary feed-empty-action',label);button.type='button';button.addEventListener('click',callback);actions.append(button);};
    if(state.mode==='saved'&&!state.saved.size){
      heading.textContent='Aún no tienes noticias guardadas';
      hint.textContent='Usa el botón de guardar de una noticia para encontrarla aquí después.';
      action('Ver todas las noticias',()=>{state.mode='all';clearFilters();});
    }else{
      heading.textContent=state.search.trim()?'Sin resultados para «'+state.search.trim()+'»':state.mode==='saved'?'No hay guardadas con estos filtros':'No hay noticias con estos filtros';
      hint.textContent='Ajusta los filtros activos para ampliar los resultados.';
      if(state.search.trim()&&hasScope())action('Buscar en todas las secciones',()=>clearScope());
      else if(state.search.trim())action('Borrar búsqueda',()=>{clearSearch();refresh(true);get('searchInput').focus({preventScroll:true});});
      else if(state.maxAge&&state.mode!=='saved')action('Ampliar antigüedad',()=>{clearAge();refresh(true);});
      else if(state.feed)action('Ver todas las fuentes',()=>{state.feed='';get('sourceSelect').value='';refresh(true);});
      else if(library().tag)action('Quitar etiqueta',()=>{window.RadarLibrary?.clearTagFilter();refresh(true);});
      else if(state.hideRead&&state.mode!=='saved')action('Mostrar leídas',()=>{state.hideRead=false;state.mode='all';savePref('hide-read',false);if(get('settingHideRead'))get('settingHideRead').checked=false;refresh(true);});
      else if(state.mode==='unread')action('Ver también las leídas',()=>{state.mode='all';refresh(true);});
      else if(state.onlyNew)action('Ver también las anteriores',()=>{state.onlyNew=false;refresh(true);});
      else if(hasScope())action('Ver todas las secciones',()=>clearScope());
      else if(state.hiddenSources.size)action('Revisar fuentes ocultas',()=>openPreference('sources','settingsSourceSearch'));
      else if(state.mutedKeywords.split(',').some(word=>word.trim().length>1))action('Revisar palabras silenciadas',()=>openPreference('reading','settingKeywords'));
      else if(state.mode==='saved')action('Ver todas las noticias',()=>{state.mode='all';refresh(true);});
      else {hint.textContent='Revisa las fuentes disponibles o vuelve después de la próxima actualización.';action('Revisar fuentes',()=>openPreference('sources','settingsSourceSearch'));}
      if(filters().filter(item=>!item.preference).length>1)action('Limpiar filtros',clearFilters);
    }
    el.append(heading,hint,actions);return el;
  };
  function update(){
    headerControls.hidden=false;
    syncDensity();
    readingNav.hidden=false;
    options.hidden=mobile;
    presentation.hidden=false;
    toggle.hidden=!mobile;
    const active=filters();chips.replaceChildren();
    for(const item of active){
      const button=mk('button','feed-filter-chip'+(item.preference?' is-preference':''),item.label+(item.preference?' · Ajustar':' ×'));
      button.type='button';button.dataset.filter=item.id;
      button.setAttribute('aria-label',(item.preference?'Revisar preferencia: ':'Quitar filtro: ')+item.label);
      button.addEventListener('click',item.remove);chips.append(button);
    }
    region.hidden=true;
    clear.hidden=!active.some(item=>!item.preference);
    scope.hidden=!active.some(item=>item.preference);
    count.textContent=String(active.length);count.hidden=!active.length;
    toggle.setAttribute('aria-label','Filtros'+(active.length?' · '+active.length+' activos':''));
    // The new row owns this chip, avoiding a second copy in the old context row.
    const oldNew=get('onlyNewChip');if(oldNew)oldNew.hidden=true;
    const context=get('feedContext'),follow=get('followTopic');if(context&&follow)context.hidden=follow.hidden;
  }
  const renderPrevious=render;
  render=function(...args){const result=renderPrevious(...args);update();return result;};
  placeControls();update();
})();
