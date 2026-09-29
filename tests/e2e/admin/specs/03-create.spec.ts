import { expect, test } from '../src/fixtures';
import { rememberCreated } from '../src/created';
import { fillForm, prepareForm, pkFromChangeUrl, submitForm } from '../src/fill';
import { visit } from '../src/health';
import { modelByLabel } from '../src/inventory';
import { nextCounter, runId, runSeed } from '../src/run-scope';
import { addInlineRow, addNameVariant, chooseAutocomplete, openInlineTab, pickFilterHorizontal } from '../src/widgets';
import type { Page } from '@playwright/test';

// One shared database, and later specs target the rows created here.
test.describe.configure({ mode: 'serial' });

const RUN = () => runId();

/**
 * Save and record the new object for specs 04-06.
 *
 * Saves with `_continue` first: that lands on the change form, whose URL carries
 * the new pk. Reading the pk back off the changelist instead would be wrong for
 * admins without `search_fields` (django_celery_beat), where `?q=` is ignored and
 * the first row is some unrelated object.
 */
async function saveAndRemember(
  page: Page,
  label: string,
  token: string,
  button: '_save' | '_continue' | '_addanother' = '_save',
): Promise<string> {
  const saved = await submitForm(page, '_continue');
  expect(
    saved.outcome,
    `${label} save -> ${saved.outcome}: ${saved.errors.join(' | ')}`,
  ).toBe('saved');

  const pk = pkFromChangeUrl(saved.url);
  expect(pk, `${label} did not land on a change form after save: ${saved.url}`).toBeTruthy();
  rememberCreated({ label, pk: pk!, token, url: new URL(saved.url).pathname });

  if (button !== '_continue') {
    const final = await submitForm(page, button);
    expect(final.outcome, `${label} ${button} -> ${final.errors.join(' | ')}`).toBe('saved');
  }
  return pk!;
}

test('auth.Group', async ({ page, probe }) => {
  const token = `E2E-group-${RUN()}`;
  await visit(page, probe, modelByLabel('auth.Group').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'group');
  await form.locator('[name="name"]').fill(token);
  await pickFilterHorizontal(page, 'permissions', 2);

  await saveAndRemember(page, 'auth.Group', token);
});

test('db.CommodityGroup with name variants and an inline commodity', async ({ page, probe }) => {
  const token = `E2E-cg-${RUN()}`.slice(0, 50);
  await visit(page, probe, modelByLabel('db.CommodityGroup').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'commoditygroup');
  await form.locator('[name="name"]').fill(token);
  // JSONField driven by NameVariantsWidget; LANGUAGES is en-US / fr-FR / es-ES.
  // Returns false on trees that render unfold's ArrayWidget for this field instead.
  if (!(await addNameVariant(page, 'name_variants', 'fr-FR', `${token} FR`))) {
    test.info().annotations.push({ type: 'widget', description: 'name_variants is not NameVariantsWidget here' });
  }

  // CommodityInline (prefix "commodities", tab = True).
  if (await openInlineTab(page, 'commodities')) {
    const index = await addInlineRow(page, 'commodities');
    await form.locator(`[name="commodities-${index}-code"]`).fill(`EC${nextCounter('code')}${RUN()}`.slice(0, 20));
    await form.locator(`[name="commodities-${index}-name"]`).fill(`${token} inline`);
    await form.locator(`[name="commodities-${index}-unit"]`).fill('kg');
  }

  await saveAndRemember(page, 'db.CommodityGroup', token);
});

test('db.Commodity with a group autocomplete', async ({ page, probe }) => {
  const groupToken = `E2E-cg-${RUN()}`.slice(0, 50);
  const token = `E2E-commodity-${RUN()}`;
  await visit(page, probe, modelByLabel('db.Commodity').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'commodity');
  await form.locator('[name="code"]').fill(`EC${nextCounter('code')}${RUN()}`.slice(0, 20));
  await form.locator('[name="name"]').fill(token);
  await form.locator('[name="unit"]').fill('kg');
  await addNameVariant(page, 'name_variants', 'es-ES', `${token} ES`);
  await chooseAutocomplete(page, 'group', groupToken);

  await saveAndRemember(page, 'db.Commodity', token);
});

