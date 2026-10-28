import { createHash } from 'node:crypto';

import type { Chinese } from '../../src/index.ts';
export type { Chinese } from '../../src/index.ts';

function canonical(value: any): any {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  return value;
}

/** Includes readings, glosses and examples; ignores generated localization. */
export function sourceHash(entry: unknown): string {
  const { zh: _previous, ...source } = entry as Record<string, unknown>;
  return createHash('sha256').update(JSON.stringify(canonical(source))).digest('hex');
}

/** Bind approval to the exact localized content, including sentence translations. */
export function reviewHash(translation: Chinese): string {
  const { status: _status, reviewer: _reviewer, review_method: _method,
    reviewed_at: _date, review_hash: _hash, ...content } = translation;
  return createHash('sha256').update(JSON.stringify(canonical(content))).digest('hex');
}

export function validateReview(translation: Chinese): void {
  if (translation.status !== 'reviewed') return;
  if (!translation.reviewer?.trim() || !translation.review_method || !translation.reviewed_at)
    throw new Error('Missing review provenance');
  if (translation.review_hash !== reviewHash(translation))
    throw new Error('Reviewed Chinese content changed; re-review required');
}

export function attachChinese(entry: any, translation?: Chinese): any {
  const { zh: _previous, ...source } = entry;
  if (!translation) return source;
  validateReview(translation);
  const current = translation.source_hash === sourceHash(source);
  return { ...source, zh: { ...translation, status: current ? translation.status : 'stale' } };
}
