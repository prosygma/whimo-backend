import { expect, test } from '../src/fixtures';
import { collectLinks, normalize, urlPattern } from '../src/crawl';
import { expectedAddStatus, isDownloadUrl, shouldSkipUrl } from '../src/expectations';
import { recordVisit, visit } from '../src/health';
import { loadInventory, models } from '../src/inventory';
import type { VisitRecord } from '../src/types';
import { BASE_URL } from '../playwright.config';

test.describe.configure({ mode: 'serial' });

const MAX_PAGES = Number(process.env.CRAWL_MAX_PAGES ?? 2000);
/** How many instances of each URL shape to visit; CRAWL_PER_PATTERN=0 means all. */
const PER_PATTERN = Number(process.env.CRAWL_PER_PATTERN ?? 5);

/**
 * A crawl must not stop at the first broken page — one failure would hide every
 * other one. Pages are visited softly and the failures are reported together.
 */
function reportFailures(failures: VisitRecord[], what: string): void {
  const summary = failures
    .map((entry) => `  ${entry.status ?? '---'} ${entry.url}\n      ${entry.djangoError ?? 'unexpected status'}`)
    .join('\n');
  expect(failures.length, `${failures.length} ${what} failed:\n${summary}`).toBe(0);
}

test('every inventoried admin page is healthy', async ({ page, probe }) => {
  test.setTimeout(10 * 60_000);
  const failures: VisitRecord[] = [];

  const check = async (url: string, source: string, expectStatus?: number[]) => {
    const record = await visit(page, probe, url, { source, expectStatus, soft: true });
    const allowed = expectStatus ?? [200];
    if (record.djangoError || !allowed.includes(record.status ?? 0)) failures.push(record);
  };

  for (const model of models()) {
    const { changelist, add, change, history } = model.urls;
    if (changelist) await check(changelist, `inventory:${model.label}`);
    if (add) await check(add, `inventory:${model.label}`, expectedAddStatus(model.label));
    if (change) await check(change, `inventory:${model.label}`);
    if (history) await check(history, `inventory:${model.label}`);
  }
  await check(loadInventory().password_change, 'inventory:password-change');

  reportFailures(failures, 'inventoried pages');
});

test('every in-admin link is followed', async ({ page, probe }) => {
  test.setTimeout(20 * 60_000);

  const start = normalize(loadInventory().admin_index, BASE_URL)!;
  const queue: string[] = [start];
  const seen = new Set<string>([start]);
  const perPattern = new Map<string, number>();
  const failures: VisitRecord[] = [];
  let processed = 0;
  let skippedByPattern = 0;

  const takePattern = (url: string): boolean => {
    if (PER_PATTERN === 0) return true;
    const pattern = urlPattern(url);
    const count = perPattern.get(pattern) ?? 0;
    if (count >= PER_PATTERN) return false;
    perPattern.set(pattern, count + 1);
    return true;
  };

  while (queue.length > 0 && processed < MAX_PAGES) {
    const url = queue.shift()!;
    processed += 1;

    if (isDownloadUrl(url)) {
      // Content-Disposition: attachment aborts page.goto, so downloads are
      // checked through the request context instead.
      const response = await page.request.get(url);
      const record: VisitRecord = {
        url,
        status: response.status(),
        ok: response.status() < 400,
        source: 'crawl:download',
        consoleErrors: [],
        failedRequests: [],
        badSubresources: [],
        notes: [`content-type: ${response.headers()['content-type'] ?? 'unknown'}`],
      };
      recordVisit(record);
      if (!record.ok) failures.push(record);
      continue;
    }

    const model = models().find((entry) => url.endsWith(`/admin/${entry.app_label}/${entry.model_name}/add/`));
    const allowed = model ? expectedAddStatus(model.label) : [200];
    const record = await visit(page, probe, url, { source: 'crawl', expectStatus: allowed, soft: true });
    if (record.djangoError || !allowed.includes(record.status ?? 0)) {
      failures.push(record);
      continue; // a broken page has no links worth following
    }

    for (const link of await collectLinks(page, BASE_URL)) {
      if (seen.has(link) || shouldSkipUrl(link)) continue;
      seen.add(link);
      if (!takePattern(link)) {
        skippedByPattern += 1;
        continue;
      }
      queue.push(link);
    }
  }

  console.log(
    `Crawled ${processed} admin URLs across ${perPattern.size} distinct page shapes ` +
      `(${skippedByPattern} extra instances skipped, ${queue.length} left in queue).`,
  );
  expect(processed, 'crawl found no pages').toBeGreaterThan(10);
  expect(queue.length, `crawl hit the ${MAX_PAGES}-page cap`).toBe(0);

  reportFailures(failures, 'crawled pages');
});
