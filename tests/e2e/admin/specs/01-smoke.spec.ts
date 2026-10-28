import { expect, test } from '../src/fixtures';
import { visit } from '../src/health';
import { loadInventory } from '../src/inventory';

test.describe.configure({ mode: 'serial' });

test('admin dashboard renders', async ({ page, probe }) => {
  const inventory = loadInventory();
  const record = await visit(page, probe, inventory.admin_index, { source: 'smoke' });

  // UNFOLD.DASHBOARD_CALLBACK runs AnalyticsService.get_analytics_data() on every
  // load, and the sidebar reverse_lazy()s every db_* changelist, so this single
  // page failing means the whole admin is down.
  await expect(page.locator('#nav-sidebar, [x-data]').first()).toBeAttached();
  expect(record.djangoError).toBeUndefined();

  if (record.failedRequests.length > 0) {
    // chart.js is loaded from cdn.jsdelivr.net by admin/index.html; note it once
    // instead of letting it colour every later page.
    test.info().annotations.push({
      type: 'degraded',
      description: `Dashboard subresources failed: ${record.failedRequests.join(', ')}`,
    });
  }
});

test('the page that fails in production renders locally', async ({ page, probe }) => {
  // The production traceback was on /admin/db/season/add/ (TemplateDoesNotExist:
  // unfold/widgets/text.html). EFI replaced Season with HarvestSeason, whose add
  // form carries the same unfold text widget.
  await visit(page, probe, '/admin/db/harvestseason/add/', { source: 'smoke' });

  const countryInput = page.locator('form#harvestseason_form [name="country"]');
  await expect(countryInput).toBeVisible();
  // Unfold's text widget, not Django's plain one.
  await expect(countryInput).toHaveClass(/border|rounded|px-3/);
});

test('every app index is reachable', async ({ page, probe }) => {
  const inventory = loadInventory();
  for (const app of inventory.app_list) {
    await visit(page, probe, `/admin/${app}/`, { source: 'smoke:app-index' });
  }
});

test('static assets for the admin are served', async ({ page, probe }) => {
  const record = await visit(page, probe, '/admin/db/commodity/', { source: 'smoke:static' });
  expect(
    record.badSubresources,
    `Admin CSS/JS failed to load: ${record.badSubresources.join(', ')}`,
  ).toEqual([]);
});
