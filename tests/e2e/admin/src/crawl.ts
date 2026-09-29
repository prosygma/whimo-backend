import type { Page } from '@playwright/test';
import { shouldSkipUrl } from './expectations';

/**
 * Normalize a URL so the same page reached by different links is visited once:
 * drop the fragment, sort query params, and strip Django's changelist-filter
 * round-trip parameter.
 */
export function normalize(href: string, base: string): string | null {
  let url: URL;
  try {
    url = new URL(href, base);
  } catch {
    return null;
  }
  if (!['http:', 'https:'].includes(url.protocol)) return null;

  const baseUrl = new URL(base);
  if (url.host !== baseUrl.host) return null;
  if (!url.pathname.startsWith('/admin/')) return null;

  url.hash = '';
  url.searchParams.delete('_changelist_filters');
  url.searchParams.sort();
  return url.toString();
}

/** Every in-admin link on the current page, normalized and deduplicated. */
export async function collectLinks(page: Page, base: string): Promise<string[]> {
  const hrefs = await page.$$eval('a[href]', (anchors) =>
    (anchors as HTMLAnchorElement[])
      .filter((anchor) => anchor.target !== '_blank')
      .map((anchor) => anchor.getAttribute('href') ?? ''),
  );

  const seen = new Set<string>();
  for (const href of hrefs) {
    if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:')) continue;
    const normalized = normalize(href, base);
    if (normalized && !shouldSkipUrl(normalized)) seen.add(normalized);
  }
  return [...seen];
}

/**
 * Collapse a URL to the shape of the page it renders: /admin/db/season/<uuid>/change/
 * and /admin/db/season/<other-uuid>/change/ are the same template.
 *
 * The crawl visits a bounded number of each shape. Without this the crawl grows
 * with the row count - the seeded database already yields well over a thousand
 * change/history URLs - while adding no new coverage after the first few.
 */
export function urlPattern(url: string): string {
  return new URL(url, 'http://127.0.0.1:8000').pathname
    .replace(/\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\//gi, '/<uuid>/')
    .replace(/\/\d+\//g, '/<id>/');
}
