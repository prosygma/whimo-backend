import { expect, type Locator, type Page } from '@playwright/test';
import { runId } from './run-scope';

/** Names the filler must never touch: CSRF, submit buttons, formset bookkeeping. */
const SKIP_NAMES = new Set([
  'csrfmiddlewaretoken',
  '_save',
  '_continue',
  '_addanother',
  '_selected_action',
  '_popup',
  'action',
  'select_across',
  'index',
]);

const SKIP_NAME_PATTERNS = [
  /-(TOTAL|INITIAL|MIN_NUM|MAX_NUM)_FORMS$/,
  /^initial-/,
  /__prefix__/,
  /-id$/,
  /-DELETE$/,
];

/** Always server-managed; these render as readonly text, but guard anyway. */
const READONLY_FIELDS = new Set(['id', 'created_at', 'updated_at', 'last_login', 'date_joined', 'short_id']);

export type ControlDescriptor = {
  name: string;
  tag: string;
  type: string;
  required: boolean;
  disabled: boolean;
  readOnly: boolean;
  maxLength: number;
  className: string;
  isMultiple: boolean;
  optionValues: string[];
};

export type FillResult = {
  filled: { name: string; value: string }[];
  skipped: string[];
  /** Controls the filler did not know how to handle — itself a finding. */
  unknown: string[];
};

export function formLocator(page: Page, modelName: string): Locator {
  // unfold's change_form.html: <form id="{{ opts.model_name }}_form" ... novalidate>
  return page.locator(`form#${modelName}_form`);
}

/**
 * unfold renders a `classes: ("collapse",)` fieldset as a native <details>, and
 * its controls are not interactable while it is shut. Open them all, then hand
 * back the form.
 */
export async function prepareForm(page: Page, modelName: string): Promise<Locator> {
  await page
    .locator('details:not([open])')
    .evaluateAll((nodes) => (nodes as HTMLDetailsElement[]).forEach((node) => (node.open = true)));
  return formLocator(page, modelName);
}

export async function describeControls(form: Locator): Promise<ControlDescriptor[]> {
  return form.locator('input, select, textarea').evaluateAll((nodes) =>
    (nodes as (HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement)[]).map((node) => ({
      name: node.name ?? '',
      tag: node.tagName.toLowerCase(),
      type: (node as HTMLInputElement).type ?? '',
      required: Boolean((node as HTMLInputElement).required),
      disabled: Boolean(node.disabled),
      readOnly: Boolean((node as HTMLInputElement).readOnly),
      maxLength: Number((node as HTMLInputElement).maxLength ?? -1),
      className: node.className ?? '',
      isMultiple: Boolean((node as HTMLSelectElement).multiple),
      optionValues:
        node.tagName.toLowerCase() === 'select'
          ? Array.from((node as HTMLSelectElement).options).map((option) => option.value)
          : [],
    })),
  );
}

function baseFieldName(name: string): string {
  // Inline controls are "<prefix>-<index>-<field>".
  const match = /^.+-\d+-(.+)$/.exec(name);
  return match ? match[1] : name;
}

function shouldSkip(control: ControlDescriptor): boolean {
  if (!control.name) return true;
  if (SKIP_NAMES.has(control.name)) return true;
  if (SKIP_NAME_PATTERNS.some((pattern) => pattern.test(control.name))) return true;
  if (control.disabled || control.readOnly) return true;
  if (READONLY_FIELDS.has(baseFieldName(control.name))) return true;
  return false;
}

function textValue(control: ControlDescriptor): string {
  const value = `E2E-${baseFieldName(control.name)}-${runId()}`;
  return control.maxLength > 0 && value.length > control.maxLength ? value.slice(0, control.maxLength) : value;
}

const TODAY = new Date().toISOString().slice(0, 10);

/**
 * Fill everything the DOM describes. Per-model overrides are applied afterwards
 * by the caller, so they always win.
 *
 * Autocomplete selects are deliberately left alone: they are select2-managed and
 * need a real AJAX round trip, handled by `chooseAutocomplete` in widgets.ts.
 */
