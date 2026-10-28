import { createHash } from 'node:crypto';

import type { Chinese } from '../../src/index.ts';
export type { Chinese } from '../../src/index.ts';

function canonical(value: any): any {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).filter(k => k !== 'zh').sort().map(k => [k, canonical(value[k])]));
  return value;
}

/** Includes readings, glosses and examples; ignores generated localization. */
export function sourceHash(entry: unknown): string {
  return createHash('sha256').update(JSON.stringify(canonical(entry))).digest('hex');
}

export function attachChinese(entry: any, translation?: Chinese): any {
  const { zh: _previous, ...source } = entry;
  if (!translation) return source;
  const current = translation.source_hash === sourceHash(source);
  return { ...source, zh: { ...translation, status: current ? translation.status : 'stale' } };
}
