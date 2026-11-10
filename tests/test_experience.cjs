'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const file=path.join(__dirname,'../web/experience.js');
assert.ok(fs.existsSync(file),'Reading experience module must exist');
const {effectiveColumns,profileSettings,normalizePreferences}=require(file);

// The previous 280px minimum prevented even a wide desktop from using 5/6.
assert.equal(effectiveColumns(1060,16,'normal','5',12),5);
assert.equal(effectiveColumns(1060,16,'normal','6',12),6);
assert.equal(effectiveColumns(900,16,'normal','6',12),5);
assert.equal(effectiveColumns(900,22,'normal','6',12),4);
assert.equal(effectiveColumns(900,22,'large','6',12),3);
assert.equal(effectiveColumns(320,22,'large','6',12),1);
// Auto and standard layouts still enforce generous reading-card widths.
assert.equal(effectiveColumns(900,16,'normal','auto',20),3);
assert.equal(effectiveColumns(900,16,'normal','4',20),3);
assert.equal(effectiveColumns(1800,16,'normal','2',20),2);
assert.equal(effectiveColumns(1800,16,'normal','auto',20),6);
assert.equal(effectiveColumns(0,16,'normal','6',12),1);

const current={cardTitleSize:22,fontSize:'large',columns:'6',theme:'dark',layout:'cards'};
for(const profile of ['visual','compact','headlines']){
 const changed=profileSettings(profile,current);
 for(const key of ['cardTitleSize','fontSize','columns','theme'])assert.equal(changed[key],current[key]);
}
assert.deepEqual(profileSettings('headlines',current),{...current,layout:'list',density:'compact',showImages:false,showSummaries:false});
assert.equal(profileSettings('visual',current).showImages,true);
assert.equal(profileSettings('compact',current).showSummaries,true);
assert.equal(profileSettings('compact',current).showImages,false);
assert.deepEqual(profileSettings('unknown',current),current);

assert.deepEqual(normalizePreferences(null),{pinnedDestinations:[]});
assert.deepEqual(normalizePreferences({pinnedDestinations:['Chile','Chile',null,{},'','__proto__','carpeta/Mis lecturas','x'.repeat(200)]}),{pinnedDestinations:['Chile','carpeta/Mis lecturas']});
assert.deepEqual(normalizePreferences({pinnedDestinations:'Chile'}),{pinnedDestinations:[]});
assert.equal(normalizePreferences({pinnedDestinations:Array.from({length:40},(_,i)=>'Carpeta '+i)}).pinnedDestinations.length,25);
console.log('Reading experience: column legibility, preference preservation and defensive favorites passed');
