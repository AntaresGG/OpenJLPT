import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { attachChinese, sourceHash, type Chinese } from '../../scripts/lib/localization.ts';
import { applyCorrections } from '../../scripts/lib/corrections.ts';
import { ROOT } from '../../scripts/lib/util.ts';
import { findWord, getVocab, getGrammar, searchVocab, searchGrammar } from '../../src/index.ts';

test('Chinese expires on source changes, not property order or previous localization', () => {
  const entry = { id: 'x', word: '食べる', meanings: ['to eat'], examples: [{ ja: '食べます。', en: 'I eat.' }] };
  const zh: Chinese = { status: 'draft', source_hash: sourceHash(entry), meanings: ['吃'], examples: [], references: ['test fixture'] };
  assert.equal(sourceHash({ meanings: entry.meanings, examples: entry.examples, word: entry.word, id: 'x' }), sourceHash(entry));
  assert.equal(attachChinese({ ...entry, zh }, zh).zh.status, 'draft');
  assert.equal(attachChinese({ ...entry, meanings: ['changed'] }, zh).zh.status, 'stale');
  assert.equal(attachChinese({ ...entry, examples: [{ ja: 'changed', en: 'I eat.' }] }, zh).zh.status, 'stale');
  assert.equal(attachChinese({ ...entry, zh }).zh, undefined);
});

test('corrections are idempotent and reject unexpected upstream edits before mutation', () => {
  const fixes = JSON.parse(readFileSync(join(ROOT, 'sources/corrections/entries.json'), 'utf8'));
  const entries = structuredClone(getVocab());
  applyCorrections(entries, fixes);
  const before = JSON.stringify(entries);
  applyCorrections(entries, fixes);
  assert.equal(JSON.stringify(entries), before);
  entries.find(e => e.id === fixes[fixes.length - 1].id)!.meanings = ['unexpected upstream edit'];
  const changed = JSON.stringify(entries);
  assert.throws(() => applyCorrections(entries, fixes), /conflict/);
  assert.equal(JSON.stringify(entries), changed);
});

test('known beginner corrections preserve IDs and align selected senses', () => {
  const soap = findWord('せっけん')!;
  assert.equal(soap.id, 'b48d0c99d4');
  assert.equal(soap.jmdict_id, 1382590);
  assert.deepEqual(soap.meanings, ['soap']);
  assert.deepEqual(soap.pos, ['n']);
  assert.deepEqual(findWord('一日')!.meanings, ['one day', 'all day']);
  assert.equal(findWord('そう')!.jmdict_id, 2137720);
  assert.deepEqual(findWord('そう')!.pos, ['adv']);
  assert.ok(findWord('そう')!.examples!.every(e => !e.tatoeba_id));
  assert.ok(findWord('受付')!.meanings.includes('reception (desk)'));
  assert.ok(findWord('四日')!.meanings.includes('fourth day of the month'));
  assert.ok(findWord('相談')!.meanings.includes('consultation'));
});

test('Chinese search finds exact and partial Chinese while preserving English behavior', () => {
  assert.equal(searchVocab('肥皂')[0].word, 'せっけん');
  assert.equal(searchVocab('接待')[0].word, '受付');
  assert.equal(searchVocab('吃')[0].word, '食べる');
  assert.equal(searchVocab('eat')[0].word, '食べる');
  assert.ok(searchGrammar('事先').some(g => g.id === 'te-oku'));
  assert.equal(getVocab().filter(v => v.zh?.status === 'draft').length, 200);
  assert.equal(getGrammar().filter(g => g.zh?.status === 'draft').length, 20);
});
