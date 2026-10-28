/**
 * Offline reproducible overlays on the committed or freshly rebuilt dataset.
 * Corrections are guarded; translations survive rebuilds and expire on source edits.
 */
import { join } from 'node:path';
import { readFileSync } from 'node:fs';
import Ajv from 'ajv';
import { ROOT, DATA_DIR, LEVELS, writeJson, writeCsv } from './lib/util.ts';
import { applyCorrections, type EntryCorrection } from './lib/corrections.ts';
import { attachChinese, sourceHash, validateReview, type Chinese } from './lib/localization.ts';

const read = (p: string) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const check = process.argv.includes('--check');
const ajv = new Ajv({ allErrors: true });
const validate = ajv.compile(read('schema/chinese.schema.json'));
const output = new Map<string, any[]>();
for (const kind of ['vocab', 'grammar']) {
  const translations: Record<string, Chinese> = read('sources/zh-CN/' + kind + '.json');
  const all = LEVELS.flatMap(({ level }) => read('data/json/' + kind + '/' + level.toLowerCase() + '.json'));
  if (kind === 'vocab') applyCorrections(all, read('sources/corrections/entries.json') as EntryCorrection[]);
  const ids = new Set(all.map(e => e.id));
  for (const [id, translation] of Object.entries(translations)) {
    if (!ids.has(id)) throw new Error('Orphan Chinese entry: ' + id);
    if (!validate(translation)) throw new Error(id + ': ' + ajv.errorsText(validate.errors));
    validateReview(translation);
    const source = all.find(e => e.id === id);
    if (translation.source_hash === sourceHash(source)) {
      for (const ex of translation.examples)
        if (!source.examples?.some((e: any) => e.ja === ex.ja)) throw new Error('Unknown source sentence: ' + id);
    }
  }
  for (const { level } of LEVELS) {
    const path = 'data/json/' + kind + '/' + level.toLowerCase() + '.json';
    const rows = all.filter(e => e.level === level).map(e => attachChinese(e, translations[e.id]));
    if (check && JSON.stringify(rows) !== JSON.stringify(read(path))) throw new Error('Generated output is stale: ' + path);
    output.set(path, rows);
  }
}
// Overlay corrections can add examples; preserve upstream snapshot provenance.
const metaPath = 'data/json/meta.json';
const meta = read(metaPath);
const withExamples = [...output].filter(([path]) => path.includes('/vocab/'))
  .flatMap(([, rows]) => rows).filter(e => e.examples?.length).length;
if (check && meta.vocab_with_examples !== withExamples) throw new Error('Generated output is stale: ' + metaPath);
// Validate everything before writing any output.
if (!check) for (const [path, rows] of output) {
  writeJson(join(ROOT, path), rows);
  const kind = path.includes('/vocab/') ? 'vocab' : 'grammar';
  const lc = rows[0].level.toLowerCase();
  const headers = kind === 'vocab'
    ? ['id','word','reading','romaji','meanings','level','pos','jmdict_id','other_forms','example_ja','example_en','meanings_zh','explanation_zh','status_zh','formation_zh','notes_zh','examples_zh']
    : ['id','pattern','reading','romaji','level','meaning','formation','example_ja','example_en','tags','notes','meanings_zh','explanation_zh','status_zh','formation_zh','notes_zh','examples_zh'];
  writeCsv(join(DATA_DIR, 'csv', kind + '-' + lc + '.csv'), headers, rows.map(e => headers.map(key => {
    if (key === 'example_ja') return e.examples?.[0]?.ja ?? '';
    if (key === 'example_en') return e.examples?.[0]?.en ?? '';
    if (key === 'meanings_zh') return e.zh?.status !== 'stale' ? (e.zh?.meanings ?? []).join('; ') : '';
    if (key === 'explanation_zh') return e.zh?.status !== 'stale' ? e.zh?.explanation ?? '' : '';
    if (key === 'formation_zh' || key === 'notes_zh') return e.zh?.status !== 'stale' ? e.zh?.[key.replace('_zh', '')] ?? '' : '';
    if (key === 'examples_zh') return e.zh?.status !== 'stale' ? JSON.stringify(e.zh?.examples ?? []) : '[]';
    if (key === 'status_zh') return e.zh?.status ?? '';
    return Array.isArray(e[key]) ? e[key].join('; ') : e[key] ?? '';
  })));
}
if (!check && meta.vocab_with_examples !== withExamples) {
  meta.vocab_with_examples = withExamples;
  writeJson(join(ROOT, metaPath), meta);
}
console.log(check ? 'Corrections and Chinese outputs are current.' : 'Applied corrections and Chinese overlays.');
