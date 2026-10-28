import { join } from 'node:path';
import { readFileSync } from 'node:fs';
import { ROOT, LEVELS, writeJson } from './lib/util.ts';

const read = (path: string) => JSON.parse(readFileSync(join(ROOT, path), 'utf8'));
const rows = (kind: string): any[] => LEVELS.flatMap(({ level }) => read('data/json/' + kind + '/' + level.toLowerCase() + '.json'));
const vocab = rows('vocab');
const grammar = rows('grammar');
const pilot = read('sources/quality/pilot.json');
for (const [ids, data] of [[pilot.vocab_ids, vocab], [pilot.grammar_ids, grammar]] as [string[], any[]][]) {
  if (ids.length !== new Set(ids).size || ids.some(id => !data.some(e => e.id === id)))
    throw new Error('Invalid pilot selection');
}
const coverage = (data: any[]) => Object.fromEntries(LEVELS.map(({ level }) => {
  const items = data.filter(e => e.level === level);
  return [level, {
    total: items.length,
    draft: items.filter(e => e.zh?.status === 'draft').length,
    reviewed: items.filter(e => e.zh?.status === 'reviewed').length,
    ai_reviewed: items.filter(e => e.zh?.status === 'reviewed' && e.zh?.review_method === 'ai').length,
    stale: items.filter(e => e.zh?.status === 'stale').length,
    translated_examples: items.reduce((n, e) => n + (e.zh?.status !== 'stale' ? e.zh?.examples.length ?? 0 : 0), 0),
  }];
}));
const groups = new Map<string, any[]>();
for (const v of vocab) if (v.jmdict_id) {
  const key = v.jmdict_id + ':' + v.reading;
  groups.set(key, [...(groups.get(key) ?? []), v]);
}
const candidates = [...groups].filter(([, es]) => es.length > 1).map(([key, es]) => ({
  kind: 'shared_dictionary_reading', key, ids: es.map(e => e.id), words: es.map(e => e.word),
  status: 'needs_review', reason: 'May be legitimate distinct spellings. Do not merge without an ID migration.',
}));
const malformedFurigana = vocab.flatMap(e => (e.examples ?? [])
  .filter((ex: any) => [...(ex.furigana ?? '').matchAll(/\{[^|{}]+\|([^|{}]+)\}/g)]
    .some(m => !/^[ぁ-ゖー]+$/.test(m[1])))
  .map((ex: any) => ({ id: e.id, word: e.word, ja: ex.ja, furigana: ex.furigana, status: 'needs_review' })));
const report = {
  selection: pilot.selection,
  pilot: { vocab: pilot.vocab_ids.length, grammar: pilot.grammar_ids.length },
  coverage: { vocab: coverage(vocab), grammar: coverage(grammar) },
  applied_corrections: read('sources/corrections/entries.json').map((x: any) => ({ id: x.id, reason: x.reason, references: x.references })),
  candidates,
  malformed_furigana: malformedFurigana,
  limitation: 'Structural audit and explicitly recorded Codex linguistic review; no independent human review or statistical error-rate estimate. Initial pilot selection and expanded coverage are reported separately.',
};
writeJson(join(ROOT, 'data/quality-report.json'), report);
console.log(JSON.stringify({ pilot: report.pilot, coverage: report.coverage, review_candidates: candidates.length }, null, 2));
