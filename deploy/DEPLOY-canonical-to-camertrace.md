# Deploying the canonical backend to camertrace.cm

Written 2026-09-18. **Not executed** — this machine has no credentials for the
target host. Someone with server access runs this.

> This is not a patch of what is running. It replaces the deployed application
> with a different codebase. Read §0 and §1 before touching anything.

---

## 0. What is actually being changed

camertrace.cm has been running `Coderkube-Node-js/WHIMO-backend` (commit `eccac83`).
That checkout was archived on 2026-09-18 to `~/whimo-fork-archive-2026-09-18/`
and removed locally. The tree being deployed is `prosygma/whimo-backend` @ `a9ff447`,
which differs substantially:

| | deployed now (fork) | being deployed (canonical) |
|---|---|---|
| django-unfold | 0.59.0 | 0.99.0 |
| lockfile | `uv.lock` | `poetry.lock` |
| `name_variants` widget | unfold `ArrayWidget` | project `NameVariantsWidget` |
| `name_variants` data shape | **list** | **dict** (migration 0004 converts) |
| migrations | through `0003` | through `0004` |
| extra code | — | `whimo/common/captcha.py` (Turnstile), Telnyx SMS |
| Firebase init | `if True:` (hard requirement) | behind `PUSH_NOTIFICATIONS_FCM_ENABLED` |

Fixes carried in: unfold restored to `INSTALLED_APPS`, the 13 no-op `"pk"` entries
removed from `HistoricalRecords(excluded_fields=...)`, and `readonly_fields` added
to `NotificationAdmin`. Verified locally — full admin crawl, 577 URLs, 0 errors.

---

## 1. Blockers — resolve before deploying

### 1.1 Three required env vars are missing (the app will NOT start without them)

`whimo/settings.py` reads these with no default, so a missing one raises
`ImproperlyConfigured` at import and the container dies on boot:

- `SMS_TELNYX_API_KEY`   (`settings.py:299`)
- `SMS_TELNYX_SENDER_ID` (`settings.py:301`)
- `SMS_TELNYX_MESSAGING_PROFILE_ID` (`settings.py:303`)

The production env file predates the Telnyx work and defines none of them
(checked against the archived copy). Add all three to `config/.env.<ENV>` on the
server before deploying. If Telnyx is not in use yet, set them to non-empty
placeholders and leave `SMS_TELNYX_ENABLED=False`; they only need to parse.

Also confirm present (they already were): `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`,
`REDIS_PASSWORD`, `EMAIL_HOST_PASSWORD`.

New optional vars with safe defaults, set only if wanted:
`CAPTCHA_TURNSTILE_SECRET_KEY`, `SENTRY_DSN`, `SENTRY_ENVIRONMENT`,
`PUSH_NOTIFICATIONS_FCM_ENABLED`.

### 1.2 Migration 0004 rewrites live rows

`0004_name_variants_to_dict` does two `AlterField`s plus a `RunPython` that
iterates every `Commodity` and `CommodityGroup` and converts `name_variants`
from a list to a dict keyed by language code. Production data is in list form,
so this **will** touch every one of those rows.

It has a reverse (`dict_to_list`), so it is reversible — but take the backup in §2
regardless, and note that the reverse is lossy if a language code is absent.

### 1.3 Firebase

The fork required `config/push/fcm.json` unconditionally. Canonical only loads it
when `PUSH_NOTIFICATIONS_FCM_ENABLED=True`. Keep the file in place; if push
notifications are expected to work, set that var to `True`.

---

## 2. Back up first, and verify the backup restores

The repo already ships `deploy/backup/pg_backup_daily.sh`, which runs `pg_dump`
inside the `postgres` service. On the server:

    cd /var/whimo-backend
    ENV=local BACKUP_DIR=/var/backups/whimo-predeploy UPLOAD_METHOD=none \
      ./deploy/backup/pg_backup_daily.sh

Then prove it is restorable — an unverified backup is not a backup:

    # spin a throwaway postgres, restore into it, count rows
    docker run -d --name restore-check -e POSTGRES_PASSWORD=x postgres:17.4-alpine
    sleep 10
    docker exec -i restore-check psql -U postgres -c 'CREATE DATABASE verify;'
    docker exec -i restore-check psql -U postgres -d verify < /var/backups/whimo-predeploy/<dump>.sql
    docker exec -i restore-check psql -U postgres -d verify \
      -c 'SELECT count(*) FROM commodities; SELECT count(*) FROM transactions;'
    docker rm -f restore-check

Record those counts. §5 checks them again after deploying.

---

## 3. Deploy

Server facts below come from `activities-backend.md` (2026-06-08), not from the
CI file — `ci/.gitlab-ci.yml` describes only a *dev* pipeline and its
`/var/www/whimo` path does **not** apply here.

| | value |
|---|---|
| host | `173.212.223.65` (`camertrace.cm`, `www.camertrace.cm`) |
| ssh user | `root` |
| project path | **`/var/whimo-backend`** |
| `ENV` | **`local`** -> env file `config/.env.local` |
| api container | `deploy-api-1` (gunicorn, not runserver) |
| host static dir | `/var/www/whimo-static/` |
| host nginx | `/etc/nginx/sites-enabled/whimo-test`, proxies `/admin/` -> `127.0.0.1:8000` |

The Docker `nginx` service never starts (host nginx already holds 80/443); that is
expected and not a fault.

### 3.1 First: confirm which codebase is actually on the box

    ssh root@173.212.223.65
    cd /var/whimo-backend
    git remote -v && git log --oneline -3
    grep -n '"unfold"' whimo/settings.py     # commented out == the broken fork

### 3.2 Add the three missing vars (§1.1) to `config/.env.local`

