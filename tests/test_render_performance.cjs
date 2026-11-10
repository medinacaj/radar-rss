'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/app.js','utf8');
function extract(name){const a=source.indexOf('function '+name+'(');assert.ok(a>=0,`Missing behavior: ${name}`);let depth=0,started=false;for(let i=source.indexOf('{',a);i<source.length;i++){if(source[i]==='{'){depth++;started=true;}else if(source[i]==='}'&&!--depth&&started)return source.slice(a,i+1);}}
let scans=0;const state={mode:'all',feed:'',category:'all',search:'',sort:'newest',maxAge:0,hideRead:false,onlyNew:false};
const context={state,Map,applyFilters:(mode=state.mode)=>{scans++;return [mode,state.feed];}};
vm.createContext(context);vm.runInContext(extract('withRenderFilterCache'),context);
const base=context.applyFilters;
context.withRenderFilterCache(()=>{assert.strictEqual(context.applyFilters('all'),context.applyFilters('all'));state.feed='source';assert.deepEqual(context.applyFilters('all'),['all','source']);assert.strictEqual(context.applyFilters('all'),context.applyFilters('all'));});
assert.equal(scans,2,'one scan per mode/source scope inside a render');assert.equal(context.applyFilters,base);
context.withRenderFilterCache(()=>context.applyFilters());assert.equal(scans,3,'a new render observes new reading/filter state');
assert.throws(()=>context.withRenderFilterCache(()=>{throw Error('render failed');}),/render failed/);assert.equal(context.applyFilters,base,'failure must restore module filter chain');
console.log('Render filtering: bounded scans, scope changes and restoration verified.');
