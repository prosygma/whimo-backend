import { expect, test } from '../src/fixtures';
import { listCreated } from '../src/created';
import { NO_DELETE_MODELS } from '../src/expectations';
import { visit } from '../src/health';
import { models } from '../src/inventory';

// Runs last: it removes the rows specs 03-05 created.
test.describe.configure({ mode: 'serial' });

/**
 * Django's delete_confirmation form is the one carrying <input name="post" value="yes">.
 * A bare `form [type=submit]` also matches the logout button hidden in the user
 * dropdown, which is never clickable.
 */
const DELETE_SUBMIT = 'form:has(input[name="post"]) [type="submit"]';

/** Children before parents, so PROTECT-ed FKs do not block the teardown. */
const DELETE_ORDER = [
  'django_celery_beat.PeriodicTask',
  'db.ConversionRecipe',
  'db.Season',
  'db.Gadget',
  'db.Commodity',
  'db.CommodityGroup',
  'auth.Group',
];

const PROTECTED_MESSAGE = /protected related objects|Cannot delete/i;

test('delete confirmation pages render', async ({ page, probe }) => {
  for (const label of DELETE_ORDER) {
    for (const created of listCreated(label)) {
      await visit(page, probe, created.url.replace('/change/', '/delete/'), {
        source: `delete-confirm:${label}`,
      });

      // Django renders one of two pages: the confirmation form, or - when an
      // on_delete=PROTECT reference still exists (CommodityGroup <- Commodity) -
      // a "protected related objects" page with no form at all. Both are correct;
      // a 500 would not be.
      const hasForm = (await page.locator(DELETE_SUBMIT).count()) > 0;
      if (!hasForm) {
        await expect(
          page.locator('body'),
          `${label} delete page has neither a confirm button nor a protected-objects notice`,
        ).toContainText(PROTECTED_MESSAGE);
      }
    }
  }
});

test('objects created by this run are deleted', async ({ page, probe }) => {
  const residual: string[] = [];

  for (const label of DELETE_ORDER) {
    for (const created of listCreated(label)) {
      const deleteUrl = created.url.replace('/change/', '/delete/');
      await visit(page, probe, deleteUrl, { source: `delete:${label}` });

      const body = await page.content();
      if (PROTECTED_MESSAGE.test(body)) {
        // on_delete=PROTECT (CommodityGroup <- Commodity): the admin must say so,
        // not raise. That is the assertion; the row simply stays.
        residual.push(`${label}:${created.pk} (protected)`);
        continue;
      }

      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => null),
        page.locator(DELETE_SUBMIT).first().click(),
      ]);

      const after = await page.content();
      expect(after, `Django error deleting ${label}`).not.toContain('Exception Value:');

      // The object should now be gone: Django redirects to the changelist with a
      // "doesn't exist" message, or 404s.
      const check = await page.request.get(created.url, { maxRedirects: 0 });
      expect([302, 404], `${label} still resolves after delete`).toContain(check.status());
    }
  }

  if (residual.length > 0) {
    test.info().annotations.push({ type: 'residual', description: residual.join(', ') });
  }
});

test('delete is refused where the admin forbids it', async ({ page, probe }) => {
  for (const model of models()) {
    if (!NO_DELETE_MODELS.includes(model.label.toLowerCase())) continue;
    if (!model.urls.delete) continue;

    await visit(page, probe, model.urls.delete, {
      source: `delete:${model.label}:forbidden`,
      expectStatus: [403],
    });
  }
});