While editing, also confirm `DJANGO_SUPERUSER_PASSWORD` is set — without it the
entrypoint's `createsuperuser --noinput` fails silently on every start.

### 3.3 Update the code, rebuild, restart

    cd /var/whimo-backend
    git fetch origin && git checkout main && git pull      # -> prosygma/whimo-backend @ a9ff447+
    cd deploy
    ENV=local docker compose -f docker-compose.yaml build api
    ENV=local docker compose -f docker-compose.yaml up -d api celery-worker celery-beat

`whimo/entrypoint.sh` runs `migrate` on start, so **migration 0004 fires here**.
To separate the data migration from the release, run it first (§1.2):

    ENV=local docker compose -f docker-compose.yaml run --rm api \
      poetry run ./manage.py migrate db 0004

### 3.4 MANDATORY — refresh the host static files

gunicorn does not serve `/static/`; host nginx serves `/var/www/whimo-static/`,
which is a **copy** taken out of the container. It does not update on rebuild.
This release moves django-unfold 0.59 -> 0.99, whose static assets differ, so
skipping this leaves the admin with stale CSS/JS:

    docker cp deploy-api-1:/app/static /tmp/whimo-static-new
    rsync -a --delete /tmp/whimo-static-new/ /var/www/whimo-static/
    rm -rf /tmp/whimo-static-new

(`--delete` is deliberate here: 0.59 assets that no longer exist should go.)

No nginx reload is needed unless the nginx config itself changed.

## 4. If it does not come up

    docker logs deploy-api-1 --tail 100

`ImproperlyConfigured: Set the SMS_TELNYX_... environment variable` means §1.1 was
skipped. Add the vars and `up -d` again — no rollback needed, nothing migrated yet.

---

## 5. Verify

    curl -sS -o /dev/null -w '%{http_code}\n' https://camertrace.cm/api/v1/system/healthcheck/
    docker logs deploy-api-1 --tail 50

Then, logged into the admin:

| URL | expect |
|---|---|
| `/admin/` | 200, unfold dashboard renders |
| `/admin/db/season/add/` | **200** — this is the page that was returning `TemplateDoesNotExist` |
| `/admin/db/commodity/` | 200, and `name_variants` shows translations, not raw lists |
| `/admin/db/user/<pk>/history/<n>/` | 200 — was 500 before the `"pk"` fix |
| `/admin/db/notification/<pk>/history/<n>/` | 200 — was 500 before the `readonly_fields` fix |

Re-check the row counts from §2 to confirm migration 0004 did not lose rows.

The Playwright suite in `tests/e2e/admin/` can be pointed at the deployed host,
but note specs 03–06 **write and delete records**. Against production run only
the read-only ones:

    cd tests/e2e/admin
    ADMIN_BASE_URL=https://www.camertrace.cm \
    ADMIN_INVENTORY=<inventory dumped from the prod container> \
      npx playwright test specs/01-smoke.spec.ts specs/02-crawl.spec.ts

Generate that inventory on the server with:

    docker exec deploy-api-1 poetry run ./manage.py dump_admin_inventory --output /tmp/inv.json
    # then copy it off the host: docker cp deploy-api-1:/tmp/inv.json ./inv.json

---

## 6. Rollback

1. `cd /var/whimo-backend/deploy && ENV=local docker compose down`
2. Reverse the data migration if it ran:
   `ENV=local docker compose run --rm api poetry run ./manage.py migrate db 0003`
3. Check out the previous commit (or restore the fork from
   `~/whimo-fork-archive-2026-09-18/whimo-backend-edited-full.tar.gz`) and `up -d`.
4. If data looks wrong, restore the §2 dump into the `postgres` service.

---

## 7. Not verified from here

- No SSH access to `173.212.223.65` was available, so nothing below §1 has been
  executed or tested against the real host.
- How camertrace.cm is currently deployed is **unconfirmed** — the repo describes
  only a dev pipeline. Confirm the working directory, the `ENV` value, the branch,
  and whether images are built on the host or pulled.
- Whether the production database's `name_variants` values are uniformly lists.
  Sample before migrating:
  `SELECT id, name_variants FROM commodities LIMIT 5;`
- The `db.Transaction`/`Balance`/`Notification` admins are read-only by design
  (`ReadOnlyAdminMixin`); their `add/` returning 403 after deploy is correct.

---

## 8. Pre-existing production issues found in `activities-backend.md`

Not caused by this release, but worth fixing while you are on the box.

**`DJANGO_DEBUG=True` in production.** Recorded in §8 of that log. This is why the
original `TemplateDoesNotExist` rendered a full traceback with source lines,
settings and file paths to the public internet. Set `DJANGO_DEBUG=False` in
`config/.env.local`. Note the consequence: with DEBUG off, Django stops serving
anything itself and the `/var/www/whimo-static/` copy in §3.4 becomes the *only*
source of admin CSS/JS — so do §3.4 first, then flip DEBUG.

**`SECURE_PROXY_SSL_HEADER` is inverted.** `DJANGO_HTTP_X_FORWARDED_PROTO` is
unset, so it defaults to `http`, meaning `request.is_secure()` is true only when
nginx sends `X-Forwarded-Proto: http` — the opposite of the convention. Set
`DJANGO_HTTP_X_FORWARDED_PROTO=https`. Host nginx already sends that header on
both HTTPS server blocks, but deliberately omits it on the port-80 IP block, so
direct-IP admin access keeps working either way.

**Admin credentials are in plaintext** in `activities-backend.md` (§5). Rotate
that password and keep the file out of any repository.

**`DJANGO_CSRF_TRUSTED_ORIGINS`** already includes `https://camertrace.cm` and
`https://www.camertrace.cm` as of the 2026-06-08 fix — no change needed, but
confirm it survived any later edits, or admin login returns 403.
