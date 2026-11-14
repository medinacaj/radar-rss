'use strict';
// Execute the real enhancement in a small DOM; exercise outcomes and existing nodes.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
class Element {
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.parentNode=null;this.attributes={};this.dataset={};this.listeners={};this.hidden=false;this.open=false;this.value='';this._text='';this.className='';}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  set textContent(value){this._text=String(value);this.children.forEach(x=>x.parentNode=null);this.children=[];}
  get classList(){return {contains:c=>this.className.split(/\s+/).includes(c),add:(...cs)=>{this.className=[...new Set([...this.className.split(/\s+/).filter(Boolean),...cs])].join(' ');},remove:(...cs)=>{this.className=this.className.split(/\s+/).filter(c=>!cs.includes(c)).join(' ');},toggle:(c,on)=>{if(on===undefined)on=!this.classList.contains(c);if(on)this.classList.add(c);else this.classList.remove(c);return on;}};}
  append(...nodes){for(const node of nodes){node.remove();node.parentNode=this;this.children.push(node);}}
  prepend(node){this.insertBefore(node,this.children[0]);}
  insertBefore(node,before){if(!before)return this.append(node);node.remove();const i=this.children.indexOf(before);assert.ok(i>=0);node.parentNode=this;this.children.splice(i,0,node);}
  after(node){this.parentNode.insertBefore(node,this.parentNode.children[this.parentNode.children.indexOf(this)+1]);}
  before(node){this.parentNode.insertBefore(node,this);}
  remove(){if(this.parentNode){this.parentNode.children.splice(this.parentNode.children.indexOf(this),1);this.parentNode=null;}}
  replaceChildren(...nodes){this.textContent='';this.append(...nodes);}
  setAttribute(k,v){this.attributes[k]=String(v);}
  getAttribute(k){return this.attributes[k];}
  addEventListener(name,handler){(this.listeners[name]??=[]).push(handler);}
  dispatch(name,event={}){for(const fn of this.listeners[name]||[])fn({target:this,preventDefault(){},stopPropagation(){},...event});}
  click(){this.dispatch('click');}
  focus(){document.activeElement=this;}
  scrollIntoView(){}
  showModal(){this.open=true;}
  close(){this.open=false;this.dispatch("close");}
  matches(selector){if(selector==='[data-settings-pane="reading"]')return this.dataset.settingsPane==='reading';const attr=selector.match(/^\[data-(mode|destination)="([^"]+)"\]$/);if(attr)return this.dataset[attr[1]]===attr[2];if(selector.startsWith('#'))return this.id===selector.slice(1);if(selector.startsWith('.'))return this.classList.contains(selector.slice(1));return this.tagName.toLowerCase()===selector;}
  closest(selector){return this.matches(selector)?this:this.parentNode?.closest(selector);}
  querySelectorAll(selector){const selectors=selector.split(',').map(x=>x.trim());return this.children.flatMap(node=>[...(selectors.some(s=>node.matches(s))?[node]:[]),...node.querySelectorAll(selector)]);}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  contains(node){return node===this||this.children.some(child=>child.contains(node));}
}
const body=new Element('body');
const document={body,activeElement:null,createElement:tag=>new Element(tag),getElementById:id=>body.querySelector('#'+id),querySelector:selector=>body.querySelector(selector),addEventListener(){}};
const node=(tag,id,cls,text='')=>{const el=new Element(tag);el.id=id;el.className=cls||'';el.textContent=text;return el;};
const header=node('header',null,'topbar'),actions=node('div',null,'topbar-actions');
const tools=node('div','topbarTools','topbar-tools');actions.append(tools);
header.append(node('div',null,'topbar-caption'),actions);body.append(header);
const navigation=node('div','sidebarNavigation'),coreSection=node('section','sidebarCoreSection'),sidebar=node('div','sidebarCoreContent');
const primaryNav=node('nav','categoryNav');
for(const destination of ['home','all','agenda']){const button=node('button',null,'nav-link',destination);button.dataset.destination=destination;primaryNav.append(button);}
sidebar.append(primaryNav);coreSection.append(sidebar);navigation.append(coreSection);body.append(navigation);
const feed=node('section','feedView');body.append(feed);
const sectionHeading=node('div',null,'section-heading sr-only'),heading=node('h1','feedHeading',null,'Todas las noticias');sectionHeading.append(heading);feed.append(sectionHeading);
const modes=node('div',null,'mode-tabs');
const modeButtons={};
for(const [mode,label] of [['all','Todas'],['unread','Sin leer'],['saved','Guardadas']]){
  const button=node('button',null,'mode-tab',label),count=node('span',mode+'Count','mode-tab-count','0');
  button.dataset.mode=mode;button.append(count);modes.append(button);modeButtons[mode]=button;
}
const bar=node('div',null,'filter-bar'),controls=node('div',null,'filter-controls');bar.append(modes,controls);feed.append(bar);
const source=node('label',null,'source-filter'),sourceSelect=node('select','sourceSelect');source.append(sourceSelect);
const tag=node('label',null,'library-tag-filter-wrap'),tagSelect=node('select','libraryTagFilter');tag.append(tagSelect);
const display=node('div',null,'display-controls');
const advanced=node('details','feedAdvanced','feed-advanced'),advancedContent=node('div',null,'feed-advanced-content');advanced.append(node('summary',null,null,'Más opciones'),advancedContent);
advancedContent.append(node('select','v12Date'),node('button','v12SaveSearch'),node('button','markAllVisible'));
controls.append(source,tag,display,advanced);
const grid=node('div','articleGrid'),search=node('input','searchInput'),contextNode=node('div','feedContext');
const onlyNew=node('span','onlyNewChip'),followTopic=node('button','followTopic');followTopic.hidden=true;contextNode.append(onlyNew,followTopic);
feed.append(grid,contextNode);body.append(search);
const reading=node('section');reading.dataset.settingsPane='reading';
const settings=node('dialog','settingsDialog');settings.append(reading);settings.showModal=()=>{settings.open=true;};
for(const id of ['settingAge','settingHideRead','settingKeywords','settingsSourceSearch'])settings.append(node('input',id));body.append(settings);
const windowListeners={};
const window={innerWidth:1440,addEventListener(name,fn,options){(windowListeners[name]??=[]).push({fn,once:options?.once});},emit(name,event={}){const list=(windowListeners[name]||[]).slice();windowListeners[name]=(windowListeners[name]||[]).filter(x=>!x.once);list.forEach(x=>x.fn(event));}};
const state={pageView:'feed',category:'all',feed:'',search:'',maxAge:0,mode:'all',density:'comfortable',hideRead:false,mutedKeywords:'',hiddenSources:new Set(),onlyNew:false,page:1,sources:[{id:'s1',name:'Medio Uno'}],items:[{id:'a'}],saved:new Set(),historyLoading:false};
let privateFolder=null,privateTag='',geo='all',settingsTab='',renderCount=0;
const prefWrites=[];let displayChanges=0;
window.RadarLibrary={getFeedFilters:()=>({folder:privateFolder,tag:privateTag}),clearTagFilter(){privateTag='';tagSelect.value='';}};
window.RadarV12={getFeedGeo:()=>({id:geo,label:'Latinoamérica'})};
const location={hash:'#noticias'};
const context={window,document,state,location,console,mk:(tag,cls,text)=>node(tag,null,cls,text),sourceLabel:x=>x,categoryLabel:x=>x,
  storeGet:()=>null,svgIcon:name=>node('svg',null,'ui-icon',name),
  savePref:(k,v)=>prefWrites.push([k,v]),selectedTab:name=>{settingsTab=name;},
  syncSettings(){},applyDisplaySettings(){displayChanges++;},goTo(){privateFolder=null;geo='all';state.category='all';state.feed='';location.hash='#noticias';context.render();window.emit('hashchange');},
  fillSelect(){sourceSelect.value=state.feed;},hasHistory:()=>false,newsCountsUnavailable:()=>false,
  emptyState:()=>node('div',null,'empty-state','Existing loading state'),
  render(){renderCount++;grid.replaceChildren(context.emptyState([]));},applyFilters:()=>[]};
