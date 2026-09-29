import { expect, test } from '../src/fixtures';
import { listCreated } from '../src/created';
import { isReadOnly } from '../src/expectations';
import { prepareForm, submitForm } from '../src/fill';
import { visit } from '../src/health';
import { models, modelByLabel } from '../src/inventory';
import { runId } from '../src/run-scope';

test.describe.configure({ mode: 'serial' });

test('change forms render every inline tab', async ({ page, probe }) => {
  for (const created of listCreated()) {
    const model = models().find((entry) => entry.label === created.label);
    if (!model) continue;

    await visit(page, probe, created.url, { source: `change:${created.label}` });

    // Tabbed inlines are in the DOM but hidden until their tab is clicked; the
    // read-only ones (sold, bought, balance_set, ...) only run their
    // change_link_with_icon callables once rendered.
    const tabs = page.locator('#tabs-items a');
    for (let index = 0; index < (await tabs.count()); index += 1) {
      await tabs.nth(index).click();
      await page.waitForTimeout(0);
      const body = await page.content();
      expect(body, `Django error after opening a tab on ${created.label}`).not.toContain('Exception Value:');
    }
  }
});

test('save, save-and-continue and save-and-add-another all work', async ({ page, probe }) => {
  const created = listCreated('db.Season')[0] ?? {
    url: modelByLabel('db.Season').urls.change ?? '',
  };
  test.skip(!created.url, 'no season available');

  // _save -> changelist
  await visit(page, probe, created.url, { source: 'change:db.Season:_save' });
  const seasonForm = await prepareForm(page, 'season');
  await seasonForm.locator('[name="description"]').fill(`edited by run ${runId()}`);
  let result = await submitForm(page, '_save');
  expect(result.outcome, result.errors.join(' | ')).toBe('saved');
  expect(result.url).toContain('/admin/db/season/');

  // The edit must have persisted.
  await visit(page, probe, created.url, { source: 'change:db.Season:verify' });
  const reloaded = await prepareForm(page, 'season');
  await expect(reloaded.locator('[name="description"]')).toHaveValue(`edited by run ${runId()}`);

  // _continue -> stay on the change form with a success message
  result = await submitForm(page, '_continue');
  expect(result.outcome, result.errors.join(' | ')).toBe('saved');
  expect(result.url).toContain('/change/');
  // unfold renders messages as bare Tailwind divs with no class or role to hook
  // onto, so assert on the text the user actually sees.
  await expect(page.locator('body')).toContainText(/was changed successfully/i);

  // _addanother -> the add form
  result = await submitForm(page, '_addanother');
  expect(result.url).toContain('/add/');
});

test('read-only change forms have no save button and reject POST', async ({ page, probe }) => {
  for (const model of models().filter((entry) => isReadOnly(entry.label))) {
    if (!model.urls.change) continue;

    await visit(page, probe, model.urls.change, { source: `change:${model.label}:readonly` });
    await expect(page.locator('[name="_save"]')).toHaveCount(0);

    const cookies = await page.context().cookies();
    const csrf = cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
    const response = await page.request.post(model.urls.change, {
      form: { csrfmiddlewaretoken: csrf, _save: 'Save' },
      headers: { referer: new URL(model.urls.change, page.url()).toString(), 'X-CSRFToken': csrf },
      maxRedirects: 0,
    });
    expect(response.status(), `${model.label} accepted a POST it should refuse`).toBe(403);
  }
});

test('history views render for every simple_history model', async ({ page, probe }) => {
  for (const model of models()) {
    if (!model.urls.history) continue;
    await visit(page, probe, model.urls.history, { source: `history:${model.label}` });
  }
});

