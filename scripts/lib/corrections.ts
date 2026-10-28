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
    // A corrected reading keeps the frozen ID and must carry its original value.
    if ('reading' in fix.set && (fix.before.reading !== fix.reading ||
        typeof fix.set.reading !== 'string' || !fix.set.reading.trim() ||
        typeof fix.set.romaji !== 'string' || !fix.set.romaji.trim()))
      throw new Error('Reading correction needs original reading and corrected romaji: ' + fix.id);
    if (!entry || entry.word !== fix.word ||
        (entry.reading !== fix.reading && entry.reading !== fix.set.reading))
      throw new Error('Correction identity changed: ' + fix.id);
    if (!fix.reason || !fix.references.length) throw new Error('Correction needs evidence: ' + fix.id);
    for (const [key, value] of Object.entries(fix.set)) {
      if (['id', 'word', 'level', 'zh'].includes(key))
        throw new Error('Identity changes require a migration: ' + key);
      const actual = JSON.stringify(entry[key]);
      if (actual !== JSON.stringify(fix.before[key]) && actual !== JSON.stringify(value))
        throw new Error('Upstream correction conflict: ' + fix.id + '.' + key);
    }
  }
  for (const fix of corrections) Object.assign(entries.find(e => e.id === fix.id), fix.set);
}