const scriptPath=path.join(__dirname,'../web/feed-ux.js');
vm.runInNewContext(fs.existsSync(scriptPath)?fs.readFileSync(scriptPath,'utf8'):'',context,{filename:'feed-ux.js'});
const get=id=>document.getElementById(id);
const chip=name=>get('feedFilterChips')?.querySelectorAll('button').find(el=>el.dataset.filter===name);
const refresh=()=>context.render();
assert.equal(heading.parentNode,sectionHeading);assert.equal(sectionHeading.classList.contains('sr-only'),true);
assert.ok(sidebar.contains(modes),'reading modes are moved inside Principal');
assert.equal(modes.parentNode,primaryNav,'reading shortcuts share the one main navigation');
assert.equal(modes.id,'sidebarReadingModes');
assert.deepEqual(primaryNav.children.map(el=>el.dataset.destination||el.id),['home','all','sidebarReadingModes','agenda']);
assert.equal(modeButtons.all.hidden,true,'Noticias replaces duplicate Todas');
assert.equal(modeButtons.all.getAttribute('aria-hidden'),'true');
assert.equal(modeButtons.unread.classList.contains('nav-link'),true);
assert.equal(modeButtons.saved.classList.contains('nav-link'),true);
assert.equal(modeButtons.unread.querySelector('.mode-tab-count').id,'unreadCount','preserves article counter');
assert.ok(tools.contains(get('feedHeaderControls')),'the only source controls live in the topbar popup');
assert.ok(tools.contains(get('presentationControl')),'the single presentation control lives in the topbar');
assert.ok(!navigation.contains(get('feedHeaderControls')),'sidebar has no duplicated filters');
assert.ok(!navigation.contains(get('presentationControl')),'sidebar has no duplicated view controls');
assert.ok(!bar.contains(get('feedHeaderControls')),'no duplicated toolbar above the news');
assert.equal(get('sidebarFeedOptions').open,false,'filter popup starts closed');
assert.ok(tools.contains(get('feedFiltersToggle')),'mobile filter button lives in topbar');
assert.ok(tools.contains(get('feedViewToggle')),'mobile view button lives in topbar');
assert.ok(tools.contains(get('feedDensityToggle')),'view controls reuse original node');
assert.match(get('sidebarFeedOptions').querySelector('summary').textContent,/Filtros/);
assert.equal(get('topbarFilterCount').hidden,true,'no misleading filter count on a fresh page');
assert.match(get('presentationSummary').textContent,/Vista/);
assert.equal(navigation.querySelector('.sidebar-reading'),null,'redundant Herramientas sidebar group is removed');
assert.ok(get('feedActiveFilters'),'filter state remains available internally');
assert.equal(get('feedActiveFilters').hidden,true,'no active-filter band is rendered above news');
assert.equal(get('feedActiveFilters').getAttribute('aria-hidden'),'true');
assert.equal(get('sidebarReadingToggle'),null,'no old accordion toolbar remains');
assert.equal(get('sidebarReadingContent'),null,'no empty side panel remains');
assert.equal(get('sidebarFeedOptions').parentNode,tools);
assert.equal(get('presentationControl').parentNode,tools);
assert.equal(get('feedClearFilters').parentNode.className,'sidebar-feed-options-body');
get('sidebarFeedOptions').open=true;
get('sidebarFeedOptions').querySelector('.sidebar-feed-options-body').dispatch('change',{target:sourceSelect});
assert.equal(get('sidebarFeedOptions').open,false,'choosing a source closes its topbar popup');
assert.equal(get('feedDensityToggle').getAttribute('aria-pressed'),'false');
get('feedDensityToggle').click();
assert.equal(state.density,'compact');assert.equal(get('feedDensityToggle').getAttribute('aria-pressed'),'true');
assert.ok(prefWrites.some(([key,value])=>key==='density'&&value==='compact'));
get('feedDensityToggle').click();
assert.equal(state.density,'comfortable');assert.equal(get('feedDensityToggle').getAttribute('aria-pressed'),'false');
assert.equal(displayChanges,2,'both density choices immediately refresh the layout');
assert.equal(get('feedActiveFilters').hidden,true,'no empty toolbar when nothing filters');
state.search='energía';state.feed='s1';state.maxAge=7;state.mode='unread';state.hideRead=true;
state.hiddenSources.add('s2');state.mutedKeywords='política';privateFolder={id:'Lectura',label:'Lectura',kind:'manual'};privateTag='Informe';
refresh();
assert.equal(get('feedActiveFilters').hidden,true,'active filters do not occupy a content row');
assert.equal(get('topbarFilterCount').hidden,false,'toolbar indicates active filters');
assert.match(get('sidebarFeedOptions').querySelector('summary').getAttribute('aria-label'),/filtros activos/);
assert.equal(get('feedClearFilters').hidden,false,'clear filters remains in the topbar popup');
for(const key of ['search','source','age','mode','folder','tag','hide-read','hidden-sources','keywords'])assert.ok(chip(key),'chip for '+key);
assert.match(chip('source').textContent,/Medio Uno/);
chip('source').click();assert.equal(state.feed,'');assert.equal(state.search,'energía');
chip('tag').click();assert.equal(privateTag,'');assert.equal(privateFolder.label,'Lectura');
chip('keywords').click();assert.equal(settingsTab,'reading');assert.equal(settings.open,true);assert.equal(document.activeElement,get('settingKeywords'));
assert.equal(state.mutedKeywords,'política','opening preferences never erases them');
state.feed='s1';privateTag='Informe';state.onlyNew=true;refresh();
get('feedClearFilters').click();
assert.equal(state.search,'');assert.equal(state.feed,'');assert.equal(state.maxAge,0);assert.equal(state.mode,'all');assert.equal(state.onlyNew,false);assert.equal(privateTag,'');assert.equal(privateFolder,null);
assert.equal(state.hideRead,true);assert.equal(state.mutedKeywords,'política');assert.equal(state.hiddenSources.has('s2'),true,'bulk reset preserves explicit global preferences');
assert.match(get('feedActiveFilters').textContent,/Conserva/);
assert.ok(prefWrites.some(([key,value])=>key==='max-age'&&value===0),'date setting is synchronized');
state.hideRead=false;state.mutedKeywords='';state.hiddenSources.clear();state.mode='saved';refresh();
assert.match(grid.textContent,/Aún no tienes noticias guardadas/);
assert.match(grid.textContent,/guardar/i);
assert.equal(grid.querySelectorAll('button')[0].textContent,'Ver todas las noticias');
state.mode='all';state.maxAge=7;refresh();
assert.match(grid.textContent,/Ampliar antigüedad/);grid.querySelectorAll('button')[0].click();assert.equal(state.maxAge,0);
state.search='sin coincidencia';privateFolder={id:'Lectura',label:'Lectura',kind:'manual'};state.feed='s1';location.hash='#carpeta/Lectura';refresh();
assert.match(grid.textContent,/Buscar en todas las secciones/);grid.querySelectorAll('button')[0].click();
assert.equal(privateFolder,null);assert.equal(state.search,'sin coincidencia');assert.equal(state.feed,'s1','broadening scope retains source selection');
// Existing listeners and node identities survive mobile placement and desktop restoration.
let sourceChanges=0;sourceSelect.addEventListener('change',()=>sourceChanges++);
window.innerWidth=390;window.emit('resize');
assert.equal(get('feedViewToggle').hidden,false,'mobile View button is visible');
assert.equal(get('feedFiltersToggle').hidden,false);assert.equal(get('sidebarFeedOptions').hidden,true);assert.equal(source.parentNode,get('feedFilterFields'));assert.equal(tag.parentNode,get('feedFilterFields'));assert.equal(display.closest('#presentationControl').parentNode,get('feedFilterFields'));assert.equal(advanced.parentNode,null);
assert.equal(get('feedFilterPanel').hidden,true);get('feedFiltersToggle').click();
assert.equal(get('feedFilterPanel').hidden,false);assert.equal(get('feedFiltersToggle').getAttribute('aria-expanded'),'true');assert.equal(get('feedDensityToggle').parentNode,get('feedFilterFields'));assert.equal(get('feedClearFilters').parentNode,get('feedFilterFields'));assert.equal(get('v12Date').closest('.settings-feed-actions').parentNode,reading);
sourceSelect.dispatch('change');assert.equal(sourceChanges,1);
get('feedFilterPanel').dispatch('keydown',{key:'Escape'});assert.equal(get('feedFilterPanel').hidden,true);assert.equal(document.activeElement,get('feedFiltersToggle'));
window.innerWidth=1440;window.emit('resize');
assert.equal(get('feedViewToggle').hidden,true,'desktop uses Vista disclosure rather than mobile button');
assert.equal(source.parentNode,get('feedHeaderControls'));
assert.equal(display.closest('#presentationControl').parentNode,tools);
assert.equal(tag.parentNode.className,'sidebar-feed-options-body');
assert.equal(get('feedDensityToggle').parentNode.className,'presentation-controls-body');
assert.equal(get('feedClearFilters').parentNode.className,'sidebar-feed-options-body');
assert.equal(get('sidebarFeedOptions').hidden,false);
assert.equal(get('presentationControl').hidden,false);
assert.equal(advanced.parentNode,null);
for(const pageView of ['dashboard','briefing','agenda']){
  state.pageView=pageView;refresh();
  assert.equal(get('sidebarFeedOptions').parentNode,tools,`filters are in topbar on ${pageView}`);
  assert.equal(get('feedHeaderControls').hidden,false,`filters remain available on ${pageView}`);
  assert.equal(get('sidebarFeedOptions').hidden,false,`filter disclosure remains available on ${pageView}`);
  assert.equal(get('presentationControl').hidden,false,`presentation disclosure remains available on ${pageView}`);
  assert.equal(get('feedFiltersToggle').hidden,true,'desktop mobile-only filter button stays hidden');
}
assert.equal(navigation.querySelector('.sidebar-reading'),null,'Tools does not occupy sidebar navigation');
window.innerWidth=390;window.emit('resize');
assert.equal(get('feedFiltersToggle').hidden,false,'mobile filters remain available on Inicio and other pages');
state.pageView='dashboard';refresh();
get('feedFiltersToggle').click();
assert.equal(get('feedFilterPanel').hidden,false,'mobile filter sheet opens from Inicio');
get('feedFiltersDone').click();
assert.equal(get('feedFilterPanel').hidden,true);
get('feedViewToggle').click();
assert.equal(get('feedFilterPanel').hidden,false,'mobile view sheet opens from Inicio');
assert.equal(get('feedViewToggle').getAttribute('aria-expanded'),'true');
assert.equal(document.activeElement,get('presentationSummary'),'view button focuses view controls');
get('feedFiltersDone').click();
assert.equal(get('feedFilterPanel').hidden,true);
window.innerWidth=1440;window.emit('resize');
state.pageView='feed';refresh();assert.equal(get('feedHeaderControls').hidden,false);
assert.equal(get('feedFiltersToggle').hidden,true);sourceSelect.dispatch('change');assert.equal(sourceChanges,2);
assert.ok(renderCount>0);
console.log('Feed UX verified: filter chips, scoped reset, contextual empty recovery, mobile controls and desktop restoration.');