export async function fillForm(
  page: Page,
  form: Locator,
  options: { skipNames?: string[]; password?: string } = {},
): Promise<FillResult> {
  const result: FillResult = { filled: [], skipped: [], unknown: [] };
  const explicitSkips = new Set(options.skipNames ?? []);
  await page
    .locator('details:not([open])')
    .evaluateAll((nodes) => (nodes as HTMLDetailsElement[]).forEach((node) => (node.open = true)));
  const password = options.password ?? `E2e-${runId()}-Pw!`;

  for (const control of await describeControls(form)) {
    if (shouldSkip(control) || explicitSkips.has(control.name)) {
      if (control.name) result.skipped.push(control.name);
      continue;
    }

    const locator = form.locator(`[name="${control.name}"]`).first();
    const record = (value: string) => result.filled.push({ name: control.name, value });

    if (control.tag === 'select') {
      if (/admin-autocomplete/.test(control.className)) {
        result.skipped.push(`${control.name} (autocomplete)`);
        continue;
      }
      const choices = control.optionValues.filter(Boolean);
      if (choices.length === 0) {
        result.unknown.push(`${control.name} (select with no selectable options)`);
        continue;
      }
      const pick = control.isMultiple ? choices.slice(0, 1) : choices[0];
      await locator.selectOption(pick);
      record(String(pick));
      continue;
    }

    if (control.tag === 'textarea') {
      await locator.fill(`E2E ${baseFieldName(control.name)} ${runId()}`);
      record('textarea');
      continue;
    }

    switch (control.type) {
      case 'hidden':
        result.skipped.push(`${control.name} (hidden)`);
        break;
      case 'checkbox':
        if (control.required) {
          await locator.check();
          record('checked');
        } else {
          result.skipped.push(`${control.name} (optional checkbox)`);
        }
        break;
      case 'radio':
        // e.g. Django 5.2's `usable_password` on the user add form.
        result.skipped.push(`${control.name} (radio, default kept)`);
        break;
      case 'number':
        await locator.fill('1');
        record('1');
        break;
      case 'email':
        await locator.fill(`e2e+${runId()}@example.test`);
        record('email');
        break;
      case 'url':
        await locator.fill(`https://example.test/${runId()}`);
        record('url');
        break;
      case 'password':
        await locator.fill(password);
        record('password');
        break;
      case 'date':
        await locator.fill(TODAY);
        record(TODAY);
        break;
      case 'time':
        await locator.fill('12:00:00');
        record('12:00:00');
        break;
      case 'text':
      case 'search':
      case '':
        if (/vDateField|vCustomDateField/.test(control.className)) {
          await locator.fill(TODAY);
          record(TODAY);
        } else if (/vTimeField/.test(control.className)) {
          await locator.fill('12:00:00');
          record('12:00:00');
        } else {
          const value = textValue(control);
          await locator.fill(value);
          record(value);
        }
        break;
      default:
        result.unknown.push(`${control.name} (input type=${control.type})`);
    }
  }

  return result;
}

export type SubmitButton = '_save' | '_continue' | '_addanother';
export type SubmitOutcome = 'saved' | 'validation-error' | 'server-error';

export type SubmitResult = {
  outcome: SubmitOutcome;
  url: string;
  status: number | null;
  errors: string[];
};

/**
 * unfold renders the submit buttons outside <form> and binds them with the HTML
 * `form=` attribute, so they must be targeted by name at page level, not as
 * descendants of the form.
 */
export async function submitForm(page: Page, button: SubmitButton = '_save'): Promise<SubmitResult> {
  const submit = page.locator(`[name="${button}"]`).first();
  await expect(submit).toBeVisible();

  const [response] = await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => null),
    submit.click(),
  ]);
  await page.waitForLoadState('load').catch(() => undefined);

  const status = response?.status() ?? null;
  const errors = await page.locator('ul.errorlist li, .errornote').allTextContents();
  const body = await page.content();

  let outcome: SubmitOutcome = 'saved';
  if (body.includes('Exception Value:') || body.includes('Traceback (most recent call last)')) {
    outcome = 'server-error';
  } else if (errors.length > 0) {
    outcome = 'validation-error';
  }

  return { outcome, url: page.url(), status, errors: errors.map((entry) => entry.trim()) };
}

/** The pk Django put in the URL after a save, if we landed on a change page. */
export function pkFromChangeUrl(url: string): string | null {
  return /\/admin\/[^/]+\/[^/]+\/([^/]+)\/change\//.exec(decodeURIComponent(url))?.[1] ?? null;
}
