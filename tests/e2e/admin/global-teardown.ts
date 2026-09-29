import fs from 'fs';
import path from 'path';
import { LEDGER_PATH } from './src/health';
import { inventoryUrls } from './src/inventory';
import type { VisitRecord } from './src/types';

const COVERAGE_PATH = path.join(__dirname, 'reports', 'admin-coverage.json');

export default async function globalTeardown(): Promise<void> {
  if (!fs.existsSync(LEDGER_PATH)) return;

  const visits = fs
    .readFileSync(LEDGER_PATH, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line) as VisitRecord);

  // The ledger mixes absolute URLs (the crawler) with admin paths (the inventory
  // specs), so compare on the path.
  const toPath = (url: string): string => {
    try {
      return new URL(url, 'http://127.0.0.1:8000').pathname;
    } catch {
      return url;
    }
  };

  // Collapse repeat visits, keeping the worst outcome for each URL.
  const byUrl = new Map<string, VisitRecord>();
  for (const visit of visits) {
    const previous = byUrl.get(visit.url);
    if (!previous || (previous.ok && !visit.ok)) byUrl.set(visit.url, visit);
  }

  const visitedPaths = new Set([...byUrl.keys()].map(toPath));
  const visited = [...byUrl.keys()];
  const expected = inventoryUrls();
  const missed = expected.filter((url) => !visitedPaths.has(toPath(url)));
  const failures = [...byUrl.values()].filter((visit) => !visit.ok);
  const withConsoleErrors = [...byUrl.values()].filter((visit) => visit.consoleErrors.length > 0);
  const withBadSubresources = [...byUrl.values()].filter((visit) => visit.badSubresources.length > 0);

  const report = {
    generatedAt: new Date().toISOString(),
    summary: {
      urlsVisited: visited.length,
      inventoryUrls: expected.length,
      inventoryUrlsNotVisited: missed.length,
      pagesWithErrors: failures.length,
      pagesWithConsoleErrors: withConsoleErrors.length,
      pagesWithFailedSubresources: withBadSubresources.length,
    },
    inventoryUrlsNotVisited: missed,
    failures,
    consoleErrors: withConsoleErrors.map((visit) => ({ url: visit.url, errors: visit.consoleErrors })),
    failedSubresources: withBadSubresources.map((visit) => ({ url: visit.url, resources: visit.badSubresources })),
    visits: [...byUrl.values()].sort((a, b) => a.url.localeCompare(b.url)),
  };

  fs.mkdirSync(path.dirname(COVERAGE_PATH), { recursive: true });
  fs.writeFileSync(COVERAGE_PATH, `${JSON.stringify(report, null, 2)}\n`);

  console.log(
    `\nAdmin coverage: ${report.summary.urlsVisited} URLs visited, ` +
      `${report.summary.inventoryUrlsNotVisited} inventory URLs missed, ` +
      `${report.summary.pagesWithErrors} with errors. -> ${COVERAGE_PATH}`,
  );
}
