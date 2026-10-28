import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { attachChinese, sourceHash, reviewHash, validateReview, type Chinese } from '../../scripts/lib/localization.ts';
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
  entries.find(e => e.id === fixes[0].id)!.meanings = ['unexpected upstream edit'];
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
  assert.equal(getVocab().filter(v => v.zh?.status === 'reviewed').length, 1859);
  assert.equal(getGrammar().filter(g => g.zh?.status === 'reviewed').length, 131);
});

test('review binds the exact Chinese wording and requires honest provenance', () => {
  const zh = structuredClone(findWord('食べる')!.zh!);
  assert.equal(zh.review_method, 'ai');
  assert.equal(zh.reviewer, 'Codex');
  assert.doesNotThrow(() => validateReview(zh));
  const approved = reviewHash(zh);
  zh.examples[0].zh = 'Changed translation';
  assert.notEqual(reviewHash(zh), approved);
  assert.throws(() => validateReview(zh), /re-review/);
  zh.status = 'draft';
  assert.doesNotThrow(() => validateReview(zh));
  zh.status = 'reviewed';
  delete zh.reviewer;
  assert.throws(() => validateReview(zh), /provenance/);
});

test('all reviewed entries have complete aligned Chinese examples and current source hashes', () => {
  const entries = [...getVocab(), ...getGrammar()].filter(e => e.zh?.status === 'reviewed');
  for (const entry of entries) {
    assert.equal(entry.zh!.source_hash, sourceHash(entry), entry.id);
    assert.doesNotThrow(() => validateReview(entry.zh!), entry.id);
    assert.deepEqual(entry.zh!.examples.map(e => e.ja), entry.examples!.map(e => e.ja), entry.id);
    assert.ok(entry.zh!.examples.every(e => e.zh.trim().length > 0), entry.id);
    assert.ok(entry.examples!.every(e => !/#[0-9]+/.test(e.furigana ?? '')), entry.id);
  }
  assert.equal(entries.filter(e => e.level !== 'N3').reduce((n,e) => n + e.zh!.examples.length, 0), 489);
});

test('all N3 vocabulary and grammar have reviewed Chinese with aligned examples', () => {
  const vocab = getVocab().filter(e => e.level === 'N3');
  const grammar = getGrammar().filter(e => e.level === 'N3');
  assert.equal(vocab.filter(e => e.zh?.status === 'reviewed').length, 1659);
  assert.equal(grammar.filter(g => g.zh?.status === 'reviewed').length, 101);
  for (const entry of [...vocab, ...grammar]) {
    assert.equal(entry.zh?.status, 'reviewed', entry.id);
    assert.ok(entry.zh!.examples.length >= 1, entry.id);
  }
  assert.equal(vocab.filter(e => !e.zh).length, 0);
  assert.equal(grammar.filter(e => !e.zh).length, 0);
  assert.ok(searchVocab('爱恋').some(e => e.id === 'c3b1f16454'));
  assert.ok(searchGrammar('难怪').some(e => e.id === 'wake-da'));
  assert.ok(vocab.find(e => e.word === '命')!.meanings.every(m => !['command', 'decree'].includes(m)));
  assert.ok(vocab.find(e => e.word === '市場')!.meanings.includes('marketplace'));
  for (const word of ['粗', '現す', 'あっ', 'いえ', '抱く']) {
    assert.ok(vocab.find(e => e.word === word)!.examples!.every(e => !e.tatoeba_id), word);
  }
});

test('review fixes counter, greeting, lexical reading and inclusive boundary errors', () => {
  const five = findWord('五つ')!;
  assert.ok(five.examples!.every(e => !e.ja.includes('五つ木')));
  assert.ok(five.examples!.some(e => e.ja === '卵を五つ買いました。' && !e.tatoeba_id));
  assert.ok(findWord('いただきます')!.examples!.every(e => e.ja.includes('「いただきます」') && !e.tatoeba_id));
  assert.ok(findWord('以下')!.meanings.includes('not more than'));
  assert.equal(findWord('以下')!.examples![0].en, 'You cannot buy it for 1,000 yen or less.');
  assert.ok(findWord('行う')!.examples!.some(e => e.furigana?.includes('{行|おこな}')));
  assert.ok(getVocab().find(e => e.word === '明日' && e.reading === 'あす')!.examples!.every(e => e.furigana?.includes('{明日|あす}')));
});
