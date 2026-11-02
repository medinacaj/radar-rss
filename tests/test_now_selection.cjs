'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const app=fs.readFileSync('web/app.js','utf8');
const start=app.indexOf('function nowItemTime('),end=app.indexOf('function nowHeadline(',start);
const ctx=vm.createContext({Date,Number,Set,Array});
if(start>=0)vm.runInContext(app.slice(start,end),ctx);
const now=Date.parse('2026-11-01T12:00:00Z'),hour=3600000;
const story=(id,age,extras={})=>({id,published_at:new Date(now-age*hour).toISOString(),categories:['04 - Chile'],...extras});
function select(items,options={}){assert.equal(typeof ctx.selectNowItems,'function');return ctx.selectNowItems(items,{now,...options});}
test('Ahora prioritizes newest publication across all sections without mutating input',()=>{
 const old=story('covered',3,{coverage:20,categories:['03 - Internacionales']}),fresh=story('fresh',.1);
 const input=Object.freeze([old,fresh]);assert.deepEqual(Array.from(select(input),x=>x.id),['fresh','covered']);assert.equal(input[0],old);
});
test('future or invalid publication falls back to valid detection and unknown dates go last',()=>{
 const future=story('future',-4,{first_seen_at:new Date(now-2*hour).toISOString()});
 const invalid=story('invalid',0,{published_at:'broken',first_seen_at:new Date(now-hour).toISOString()});
 assert.deepEqual(Array.from(select([future,invalid,story('unknown',0,{published_at:null})]),x=>x.id),['invalid','future','unknown']);
});
test('En desarrollo requires actual alternate publications and recent evidence',()=>{
 const alt=[{url:'https://medium.test/a',published_at:new Date(now-hour).toISOString()}];
 assert.deepEqual(Array.from(select([story('query',1,{coverage:10}),story('group',2,{coverage:2,also_in:alt}),story('old',30,{coverage:2,also_in:[{url:'https://medium.test/b',published_at:new Date(now-30*hour).toISOString()}]})],{view:'developing'}),x=>x.id),['group']);
});
test('regional and personal views filter explicit categories; duplicates and limits are stable',()=>{
 const a=story('a',1),b=story('b',2,{categories:['05 - Venezuela']});
 assert.deepEqual(Array.from(select([a,b],{view:'zone',zone:'05 - Venezuela'}),x=>x.id),['b']);
 assert.deepEqual(Array.from(select([a,b],{view:'mine',categories:['04 - Chile']}),x=>x.id),['a']);
 assert.equal(select([a,b],{view:'mine',categories:[]}).length,0);
 assert.equal(select([a,a,b],{limit:1}).length,1);
});
test('editorial sidebar starts closed only when no explicit preference exists',()=>{
 const src=fs.readFileSync('web/app.js','utf8'),start=src.indexOf('function sidebarStartsCollapsed(');
 assert(start>=0,'sidebar default policy missing');
 const c=vm.createContext({});vm.runInContext(src.slice(start,src.indexOf('\n}',start)+2),c);
 assert.equal(c.sidebarStartsCollapsed(null),true);
 assert.equal(c.sidebarStartsCollapsed('false'),false);
 assert.equal(c.sidebarStartsCollapsed('true'),true);
});
