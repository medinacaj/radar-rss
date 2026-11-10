'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const sandbox = {window: {}, URL};
vm.runInNewContext(fs.readFileSync('web/editorial-model.js', 'utf8'), sandbox);
const model = sandbox.window.RadarEditorial;
const now = Date.parse('2026-11-09T12:00:00Z');
const title = 'Concepción anuncia nuevas obras para mejorar 12 escuelas de la ciudad';
function item(id, options = {}) {
  return {id, title, url: `https://${id}.example/news`, publisher: id, source: id,
    source_ids: [id], categories: ['07 - Concepción'],
    published_at: '2026-11-09T10:00:00Z', ...options};
}
const plain = value => JSON.parse(JSON.stringify(value));
const originals = [item('a', {content_type: 'news'}), item('b', {title: title.toUpperCase() + '!', content_type: 'opinion'})];
const frozen = JSON.stringify(originals);
const grouped = model.groupStories(originals);
assert.equal(grouped.length, 1, 'same full headline across independent outlets groups');
assert.equal(grouped[0].id, 'a', 'lead identity is stable');
assert.deepEqual(plain(grouped[0].source_ids), ['a', 'b']);
assert.equal(grouped[0].also_in[0].title, originals[1].title);
assert.equal(grouped[0].also_in[0].published_at, originals[1].published_at);
assert.equal(grouped[0].also_in[0].content_type, 'opinion');
assert.equal(grouped[0].coverage, 2);
assert.equal(model.groupStories([item('a'),item('b',{title:title + ' y más'})]).length,1,'neutral publisher suffix preserves known duplicate behavior');
const syndicated = model.groupStories([item('a'),item('radar',{publisher:'a',is_radar:true})]);
assert.equal(syndicated.length,1,'native and syndicated entry for the same outlet coalesce');
assert.equal(syndicated[0].coverage,1,'a second feed is not a second editorial outlet');
assert.equal(model.contentType(grouped[0]), 'news', 'lead retains its own publisher classification');
assert.equal(JSON.stringify(originals), frozen, 'pure API must not mutate input');
for (const other of [
  item('b', {title: title.replace('12', '13')}),
  item('b', {title: title.replace('12', '-12')}),
  item('b', {title: title.replace('anuncia', 'no anuncia')}),
  item('b', {title: title.replace('Concepción', 'Monagas')}),
  item('b', {title: title.replace('anuncia', 'suspende')}),
  item('b', {published_at: '2026-11-07T10:00:00Z'}),
  item('b', {published_at: null, first_seen_at: null}),
  item('b', {source_ids: ['a']}),
  item('b', {publisher: 'a'}),
]) assert.equal(model.groupStories([item('a'), other]).length, 2, 'distinct fact/date/outlet is preserved');
assert.equal(model.groupStories([item('a', {title: 'Chile hoy'}), item('b', {title: 'Chile hoy'})]).length, 2);
const tracked = model.groupStories([item('a'), item('b', {title: 'Un título diferente para la misma URL', url: 'https://a.example/news?utm_source=rss'})]);
assert.equal(tracked.length, 1, 'same original URL may group syndicated feed entries');
const pregrouped = item('a', {coverage: 2, also_in: [{id:'b', url:'https://b.example/news', title, publisher:'b', source_id:'b'}]});
assert.equal(model.groupStories([pregrouped, item('b'), item('c')])[0].also_in.length, 2, 'alternatives are retained once');
const visibleGroup = item('a',{source_ids:['a','b'], summary:'Hidden lead summary',image:'https://a.example/image',
  content_type:'news',categories:['07 - Concepción','08 - Monagas'],coverage:2,
  also_in:[{id:'b',url:'https://b.example/news',title:'El medio visible publica su propio titular de la historia',
    publisher:'Visible publisher',source_id:'b',category:'08 - Monagas',published_at:'2026-11-09T11:00:00Z',content_type:'opinion'}]});
