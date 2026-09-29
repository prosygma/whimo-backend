import { expect, type Locator, type Page } from '@playwright/test';

/**
 * Handlers for the non-trivial widgets this admin actually uses. Every wait here
 * is on an observable effect of unfold's JS (a class, a counter, a visible panel),
 * never a fixed timeout — unfold initialises select2 and Alpine asynchronously.
 */

/** select2 marks the underlying <select> once it has taken it over. */
export async function waitForSelect2(select: Locator): Promise<void> {
  await expect(select).toHaveClass(/select2-hidden-accessible/, { timeout: 15_000 });
}

/**
 * Drive a select2 autocomplete: open it, type, wait for the real
 * /admin/autocomplete/ round trip, then pick a result.
 * Used by `autocomplete_fields` and by unfold's AutocompleteSelectFilter.
 */
export async function chooseAutocomplete(
  page: Page,
  selectName: string,
  term: string,
  options: { optionText?: string } = {},
): Promise<string> {
  const select = page.locator(`select[name="${selectName}"]`).first();
  await waitForSelect2(select);

  const selectId = await select.getAttribute('id');
  const opener = selectId
    ? page.locator(`#select2-${selectId}-container`)
    : select.locator('xpath=following-sibling::span[contains(@class,"select2")]').first();
  await opener.click();

  const search = page.locator('input.select2-search__field');
  await expect(search).toBeVisible();

  const [response] = await Promise.all([
    page.waitForResponse(
      (candidate) => candidate.url().includes('/admin/autocomplete/') && candidate.request().method() === 'GET',
      { timeout: 20_000 },
    ),
    search.fill(term),
  ]);

  if (response.status() !== 200) {
    throw new Error(`/admin/autocomplete/ returned ${response.status()} for ${selectName} (term "${term}")`);
  }

  const results = page.locator('.select2-results__option[role="option"]');
  await expect(results.first()).toBeVisible({ timeout: 15_000 });

  const firstText = (await results.first().innerText()).trim();
  if (/^No results/i.test(firstText)) {
    const body = await response.text();
    throw new Error(`Autocomplete for ${selectName} found nothing for "${term}". Response: ${body.slice(0, 300)}`);
  }

  const target = options.optionText
    ? results.filter({ hasText: options.optionText }).first()
    : results.first();
  const chosenText = (await target.innerText()).trim();
  await target.click();

  await expect(select).not.toHaveValue('');
  return chosenText;
}

/**
 * NameVariantsWidget (whimo/contrib/utils.py + admin/widgets/name_variants.html):
 * an Alpine x-for list of `<select name="<field>_language">` + `<input name="<field>_value">`
 * pairs, grown by clicking "Add translation". `value_from_datadict` rebuilds the
 * JSON from those two parallel lists.
 */
export async function addNameVariant(
  page: Page,
  fieldName: string,
  language: string,
  value: string,
): Promise<boolean> {
  const adder = page.getByText('Add translation', { exact: true }).first();
  if ((await adder.count()) === 0) {
    // Not this tree's NameVariantsWidget - the vendor fork renders unfold's
    // ArrayWidget for the same JSONField, which has no per-language rows.
    return false;
  }

  const values = page.locator(`input[name="${fieldName}_value"]`);
  const before = await values.count();

  await adder.click();
  // Waiting on the count is the Alpine-ready signal.
  await expect(values).toHaveCount(before + 1, { timeout: 10_000 });

  await page.locator(`select[name="${fieldName}_language"]`).nth(before).selectOption(language);
  await values.nth(before).fill(value);
  return true;
}

/** slugify() as Django applies it to an inline prefix for the tab anchor. */
export function slugify(value: string): string {
  return value.replace(/_/g, '-').toLowerCase();
}

/**
 * unfold renders `tab = True` inlines inside `x-show="activeTab == '<slug>'"`
 * panels: the fields exist in the DOM but are invisible until the tab is clicked.
 */
export async function openInlineTab(page: Page, prefix: string): Promise<boolean> {
  const link = page.locator(`#tabs-items a[href="#${prefix}"], #tabs-items a[href="#${slugify(prefix)}"]`).first();
  if ((await link.count()) === 0) return false;
  await link.click();
  await expect(page.locator(`#${prefix}-group`)).toBeVisible({ timeout: 10_000 });
  return true;
}

/**
 * Add a row to an inline formset. unfold's app.js clones `.empty-form`, rewrites
 * `__prefix__` and bumps TOTAL_FORMS; waiting on the counter guarantees both the
 * DOM row and the `formset:added` select2 re-init have fired.
 */
export async function addInlineRow(page: Page, prefix: string): Promise<number> {
  const total = page.locator(`#id_${prefix}-TOTAL_FORMS`);
  const before = Number(await total.inputValue());

  const addRow = page.locator(`#${prefix}-group .add-row a, #${prefix}-group .add-row`).first();
  await addRow.click();
  await expect(total).toHaveValue(String(before + 1), { timeout: 10_000 });
  return before;
}

/** Django's filter_horizontal (auth.Group.permissions): move one option left -> right. */
export async function pickFilterHorizontal(page: Page, fieldName: string, count = 1): Promise<void> {
  const from = page.locator(`#id_${fieldName}_from`);
  if ((await from.count()) === 0) return;

  const values = await from
    .locator('option')
    .evaluateAll((options, limit) =>
      (options as HTMLOptionElement[]).slice(0, limit).map((option) => option.value),
      count,
    );
  if (values.length === 0) return;

  await from.selectOption(values);
  // Django 5 renders the chooser as <button id="id_<field>_add">; older releases
  // used <a id="id_<field>_add_link">.
  await page.locator(`#id_${fieldName}_add, #id_${fieldName}_add_link`).first().click();
  await expect(page.locator(`#id_${fieldName}_to option`)).toHaveCount(values.length, { timeout: 10_000 });
}
