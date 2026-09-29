import fs from 'fs';
import path from 'path';
import { expect, type Page, type Response } from '@playwright/test';
import type { VisitRecord } from './types';

export const LEDGER_PATH = path.join(__dirname, '..', 'reports', 'visits.jsonl');

/**
 * Markers of a Django technical-500 page. DEBUG=True is on locally precisely so
 * these render — a blank "Server Error (500)" would tell us nothing.
 */
const DJANGO_ERROR_MARKERS = [
  'TemplateDoesNotExist',
  'Exception Value:',
  'Traceback (most recent call last)',
  'Server Error (500)',
  "You're seeing this error because you have",
];

/**
 * Console noise that says nothing about the application.
 *
 * `whimo/contrib/templates/admin/index.html` loads chart.js from cdn.jsdelivr.net,
 * so an offline or firewalled box reports a failed request plus "Chart is not
 * defined" on *every* dashboard view. 00-smoke checks the CDN once and annotates
 * the run; downgrading it here keeps 300 pages from turning red for one cause.
 */
const IGNORED_CONSOLE = [
  /favicon\.ico/i,
  /Chart is not defined/i,
  /cdn\.jsdelivr\.net/i,
  /ResizeObserver loop/i,
  /\[DOM\] Input elements should have autocomplete/i,
];

/** Subresources whose failure is not the app's fault. */
const IGNORED_SUBRESOURCES = [/favicon\.ico/i, /cdn\.jsdelivr\.net/i, /fonts\.googleapis\.com/i];

export class PageProbe {
  readonly consoleErrors: string[] = [];
  readonly failedRequests: string[] = [];
  readonly badSubresources: string[] = [];

  constructor(private readonly page: Page) {
    page.on('console', (message) => {
      if (message.type() !== 'error') return;
      const text = message.text();
      if (IGNORED_CONSOLE.some((pattern) => pattern.test(text))) return;
      this.consoleErrors.push(text);
    });

    page.on('requestfailed', (request) => {
      const url = request.url();
      if (IGNORED_SUBRESOURCES.some((pattern) => pattern.test(url))) return;
      this.failedRequests.push(`${url} :: ${request.failure()?.errorText ?? 'unknown'}`);
    });

    page.on('response', (response) => {
      if (response.status() < 400) return;
      if (response.request().isNavigationRequest()) return;
      const url = response.url();
      if (IGNORED_SUBRESOURCES.some((pattern) => pattern.test(url))) return;
      this.badSubresources.push(`${response.status()} ${url}`);
    });
  }

  reset(): void {
    this.consoleErrors.length = 0;
    this.failedRequests.length = 0;
    this.badSubresources.length = 0;
  }

  snapshot(): Pick<VisitRecord, 'consoleErrors' | 'failedRequests' | 'badSubresources'> {
    return {
      consoleErrors: [...new Set(this.consoleErrors)],
      failedRequests: [...new Set(this.failedRequests)],
      badSubresources: [...new Set(this.badSubresources)],
    };
  }
}

export async function findDjangoError(page: Page): Promise<string | undefined> {
  const body = await page.content();
  const marker = DJANGO_ERROR_MARKERS.find((entry) => body.includes(entry));
  if (!marker) return undefined;

  // The technical-500 page puts the exception class and value in #summary.
  const summary = await page
    .locator('#summary h1, #summary .exception_value')
    .allTextContents()
    .catch(() => [] as string[]);
  return summary.length ? summary.join(' — ').trim() : marker;
}

export function recordVisit(record: VisitRecord): void {
  fs.mkdirSync(path.dirname(LEDGER_PATH), { recursive: true });
  fs.appendFileSync(LEDGER_PATH, `${JSON.stringify(record)}\n`);
}

export type VisitOptions = {
  source: string;
  /** Statuses that are correct for this URL, e.g. 403 on a read-only admin's add page. */
  expectStatus?: number[];
  /** Record the outcome but do not fail the test on it. */
  soft?: boolean;
};

/** Navigate, assert the page is healthy, and append the outcome to the coverage ledger. */
export async function visit(
  page: Page,
  probe: PageProbe,
  url: string,
  options: VisitOptions,
): Promise<VisitRecord> {
  probe.reset();

  let response: Response | null = null;
  let navigationError: string | undefined;
  try {
    response = await page.goto(url, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('load').catch(() => undefined);
  } catch (error) {
    navigationError = String(error);
  }

  const status = response?.status() ?? null;
  const djangoError = navigationError ?? (await findDjangoError(page));
  const allowed = options.expectStatus ?? [200];
  const statusOk = status !== null && allowed.includes(status);

  const record: VisitRecord = {
    url,
    status,
    ok: statusOk && !djangoError,
    source: options.source,
    title: await page.title().catch(() => undefined),
    djangoError,
    ...probe.snapshot(),
  };
  recordVisit(record);

  if (!options.soft) {
    expect(djangoError, `Django error page at ${url}: ${djangoError}`).toBeUndefined();
    expect(allowed, `Unexpected status ${status} at ${url}`).toContain(status);
  }
  return record;
}