const unmodifiedGroup = JSON.stringify(visibleGroup);
const reselected = model.filterSources([visibleGroup],['a'])[0];
assert.equal(reselected.id,'a','source preference does not discard stable story reading/saved identity');
assert.equal(reselected.publisher,'Visible publisher');
assert.equal(reselected.title,visibleGroup.also_in[0].title);
assert.equal(reselected.content_type,'opinion');
assert.equal(reselected.summary,'','hidden lead text cannot be attributed to its visible alternate');
assert.equal(reselected.image,null);
assert.equal(reselected.coverage,1);
assert(reselected.editorial_member_ids.includes('b'),'visible alternate keeps its own reading identity');
assert.deepEqual(plain(reselected.source_ids),['b']);
assert.deepEqual(plain(reselected.categories),['08 - Monagas']);
assert.deepEqual(plain(reselected.also_in),[]);
const leadOnly = model.filterSources([visibleGroup],['b'])[0];
assert.equal(leadOnly.publisher,'a');
assert.equal(leadOnly.coverage,1);
assert.deepEqual(plain(leadOnly.also_in),[]);
assert.equal(model.filterSources([visibleGroup],['a','b']).length,0);
assert.equal(model.filterSources([item('a',{source_ids:['a','b']})],['a']).length,0,'no alternate metadata means no guessed attribution');
const mutedAlternative = model.filterSources([visibleGroup],[],[],['visible publisher'])[0];
assert.deepEqual(plain(mutedAlternative.also_in),[],'silenced alternative publisher cannot leak through comparison');
assert.equal(mutedAlternative.coverage,1);
assert.equal(model.filterSources([item('a',{coverage:4})],['unrelated'])[0].coverage,4,'unrelated source settings do not erase explicit coverage');
assert.equal(JSON.stringify(visibleGroup),unmodifiedGroup);
assert.equal(model.contentType(item('a', {title:'Opinión: una noticia', source:'ANÁLISIS — Diario'})), 'unknown');
assert.equal(model.contentType(item('a', {content_type:'Opinión'})), 'opinion');
assert.equal(model.contentType(item('a', {content_type:'análisis'})), 'analysis');
assert.equal(model.contentType(item('a', {content_type:'press_release'})), 'press_release');
assert.equal(model.contentType(item('a', {content_type:'text/html'})), 'unknown');
assert.equal(model.contentType(item('a', {content_type:'__proto__'})), 'unknown');
const pool = Array.from({length:16}, (_, i) => item(String(i), {
  title:`Historia distinta sobre avances de la comunidad número ${i}`,
  categories:[['04 - Chile','07 - Concepción','08 - Monagas','02 - Tecnología'][i % 4]],
  published_at:new Date(now - (i + 1) * 3600000).toISOString(),
  coverage: i === 9 ? 3 : 1,
}));
const digest = model.selectDigest(pool, now);
assert.equal(digest.length, 7);
assert.equal(digest[0].id, '9', 'explicit independent coverage is ranked before recency');
assert.equal(new Set(digest.map(x => x.categories[0])).size, 4, 'digest spans available interests');
assert.equal(model.selectDigest([item('old', {published_at:'2026-11-01T00:00:00Z'})], now).length, 0);
assert.equal(model.selectDigest([item('future', {published_at:'2026-11-10T00:00:00Z'})], now).length, 0);
assert.equal(model.selectDigest(pool, now, 5).length, 5);
assert.equal(model.selectDigest(pool, now, 99).length, 7);
const fallback = [...pool.slice(0, 3), item('yesterday', {title:'Otra historia distinta entre las noticias recientes', published_at:'2026-11-07T13:00:00Z'})];
assert.equal(model.selectDigest(fallback, now).length, 4, 'existing 48h fallback never pads with old news');
assert.equal(model.selectDigest([], now).length, 0);
const local = model.selectLocal(pool, ['08 - Monagas'], now);
assert(local.length && local.every(x => x.categories.includes('08 - Monagas')), 'local selection respects supplied interests');
assert.deepEqual(plain(model.selectLocal(pool, [], now)), [], 'explicit empty interests stays empty');
const defaults = model.selectLocal(pool, undefined, now);
assert.equal(new Set(defaults.map(x=>x.categories[0])).size, 3);
assert(defaults.every(x=>/^0[478] -/.test(x.categories[0])));
assert.equal(JSON.stringify(originals), frozen);
// Exercise the actual grouping wrappers against the core revision-aware batch.
// Presentation is stubbed, while persistence and Undo retain their real code.
const app = fs.readFileSync('web/app.js','utf8');
const ux = fs.readFileSync('web/editorial-ux.js','utf8');
const filtering = ux.slice(ux.indexOf('  function allowedStories(items'),ux.indexOf('  // Marking a grouped card'));
const savedOnly = item('saved-only',{source_ids:['a'],title:'Otra historia guardada de una fuente que ahora está oculta'});
const modeState = {items:[visibleGroup,savedOnly],mode:'all',hiddenSources:new Set(['a']),sources:[],
  mutedKeywords:'',feed:'',hideRead:false,read:new Set()};
