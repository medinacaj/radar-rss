'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('web/app.js', 'utf8');
const start = source.indexOf('function selectInternationalLead(');
const clockStart = source.indexOf('function storyTime(');
const clockEnd = source.indexOf('\n}', clockStart) + 2;
const context = vm.createContext({ Date, Number });
vm.runInContext(source.slice(clockStart, clockEnd), context);
if (start >= 0) vm.runInContext(source.slice(start, source.indexOf('\nfunction nowItemTime', start)), context);
const NOW = Date.parse('2026-10-28T12:00:00Z');
const HOUR = 3600000;
const story = (id, hours, coverage, category = '03 - Internacionales') => ({
  id, published_at: new Date(NOW - hours * HOUR).toISOString(), coverage,
  categories: [category], source_ids: [id]
});
const select = items => {
  assert.equal(typeof context.selectInternationalLead, 'function');
  return context.selectInternationalLead(items, NOW);
};

test('recent international coverage takes priority over a newer single-outlet headline', () => {
  const fresh = story('fresh', .1, 1), covered = story('covered', 8, 6);
  assert.equal(select([fresh, covered]), covered);
});

test('old and future stories do not override a current international headline', () => {
  const current = story('current', 2, 2);
  assert.equal(select([story('old', 30, 90), story('future', -1, 100), current]), current);
});

test('equal coverage is resolved by recency without modifying the input', () => {
  const older = Object.freeze(story('older', 6, 4));
  const newer = Object.freeze(story('newer', 1, 4));
  const input = Object.freeze([older, newer]);
  assert.equal(select(input), newer);
  assert.deepEqual(input, [older, newer]);
});

test('extra RSS ids and malformed coverage do not become independent outlets', () => {
  const legacy = story('legacy', .1, undefined);
  legacy.source_ids = Array.from({ length: 40 }, (_, i) => `query-${i}`);
  const actual = story('actual', 3, 2);
  assert.equal(select([legacy, story('string', .2, '999'), story('invalid', .3, Infinity), actual]), actual);
});

test('without current international stories the newest available one is retained', () => {
  const newer = story('newer', 26, 1);
  assert.equal(select([story('older', 70, 50), newer]), newer);
});

test('local-only and empty eligible selections return no international lead', () => {
  assert.equal(select([story('local', 1, 99, '04 - Chile')]), null);
  assert.equal(select([]), null);
});

test('a single international article remains readable', () => {
  const only = story('only', 2, 1);
  assert.equal(select([only]), only);
});