test('db.User via the unfold UserCreationForm', async ({ page, probe }) => {
  const token = `e2e_user_${RUN()}`;
  await visit(page, probe, modelByLabel('db.User').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'user');
  await form.locator('[name="username"]').fill(token);
  const password = `E2e-${RUN()}-Pw!`;
  await form.locator('[name="password1"]').fill(password);
  await form.locator('[name="password2"]').fill(password);

  await saveAndRemember(page, 'db.User', token);
});

test('db.Gadget with a user autocomplete', async ({ page, probe }) => {
  const userToken = `e2e_user_${RUN()}`;
  const identifier = `+1555${String(nextCounter('gadget')).padStart(3, '0')}${RUN().slice(-4)}`;
  await visit(page, probe, modelByLabel('db.Gadget').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'gadget');
  // GadgetType choices are (value, name): values are lowercase, labels uppercase.
  await form.locator('[name="type"]').selectOption('phone');
  await form.locator('[name="identifier"]').fill(identifier);
  await form.locator('[name="is_verified"]').check();
  await chooseAutocomplete(page, 'user', userToken);

  await saveAndRemember(page, 'db.Gadget', identifier);
});

test('db.Season with a commodity inline', async ({ page, probe }) => {
  const token = `E2E-season-${RUN()}`;
  const commodityToken = `E2E-commodity-${RUN()}`;
  await visit(page, probe, modelByLabel('db.Season').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'season');
  await form.locator('[name="name"]').fill(token);
  await form.locator('[name="description"]').fill(`Created by the admin e2e suite, run ${RUN()}.`);

  // Dates that make the row "current", so the dashboard's current-seasons panel
  // gets real data to render.
  const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
  const inAMonth = new Date(Date.now() + 30 * 86_400_000).toISOString().slice(0, 10);
  await form.locator('[name="start_date"]').fill(yesterday);
  await form.locator('[name="end_date"]').fill(inAMonth);

  if (await openInlineTab(page, 'season_commodities')) {
    const index = await addInlineRow(page, 'season_commodities');
    await chooseAutocomplete(page, `season_commodities-${index}-commodity`, commodityToken);
  }

  await saveAndRemember(page, 'db.Season', token);
});

test('db.ConversionRecipe with input and output inlines', async ({ page, probe }) => {
  const token = `E2E-recipe-${RUN()}`;
  const commodityToken = `E2E-commodity-${RUN()}`;
  await visit(page, probe, modelByLabel('db.ConversionRecipe').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'conversionrecipe');
  await form.locator('[name="name"]').fill(token);

  // ConversionInputInline / ConversionOutputInline are not tabbed.
  for (const [prefix, quantity] of [['inputs', '2.500000'], ['outputs', '1.000000']] as const) {
    await openInlineTab(page, prefix);
    const index = await addInlineRow(page, prefix);
    await chooseAutocomplete(page, `${prefix}-${index}-commodity`, commodityToken);
    await form.locator(`[name="${prefix}-${index}-quantity"]`).fill(quantity);
  }

  await saveAndRemember(page, 'db.ConversionRecipe', token);
});