test('UserAdmin "Access Token" detail action', async ({ page, probe }) => {
  // Fall back to an existing row so this still runs when the spec is executed on
  // its own, without 03-create's per-run objects.
  const created = listCreated('db.User')[0] ?? { pk: modelByLabel('db.User').sample_pks[0] };
  test.skip(!created.pk, 'no user available');

  // unfold routes @action detail buttons at /<app>/<model>/<pk>/<func_name>/
  await visit(page, probe, `/admin/db/user/${created.pk}/generate_access_token/`, {
    source: 'action:generate_access_token',
  });
  expect(page.url()).toContain(`/admin/db/user/${created.pk}/change/`);
  await expect(page.locator('body')).toContainText(/Access Token/i);
});

test('UserAdmin password change form', async ({ page, probe }) => {
  const created = listCreated('db.User')[0] ?? { pk: modelByLabel('db.User').sample_pks[0] };
  test.skip(!created.pk, 'no user available');
  await visit(page, probe, `/admin/db/user/${created.pk}/password/`, { source: 'action:password' });
});

test('TransactionAdmin export and detail actions', async ({ page, probe }) => {
  const transaction = modelByLabel('db.Transaction');
  test.skip(!transaction.urls.change, 'no transactions seeded');

  const pk = transaction.sample_pks[0];

  // download_chain calls ExportActionMixin.export_admin_action, which renders the
  // export *form* page rather than streaming a file.
  await visit(page, probe, `/admin/db/transaction/${pk}/download_chain/`, {
    source: 'action:download_chain',
  });
  await expect(page.locator('#id_format, select[name="format"]').first()).toBeAttached();

  // download_geojson sends an attachment, so page.goto would abort; fetch it.
  const geojson = await page.request.get(`/admin/db/transaction/${pk}/download_geojson/`);
  expect(geojson.status(), 'download_geojson should not 500').toBeLessThan(500);

  // The changelist export form.
  await visit(page, probe, '/admin/db/transaction/export/', { source: 'action:export-form' });
  const format = page.locator('#id_format');
  if ((await format.count()) > 0) {
    const options = await format.locator('option').evaluateAll((nodes) =>
      (nodes as HTMLOptionElement[]).map((option) => option.value).filter(Boolean),
    );
    // The format select is by index, not by name: "0:csv", "1:tsv", ...
    const labels = await format.locator('option').evaluateAll((nodes) =>
      (nodes as HTMLOptionElement[]).map((option) => `${option.value}:${option.text}`),
    );
    const csv = labels.find((entry) => /:csv$/i.test(entry))?.split(':')[0] ?? options[0];
    await format.selectOption(csv);

    // Scope to the form that owns #id_format: a bare [type=submit] also matches
    // the logout button hidden in the user dropdown.
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 30_000 }).catch(() => null),
      page.locator('form:has(#id_format) [type="submit"]').first().click(),
    ]);
    expect(download, 'export produced no download').not.toBeNull();
    expect(await download!.path()).toBeTruthy();
    expect(download!.suggestedFilename()).toMatch(/\.csv$/i);
  }

  // Export-only: TransactionAdmin uses ExportActionMixin, not ImportExportMixin,
  // so no import view is registered. Django's catch-all turns /import/ into
  // /import/change/, which reports "doesn't exist" - assert that, not a 404.
  const importResponse = await page.request.get('/admin/db/transaction/import/', { maxRedirects: 0 });
  expect(importResponse.status(), '/import/ should not be a real view').toBe(302);
  expect(importResponse.headers().location).toContain('/import/change/');
  await visit(page, probe, '/admin/db/transaction/import/', { source: 'action:no-import-view' });
  await expect(page.locator('#id_import_file')).toHaveCount(0);
});

test('constance config page', async ({ page, probe }) => {
  const model = models().find((entry) => entry.app_label === 'constance');
  test.skip(!model, 'constance not registered');

  // CONSTANCE_BACKEND is set but settings define no CONSTANCE_CONFIG, and
  // unfold.contrib.constance is not installed - record whatever this does.
  const record = await visit(page, probe, model!.urls.changelist!, {
    source: 'constance',
    expectStatus: [200, 302, 403, 500],
    soft: true,
  });
  test.info().annotations.push({
    type: 'constance',
    description: `status=${record.status} error=${record.djangoError ?? 'none'}`,
  });
});
