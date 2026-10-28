export interface EntryCorrection {
  id: string;
  word: string;
  reading: string;
  reason: string;
  references: string[];
  before: Record<string, unknown>;
  set: Record<string, unknown>;
}

/** Accept old or already corrected values, but fail on unexpected upstream edits. */
export function applyCorrections(entries: any[], corrections: EntryCorrection[]): void {
  const ids = new Set<string>();
  for (const fix of corrections) {
    if (ids.has(fix.id)) throw new Error('Duplicate correction: ' + fix.id);
    ids.add(fix.id);
    const entry = entries.find(e => e.id === fix.id);
    if (!entry || entry.word !== fix.word || entry.reading !== fix.reading)
      throw new Error('Correction identity changed: ' + fix.id);
    if (!fix.reason || !fix.references.length) throw new Error('Correction needs evidence: ' + fix.id);
    for (const [key, value] of Object.entries(fix.set)) {
      if (['id', 'word', 'reading', 'level', 'zh'].includes(key))
        throw new Error('Identity changes require a migration: ' + key);
      const actual = JSON.stringify(entry[key]);
      if (actual !== JSON.stringify(fix.before[key]) && actual !== JSON.stringify(value))
        throw new Error('Upstream correction conflict: ' + fix.id + '.' + key);
    }
  }
  for (const fix of corrections) Object.assign(entries.find(e => e.id === fix.id), fix.set);
}
