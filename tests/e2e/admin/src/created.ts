import fs from 'fs';
import path from 'path';
import { runId } from './run-scope';

export type CreatedObject = { label: string; pk: string; token: string; url: string };

function storePath(): string {
  return path.join(__dirname, '..', 'reports', `created-${runId()}.json`);
}

export function rememberCreated(entry: CreatedObject): void {
  const all = listCreated();
  all.push(entry);
  fs.mkdirSync(path.dirname(storePath()), { recursive: true });
  fs.writeFileSync(storePath(), `${JSON.stringify(all, null, 2)}\n`);
}

export function listCreated(label?: string): CreatedObject[] {
  const file = storePath();
  if (!fs.existsSync(file)) return [];
  const all = JSON.parse(fs.readFileSync(file, 'utf8')) as CreatedObject[];
  return label ? all.filter((entry) => entry.label === label) : all;
}

export function firstCreated(label: string): CreatedObject | undefined {
  return listCreated(label)[0];
}