const filterRuntime = {model,state:modeState,selectedType:'all',window:{},
  dashboardEligible:()=>modeState.items,applyFilters:()=>modeState.items};
vm.createContext(filterRuntime); vm.runInContext(filtering,filterRuntime);
assert.equal(vm.runInContext('applyFilters("all").length',filterRuntime),1);
assert.equal(vm.runInContext('applyFilters("all")[0].publisher',filterRuntime),'Visible publisher');
assert.equal(vm.runInContext('applyFilters("saved").length',filterRuntime),2,'saved-only articles survive hidden source preferences');
assert.equal(vm.runInContext('applyFilters("saved")[0].publisher',filterRuntime),'a','saved group keeps its original credited lead');
assert.equal(vm.runInContext('applyFilters("saved")[0].also_in.length',filterRuntime),1,'saved comparison retains attributed variants');
modeState.mode='saved';
assert.equal(vm.runInContext('applyFilters().length',filterRuntime),2,'default active saved mode gets the same exception');
assert.equal(vm.runInContext('dashboardEligible().length',filterRuntime),1,'homepage still respects hidden sources while saved mode lingers');
const cardCode = ux.slice(ux.indexOf('  const cardBase = card;'),ux.indexOf('  const readerBase = openArticleReader;'));
const badges = [];
const cardRuntime = {model,card:()=>({dataset:{},querySelector:()=>({append:node=>badges.push(node)})}),badge:()=>({})};
vm.createContext(cardRuntime); vm.runInContext(cardCode,cardRuntime);
cardRuntime.unknown = item('unknown'); cardRuntime.known = item('known',{content_type:'news'});
vm.runInContext('card(unknown); card(known)',cardRuntime);
assert.equal(badges.length,1,'unclassified cards do not repeat a noisy label; known publisher types stay visible');
const core = app.slice(app.indexOf('const readRevisions=new Map();'),app.indexOf('\nfunction render()',app.indexOf('const readRevisions=new Map();')));
const wrappers = ux.slice(ux.indexOf('  function expandMembers(items)'),ux.indexOf('  const emptyBase = emptyState;'));
let undo;
const runtime = {model, state:{items:[item('a'),item('b')],read:new Set(['b'])},
  allowedStories:items=>items,document:{activeElement:null,querySelector:()=>null},
  window:{},persist(){},render(){},actionToast(message,options){if(options?.undo) undo=options.undo;},
  format:{format:String},$:()=>({}),Set,Map};
vm.createContext(runtime);
vm.runInContext(core + '\n' + wrappers,runtime);
vm.runInContext("markArticlesRead([state.items[0]])",runtime);
assert(runtime.state.read.has('a') && runtime.state.read.has('b'));
undo(null);
assert(!runtime.state.read.has('a') && runtime.state.read.has('b'),'batch Undo preserves the previously read member');
runtime.state.read.clear();
vm.runInContext("markArticlesRead([state.items[0]]); markRead('a',false); markRead('a',true);",runtime);
undo(null);
assert(runtime.state.read.has('a') && runtime.state.read.has('b'),'concurrent explicit grouped read survives older batch Undo');
vm.runInContext("markRead('a',false)",runtime);
assert.equal(runtime.state.read.size,0,'explicit unread applies to every group member');
runtime.state.items=[]; runtime.state.pageView='feed'; runtime.state.mode='saved';
runtime.window={RadarLibrary:{getSavedStories:()=>[visibleGroup]}};
vm.runInContext("markRead('a',true)",runtime);
assert(runtime.state.read.has('a') && runtime.state.read.has('b'),'cached saved groups retain every attributable reading identity');
console.log('OK: editorial grouping, attribution, metadata, diverse recent digest and local interests');
