# Django admin end-to-end suite

Crawls the whole `/admin/` surface of this project: every registered page, every
in-admin link, and every form that can be submitted — filled with generated data
and actually saved.

## Why it exists

Production (`camertrace.cm`) served `TemplateDoesNotExist: unfold/widgets/text.html`
on `/admin/db/season/add/`. The cause was `unfold` missing from `INSTALLED_APPS`
while the admin classes still subclassed `unfold.admin.ModelAdmin`, so every
`CharField` asked for a template no loader could find. A crawl that opens every
admin page and checks for Django error pages catches that class of breakage
before a deploy does.

## Running it

```bash
# 1. bring the stack up, migrate, seed and dump the admin inventory
./tests/e2e/admin/prepare.sh

# 2. run the suite
cd tests/e2e/admin
npm ci
npx playwright install chromium   # first time only
npx playwright test

# 3. read the results
npx playwright show-report reports/html
jq '.summary' reports/admin-coverage.json
```

## What each spec covers

| spec | scope |
|---|---|
| `01-smoke` | login, dashboard, `/admin/db/season/add/` (the production failure), app indexes, static assets |
| `02-crawl` | every inventoried page, then a BFS following every in-admin link |
| `03-create` | one object per creatable model, in FK dependency order, through the real forms |
| `04-changelist` | search, every `list_filter`, column sorting, pagination, per model |
| `05-change-actions` | inline tabs, `_save` / `_continue` / `_addanother`, history, unfold detail actions, import/export, constance |
| `06-delete` | delete confirmation and the actual delete, plus the admins that correctly refuse it |

## Coverage evidence

The surface is enumerated twice and the two are reconciled in `globalTeardown`:

- `manage.py dump_admin_inventory` walks `admin.site._registry` and writes every
  derived URL to `.data/admin-inventory.json`;
- spec `02` crawls links from `/admin/` outward.

`reports/admin-coverage.json` lists every URL visited with its status, Django
error, console errors and failed subresources, plus any inventoried URL the crawl
never reached.

## Notes

- `workers: 1` and `fullyParallel: false`: the specs share one database and run in
  filename order.
- Viewport is 1920×1080 on purpose — below Tailwind's `2xl` breakpoint (1536px)
  unfold hides the changelist filter panel behind a toggle.
- Every generated value carries a per-run suffix, so the suite can be re-run
  against a database that already holds rows from earlier runs.
- `Transaction`, `Balance` and `Notification` use `ReadOnlyAdminMixin` and have no
  add form; `manage.py seed_e2e_data` creates them from `tests/factories` so their
  changelists, filters, exports and detail actions have something to act on.
