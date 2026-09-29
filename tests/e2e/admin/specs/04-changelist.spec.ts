import { expect, test } from '../src/fixtures';
import { listCreated } from '../src/created';
import { isReadOnly } from '../src/expectations';
import { visit } from '../src/health';
import { models } from '../src/inventory';
import { chooseAutocomplete } from '../src/widgets';
import type { Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

const TODAY = new Date().toISOString().slice(0, 10);
const LAST_YEAR = new Date(Date.now() - 365 * 86_400_000).toISOString().slice(0, 10);
const TOMORROW = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);

/**
 * unfold renders `#changelist-filter` as a modal drawer gated on Alpine's
 * `filterOpen`, so it is display:none at every viewport until the "Filters"
 * control is clicked. Without this the filter assertions pass vacuously.
 */
async function openFilters(page: Page): Promise<boolean> {
  const panel = page.locator('#changelist-filter');
  if ((await panel.count()) === 0) return false;
  if (await panel.isVisible()) return true;

  const toggle = page.locator('[x-on\\:click="filterOpen = true"]').first();
  if ((await toggle.count()) === 0) return false;

  await toggle.click();
  await expect(panel).toBeVisible({ timeout: 10_000 });
  return true;
}

async function applyFilters(page: Page): Promise<boolean> {
  // list_filter_submit = True renders an explicit "Apply Filters" button.
  const apply = page.locator('#filter-form button[type="submit"]').first();
  if ((await apply.count()) === 0) return false;
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => null),
    apply.click(),
  ]);
  return true;
}

for (const model of models()) {
  if (!model.urls.changelist) continue;

  test(`changelist: ${model.label}`, async ({ page, probe }) => {
    const changelist = model.urls.changelist!;
    await visit(page, probe, changelist, { source: `changelist:${model.label}` });

    // Search, with a term that should hit and one that cannot.
    if (model.search_fields.length > 0) {
      const created = listCreated(model.label)[0];
      if (created) {
        await visit(page, probe, `${changelist}?q=${encodeURIComponent(created.token)}`, {
          source: `changelist:${model.label}:search-hit`,
        });
        await expect(page.locator('#result_list tbody tr')).not.toHaveCount(0);
      }
      // A UUID fragment and a JSON field are the two lookup shapes most likely to 500.
      for (const term of ['zz-no-such-row', "' OR 1=1 --", '0000']) {
        await visit(page, probe, `${changelist}?q=${encodeURIComponent(term)}`, {
          source: `changelist:${model.label}:search-miss`,
        });
      }
    }

    // Sorting: every sortable column header.
    await visit(page, probe, changelist, { source: `changelist:${model.label}` });
    const sortLinks = await page.locator('#result_list thead a[href*="o="]').evaluateAll((anchors) =>
      (anchors as HTMLAnchorElement[]).map((anchor) => anchor.getAttribute('href')!),
    );
    for (const href of sortLinks.slice(0, 12)) {
      await visit(page, probe, new URL(href, page.url()).toString(), {
        source: `changelist:${model.label}:sort`,
      });
    }

    // Pagination, including a deliberately out-of-range page.
    await visit(page, probe, `${changelist}?p=1`, { source: `changelist:${model.label}:page` });
    await visit(page, probe, `${changelist}?p=9999`, {
      source: `changelist:${model.label}:page-oob`,
      expectStatus: [200, 302, 404],
      soft: true,
    });
    await visit(page, probe, `${changelist}?all=`, { source: `changelist:${model.label}:show-all` });
  });
}

test('range-date filters accept normal and inverted ranges', async ({ page, probe }) => {
  for (const model of models()) {
    const dateFilters = model.list_filter.filter((name) =>
      ['created_at', 'date_joined', 'last_login', 'start_date', 'end_date'].includes(name),
    );
    if (dateFilters.length === 0 || !model.urls.changelist) continue;

    for (const field of dateFilters) {
      // RangeDateFilter renders <field>_from / <field>_to inputs.
      await visit(page, probe, `${model.urls.changelist}?${field}_from=${LAST_YEAR}&${field}_to=${TOMORROW}`, {
        source: `filter:${model.label}:${field}`,
      });
      // Inverted range must not explode.
      await visit(page, probe, `${model.urls.changelist}?${field}_from=${TOMORROW}&${field}_to=${LAST_YEAR}`, {
        source: `filter:${model.label}:${field}:inverted`,
      });
      // Garbage must not explode either.
      await visit(page, probe, `${model.urls.changelist}?${field}_from=not-a-date`, {
        source: `filter:${model.label}:${field}:garbage`,
        expectStatus: [200, 302],
        soft: true,
      });
    }
  }
});

test('checkbox and boolean filters apply', async ({ page, probe }) => {
  let exercised = 0;

  for (const model of models()) {
    if (!model.urls.changelist || model.list_filter.length === 0) continue;

    await visit(page, probe, model.urls.changelist, { source: `filter:${model.label}` });
    if (!(await openFilters(page))) continue;

    const checkbox = page.locator('#filter-form input[type="checkbox"]').first();
    if ((await checkbox.count()) > 0) {
      await checkbox.check();
      if (await applyFilters(page)) {
        exercised += 1;
        const body = await page.content();
        expect(body, `Django error filtering ${model.label}`).not.toContain('Exception Value:');
      }
    }

    // Plain boolean filters render as links inside the drawer.
    await visit(page, probe, model.urls.changelist, { source: `filter:${model.label}` });
    if (!(await openFilters(page))) continue;
    const link = page.locator('#changelist-filter a[href*="__exact="]').first();
    if ((await link.count()) > 0) {
      const href = await link.getAttribute('href');
      if (href) {
        await visit(page, probe, new URL(href, page.url()).toString(), {
          source: `filter:${model.label}:boolean`,
        });
        exercised += 1;
      }
    }
  }

  expect(exercised, 'no filter control was actually exercised').toBeGreaterThan(0);
});

test('autocomplete filters round-trip through /admin/autocomplete/', async ({ page, probe }) => {
  // BalanceAdmin and CommodityAdmin both use AutocompleteSelectFilter. The filter
  // select is named after the lookup (`user__id__exact`), not the field.
  const model = models().find((entry) => entry.label === 'db.Balance');
  expect(model?.urls.changelist, 'db.Balance admin missing').toBeTruthy();

  await visit(page, probe, model!.urls.changelist!, { source: 'filter:autocomplete' });
  expect(await openFilters(page), 'filter drawer would not open').toBe(true);

  // `.admin-autocomplete` is emitted by both unfold 0.59 (the vendor fork) and
  // 0.99 (this tree); `.unfold-filter-autocomplete` is 0.99-only.
  const select = page.locator('#filter-form select.admin-autocomplete').first();
  await expect(select, 'no autocomplete filter rendered').toHaveCount(1);
  const name = (await select.getAttribute('name'))!;

  await chooseAutocomplete(page, name, '');
  expect(await applyFilters(page), 'no Apply Filters button').toBe(true);
  expect(page.url()).toContain(encodeURIComponent(name).replace(/%5F/g, '_'));

  const body = await page.content();
  expect(body, 'Django error applying an autocomplete filter').not.toContain('Exception Value:');
});

test('read-only changelists expose no add button', async ({ page, probe }) => {
  for (const model of models().filter((entry) => isReadOnly(entry.label))) {
    await visit(page, probe, model.urls.changelist!, { source: `changelist:${model.label}:readonly` });
    await expect(page.locator(`a[href$="/admin/${model.app_label}/${model.model_name}/add/"]`)).toHaveCount(0);
  }
});