test('django_celery_beat schedules', async ({ page, probe }) => {
  // All three schedule models carry a unique_together over numeric fields, where
  // a string run suffix has nowhere to go - derive the values from the run seed
  // instead, so the suite stays re-runnable.
  const seed = runSeed();

  const interval = modelByLabel('django_celery_beat.IntervalSchedule');
  await visit(page, probe, interval.urls.add!, { source: 'create' });
  let form = await prepareForm(page, 'intervalschedule');
  await form.locator('[name="every"]').fill(String((seed % 500) + 1));
  await form.locator('[name="period"]').selectOption('minutes');
  expect((await submitForm(page)).outcome).toBe('saved');

  const crontab = modelByLabel('django_celery_beat.CrontabSchedule');
  await visit(page, probe, crontab.urls.add!, { source: 'create' });
  form = await prepareForm(page, 'crontabschedule');
  for (const [name, value] of [
    ['minute', String(seed % 60)],
    ['hour', String(seed % 24)],
    ['day_of_week', '*'],
    ['day_of_month', '*'],
    ['month_of_year', '*'],
  ] as const) {
    await form.locator(`[name="${name}"]`).fill(value);
  }
  expect((await submitForm(page)).outcome).toBe('saved');

  const solar = modelByLabel('django_celery_beat.SolarSchedule');
  await visit(page, probe, solar.urls.add!, { source: 'create' });
  form = await prepareForm(page, 'solarschedule');
  await form.locator('[name="event"]').selectOption('sunrise');
  await form.locator('[name="latitude"]').fill(`${(seed % 80) + 1}.${String(seed % 1000000).padStart(6, '0')}`);
  await form.locator('[name="longitude"]').fill(`${(seed % 170) + 1}.${String(seed % 1000000).padStart(6, '0')}`);
  expect((await submitForm(page)).outcome).toBe('saved');
});

test('django_celery_beat.PeriodicTask', async ({ page, probe }) => {
  const token = `E2E-task-${RUN()}`;
  await visit(page, probe, modelByLabel('django_celery_beat.PeriodicTask').urls.add!, { source: 'create' });

  const form = await prepareForm(page, 'periodictask');
  await form.locator('[name="name"]').fill(token);
  // UnfoldPeriodicTaskForm swaps `task` for a plain text input and `regtask` for
  // an unfold select; PeriodicTaskForm.clean requires exactly one schedule, so
  // set the interval and leave crontab/solar/clocked empty.
  await form.locator('[name="task"]').fill('whimo.contrib.tasks.cleanup.cleanup_expired_transactions');
  const intervals = await form.locator('[name="interval"] option').evaluateAll((options) =>
    (options as HTMLOptionElement[]).map((option) => option.value).filter(Boolean),
  );
  expect(intervals.length, 'no IntervalSchedule to attach').toBeGreaterThan(0);
  await form.locator('[name="interval"]').selectOption(intervals[0]);
  await form.locator('[name="args"]').fill('[]');
  await form.locator('[name="kwargs"]').fill('{}');

  await saveAndRemember(page, 'django_celery_beat.PeriodicTask', token);
});

test('the read-only admins genuinely refuse writes', async ({ page, probe }) => {
  for (const label of ['db.Transaction', 'db.Balance', 'db.Notification']) {
    const model = modelByLabel(label);
    expect(model.permissions.add, `${label} should be read-only`).toBe(false);
    await visit(page, probe, model.urls.add!, { source: 'create:readonly', expectStatus: [403] });
  }
});

test('the generic filler understands every add form it can reach', async ({ page, probe }) => {
  // Not a save: this walks each add form and reports any control the filler does
  // not know how to handle, which is how an unsupported widget gets noticed.
  const unknowns: string[] = [];
  for (const model of [
    modelByLabel('db.Season'),
    modelByLabel('db.Commodity'),
    modelByLabel('db.CommodityGroup'),
    modelByLabel('db.ConversionRecipe'),
    modelByLabel('db.Gadget'),
  ]) {
    await visit(page, probe, model.urls.add!, { source: 'create:widget-audit' });
    const result = await fillForm(page, await prepareForm(page, model.model_name));
    unknowns.push(...result.unknown.map((entry) => `${model.label}: ${entry}`));
  }
  expect(unknowns, 'form controls the filler cannot handle').toEqual([]);
});
