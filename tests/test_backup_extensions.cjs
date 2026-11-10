'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/library.js','utf8');
const start=source.indexOf('// Registered local preference modules'),end=source.indexOf('// Read-only snapshot',start);
assert.ok(start>=0&&end>start,'Missing local preference backup registry');
const c={Map,Set,Object,JSON};vm.createContext(c);vm.runInContext(source.slice(start,end),c);
let pins=['Chile'],other='old';const validate=v=>{if(!v||!Array.isArray(v.pins))throw Error('bad pins');return {pins:v.pins.filter(x=>typeof x==='string').slice(0,12)};};
assert.equal(c.registerBackupModule('experiencePreferences',{validate,export:()=>({pins}),restore:v=>{pins=v.pins;},reset:()=>{pins=[];}}),true);
assert.equal(c.registerBackupModule('__proto__',{}),false);assert.equal(c.registerBackupModule('agendaPreferences',{}),false);
assert.deepEqual(JSON.parse(JSON.stringify(c.exportExtensionModules())),{experiencePreferences:{pins:['Chile']}});
c.restoreExtensionModules({});assert.deepEqual(pins,['Chile'],'old backups preserve current module state');
assert.throws(()=>c.restoreExtensionModules({experiencePreferences:{pins:null}}),/bad pins/);assert.deepEqual(pins,['Chile']);
c.restoreExtensionModules({experiencePreferences:{pins:['Monagas',4]}});assert.deepEqual(Array.from(pins),['Monagas']);
c.registerBackupModule('otherPreferences',{validate:v=>v,export:()=>other,restore:v=>{other=v;if(v==='broken')throw Error('storage full');},reset:()=>{other='';}});
assert.throws(()=>c.restoreExtensionModules({experiencePreferences:{pins:['changed']},otherPreferences:'broken'}),/storage full/);assert.deepEqual(Array.from(pins),['Monagas']);assert.equal(other,'old');
c.resetBackupModules();assert.equal(pins.length,0);
console.log('Backup extensions: validation, old backups, rollback and reset verified.');

// A failed extension restore must also roll back the enclosing import's state/storage.
assert.equal(typeof c.beginPreferenceImport,'function','whole-import rollback missing');
const storage=new Map([['radar-layout','cards'],['radar-read','["prior"]'],['unrelated-key','keep']]);
c.localStorage={get length(){return storage.size;},key:i=>[...storage.keys()][i],getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,String(v)),removeItem:k=>storage.delete(k)};
c.state={layout:'cards',read:new Set(['prior'])};c.archive=new Map([['prior',{}]]);c.folders={Original:['a']};c.defaults={};c.tags={};c.activeFolder=null;c.activeTag='';
c.backupModules=()=>({experiencePreferences:{pins:['Monagas']}});let restoreOptions;
c.restoreModules=(modules,options)=>{restoreOptions=options;};
const rollback=c.beginPreferenceImport();c.state.layout='list';c.state.read=new Set(['changed']);c.archive=new Map();c.folders={Imported:['b']};storage.set('radar-layout','list');storage.set('radar-new','temporary');
rollback();assert.equal(c.state.layout,'cards');assert.deepEqual([...c.state.read],['prior']);assert.deepEqual(c.folders,{Original:['a']});assert.equal(storage.get('radar-layout'),'cards');assert.equal(storage.has('radar-new'),false);assert.equal(storage.get('unrelated-key'),'keep');assert.equal(restoreOptions.persist,false);
console.log('Whole import rollback restores prior reading state, folders, modules and storage.');

// Saved snapshots keep bounded, attributed variants and all reading identities.
const snapshotContext={safeURL:value=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}}};
vm.createContext(snapshotContext);
vm.runInContext(source.slice(source.indexOf('const snapshot=item=>'),source.indexOf('const rawArchive='))+'\nglobalThis.takeSnapshot=snapshot;',snapshotContext);
const saved=snapshotContext.takeSnapshot({id:'lead',url:'https://lead.example/story',source_ids:['a','b'],coverage:2,editorial_member_ids:['lead','alternate'],
 also_in:[{id:'alternate',url:'https://b.example/story',title:'Attributed title',publisher:'Publisher B',source_id:'b',category:'Chile',content_type:'analysis'},
 {id:'unsafe',url:'javascript:alert(1)',publisher:'Invalid'}]});
assert.equal(saved.also_in.length,1);assert.equal(saved.also_in[0].source_id,'b');assert.equal(saved.also_in[0].content_type,'analysis');
assert.deepEqual(Array.from(saved.editorial_member_ids),['lead','alternate']);assert.equal(saved.coverage,2);
console.log('Saved snapshots preserve safe attributed comparison and grouped reading identities.');
let persisted=0;
snapshotContext.state={saved:new Set(['lead']),items:[{id:'lead',url:'https://lead.example/story',title:'Same title',content_type:'analysis'}]};
snapshotContext.archive=new Map([['lead',snapshotContext.takeSnapshot({id:'lead',url:'https://lead.example/story',title:'Same title'})]]);
snapshotContext.saveArchive=()=>{persisted++;};
vm.runInContext(source.slice(source.indexOf('function syncArchive(){'),source.indexOf('function toggleBookmark(')),snapshotContext);
snapshotContext.syncArchive();assert.equal(snapshotContext.archive.get('lead').content_type,'analysis');assert.equal(persisted,1);
snapshotContext.syncArchive();assert.equal(persisted,1,'unchanged archive does not write again');
