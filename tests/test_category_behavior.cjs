"use strict";
// Execute the production category/filter/briefing logic with offline articles.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');
const v12 = fs.readFileSync(path.join(root, 'web/v12.js'), 'utf8');
const features = fs.readFileSync(path.join(root, 'web/features.js'), 'utf8');
const categories = [
  '01 - Inteligencia Artificial', '02 - Tecnología', '03 - Internacionales',
  '04 - Chile', '05 - Venezuela', '06 - Latinoamérica', '07 - Concepción'
];
function productionFunction(source, name) {
  const start = source.indexOf('function ' + name + '(');
  assert.ok(start >= 0, name + ' exists');
  let depth = 0;
  for (let end = source.indexOf('{', start); end < source.length; end++) {
    if (source[end] === '{') depth++;
    if (source[end] === '}' && --depth === 0) return source.slice(start, end + 1);
  }
  throw new Error('Unclosed production function: ' + name);
}
function reader(scope) {
  const items = categories.map((cat, i) => ({id: 'story-' + i, title: 'Noticia ' + i,
    categories: [cat], source_ids: ['source-' + i], published_at: new Date().toISOString()}));
  const state = {categories, items, category: 'all', mode: 'all', search: '', mutedKeywords: '',
    hiddenSources: new Set(), saved: new Set(), read: new Set(), feed: '', maxAge: 0,
    hideRead: false, sort: 'newest'};
  const context = vm.createContext({state, window: {},
    localStorage: {getItem: key => key === 'radar-v12-preferences' ? JSON.stringify({briefing: scope}) : null},
    actionToast() {}, eligible: () => items, within: () => true, coverageOf: () => 1,
    storyTime: () => 0});
  const labels = app.match(/^const CATEGORY_LABELS = .*$/m)[0];
  vm.runInContext([labels, productionFunction(app, 'categoryLabel'),
    productionFunction(app, 'stripAccents'), 'const newsSearchCache=new WeakMap();', productionFunction(app,'newsSearchText'), productionFunction(app, 'applyFilters')].join('\n'), context);
  // This initial module section owns geography and the public briefing API;
  // DOM rendering starts at const display and is exercised by the browser smoke.
  vm.runInContext(v12.slice(0, v12.indexOf('  const display =')) +
    '\nwindow.testInGeo = inGeo;\n})();', context);
  vm.runInContext(productionFunction(features, 'briefingData'), context);
  return context;
}
const plain = value => JSON.parse(JSON.stringify(value));
const all = reader('all');
assert.equal(vm.runInContext("categoryLabel('07 - Concepción')", all), 'Concepción');
all.state.category = '07 - Concepción';
assert.deepEqual(plain(vm.runInContext('applyFilters().map(x => x.id)', all)), ['story-6'],
  'the Concepción folder excludes other category articles');
assert.deepEqual(plain(vm.runInContext('briefingData().sections.map(x => x.label)', all)),
  ['Inteligencia Artificial', 'Tecnología', 'Internacionales', 'Chile', 'Venezuela', 'Latinoamérica', 'Concepción']);

const chile = reader('chile');
assert.deepEqual(plain(chile.window.RadarV12.briefingCategories()), ['04 - Chile', '07 - Concepción'],
  'the Chile briefing includes the local folder');
assert.deepEqual(plain(vm.runInContext('briefingData().sections.map(x => x.items[0].id)', chile)), ['story-3', 'story-6']);
const latam = reader('latam');
assert.deepEqual(plain(latam.window.RadarV12.briefingCategories()),
  ['04 - Chile', '05 - Venezuela', '06 - Latinoamérica', '07 - Concepción']);
for (const geo of ['chile', 'latam']) {
  assert.equal(latam.window.testInGeo({categories: ['07 - Concepción']}, geo), true,
    'Concepción articles belong to ' + geo);
}
for (const geo of ['venezuela', 'region']) {
  assert.equal(latam.window.testInGeo({categories: ['07 - Concepción']}, geo), false,
    'Concepción articles do not belong exclusively to ' + geo);
}
const local = reader('cat:07 - Concepción');
assert.deepEqual(plain(vm.runInContext('briefingData().sections.map(x => x.items[0].id)', local)), ['story-6']);
console.log('Category behavior verified: 7 folders, exclusive filtering, Chile/Latam/local briefings.');
