'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const app=fs.readFileSync('web/app.js','utf8');
const a=app.indexOf('function visitArticle('),b=app.indexOf('\nfunction ',a+1);
assert.ok(a>=0,'Missing direct publisher visit');
let prevented=false;const reads=[],timers=[],opens=[];
const state={newTab:false};const c={state,markRead:(...args)=>reads.push(args),render(){},safeURL:v=>/^https?:\/\//.test(v)?v:null,
 window:{setTimeout:fn=>timers.push(fn),open:(...args)=>opens.push(args)}};
vm.createContext(c);vm.runInContext(app.slice(a,b),c);
const event={currentTarget:{tagName:'A'},button:0,preventDefault(){prevented=true;}};
c.visitArticle({id:'a',url:'https://publisher.example/story'},event);
assert.equal(prevented,false,'native link must remain navigable');assert.equal(event.currentTarget.target,'_self');
assert.equal(reads[0][0],'a');assert.equal(reads[0][2].render,false,'read persistence must not detach the activating link');assert.equal(timers.length,1);assert.equal(opens.length,0);
for(const modification of [{ctrlKey:true},{metaKey:true},{button:1}]){c.visitArticle({id:'a',url:'https://publisher.example/story'},{...event,...modification});assert.equal(prevented,false);}
state.newTab=true;c.visitArticle({id:'b',url:'https://publisher.example/b'});assert.equal(opens[0][1],'_blank');assert.equal(opens[0][2],'noopener,noreferrer');
c.visitArticle({id:'bad',url:'javascript:alert(1)'},event);assert.equal(prevented,true);assert.equal(reads.length,5);
console.log('Direct publisher visits retain native navigation, safe URLs, tab preference and deferred redraw.');
let redraws=0,persisted=0;
const core={state:{read:new Set()},document:{activeElement:null},persist:()=>{persisted++;},render:()=>{redraws++;}};
vm.createContext(core);
vm.runInContext(app.slice(app.indexOf('const readRevisions=new Map();'),app.indexOf('function markArticlesRead(')),core);
core.markRead('linked',true,['linked','alternate'],{render:false});
assert.equal(redraws,0,'persisting native navigation cannot rebuild and detach the activating link');
assert.equal(persisted,1);assert.equal(core.state.read.size,2);
