import fs from 'fs';
import path from 'path';

const META_PATH = path.join(__dirname, '..', 'reports', 'run-meta.json');

/**
 * One suffix per run, so the suite can be re-run against a database that already
 * holds rows from previous runs without tripping unique constraints
 * (Commodity.code, Gadget.identifier, User.username, auth.Group.name, ...).
 */
export function runId(): string {
  if (process.env.RUN_ID) return process.env.RUN_ID;
  if (fs.existsSync(META_PATH)) {
    return (JSON.parse(fs.readFileSync(META_PATH, 'utf8')) as { runId: string }).runId;
  }
  throw new Error('run-meta.json missing; globalSetup did not run.');
}

export function writeRunMeta(id: string): void {
  fs.mkdirSync(path.dirname(META_PATH), { recursive: true });
  fs.writeFileSync(META_PATH, `${JSON.stringify({ runId: id, startedAt: new Date().toISOString() }, null, 2)}\n`);
}

export function newRunId(): string {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  return `${stamp}${Math.floor(Math.random() * 0xffff).toString(16).padStart(4, '0')}`;
}

/** A unique value that still fits a column's max_length. */
export function unique(prefix: string, maxLength = 255): string {
  const value = `${prefix}-${runId()}`;
  return value.length <= maxLength ? value : `${prefix.slice(0, Math.max(0, maxLength - runId().length - 1))}-${runId()}`;
}

const counters = new Map<string, number>();

export function nextCounter(key: string): number {
  const next = (counters.get(key) ?? 0) + 1;
  counters.set(key, next);
  return next;
}

/**
 * A stable number derived from the run id, for models with `unique_together`
 * over numeric fields (IntervalSchedule, CrontabSchedule, SolarSchedule) where a
 * string suffix has nowhere to go.
 */
export function runSeed(): number {
  let hash = 0;
  for (const char of runId()) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash;
}
