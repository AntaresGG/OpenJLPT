import test from 'node:test';
import assert from 'node:assert/strict';
import { withCounts } from '../../scripts/lib/readme-counts.ts';

test('example coverage does not claim completeness or furigana from rounded counts', () => {
  const counts = {
    vocab: { N5: 674, N4: 630, N3: 1659, N2: 1778, N1: 3070, total: 7811 },
    kanji: { N5: 84, N4: 169, N3: 387, N2: 398, N1: 1345, total: 2383 },
    grammar: { N5: 81, N4: 98, N3: 101, N2: 123, N1: 123, total: 526 },
  };
  const text = '<!-- counts:line --><!-- /counts:line -->';
  for (const lang of ['en', 'ja'] as const) {
    const partial = withCounts(text, { counts, vocab_with_examples: 7799 }, lang);
    assert.ok(partial.includes('99.8%'));
    assert.ok(!/furigana|ふりがな/.test(partial));
    const almost = withCounts(text, { counts, vocab_with_examples: 7810 }, lang);
    assert.ok(!almost.includes('100%'));
    const full = withCounts(text, { counts, vocab_with_examples: 7811 }, lang);
    assert.ok(full.includes('100%'));
  }
});
