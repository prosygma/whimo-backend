#!/usr/bin/env bash
#
# camertrace.cm (173.212.223.65) admin repair / deploy helper.
#
#   ./deploy/deploy-to-camertrace.sh --dry-run      inspect the server, change nothing
#   ./deploy/deploy-to-camertrace.sh --fix-admin    RECOMMENDED: repair the admin in place
#   ./deploy/deploy-to-camertrace.sh --full-upgrade fast-forward 5 commits (big change)
#
# The SSH password is asked for ONCE; the connection is multiplexed and reused.
#
# Companion document: deploy/DEPLOY-canonical-to-camertrace.md
#
set -euo pipefail

SSH_HOST="${SSH_HOST:-173.212.223.65}"
SSH_USER="${SSH_USER:-root}"
SSH_TARGET="$SSH_USER@$SSH_HOST"
REMOTE_DIR="${REMOTE_DIR:-/var/whimo-backend}"
ENV_NAME="${ENV_NAME:-local}"
API_CONTAINER="${API_CONTAINER:-deploy-api-1}"
STATIC_DIR="${STATIC_DIR:-/var/www/whimo-static}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/whimo-predeploy}"

MODE=""
case "${1:-}" in
  --dry-run)      MODE=dry ;;
  --fix-admin)    MODE=fix ;;
  --full-upgrade) MODE=full ;;
  -h|--help)      sed -n '2,12p' "$0" | sed 's/^# \?//'; exit 0 ;;
  *) echo "usage: $0 --dry-run | --fix-admin | --full-upgrade   (see --help)" >&2; exit 1 ;;
esac

SOCKET="/tmp/whimo-deploy-$$.sock"
bold() { printf '\033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
err()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }
step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

cleanup() { ssh -O exit -o ControlPath="$SOCKET" "$SSH_TARGET" 2>/dev/null || true; rm -f "$SOCKET"; }
trap cleanup EXIT

r() { ssh -o ControlPath="$SOCKET" "$SSH_TARGET" "$@"; }
# Capture remote output with a default. Note `|| true` INSIDE the substitution:
# `$(cmd || echo X)` captures BOTH cmd's output and X when cmd prints then fails
# (e.g. `grep -c` prints 0 and exits 1) — that produced "0 0" and a broken test.
rqd() { local out; out=$(ssh -o ControlPath="$SOCKET" "$SSH_TARGET" "$1" 2>/dev/null || true); printf '%s' "${out:-$2}"; }

step "Connecting to $SSH_TARGET (enter the password if prompted)"
ssh -o ControlMaster=yes -o ControlPath="$SOCKET" -o ControlPersist=15m \
    -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -fN "$SSH_TARGET"
bold "connected (reused for every later command; no further prompts)"

# ---------------------------------------------------------------- inspect ---
step "1. Server state"
REMOTE_URL=$(rqd  "cd $REMOTE_DIR && git remote get-url origin" "UNKNOWN")
REMOTE_HEAD=$(rqd "cd $REMOTE_DIR && git log --oneline -1" "UNKNOWN")
DIRTY=$(rqd       "cd $REMOTE_DIR && git status --porcelain | wc -l" "?")
UNFOLD=$(rqd      "cd $REMOTE_DIR && grep -c '^[[:space:]]*\"unfold\",' whimo/settings.py" "0")

echo "  path:       $REMOTE_DIR"
echo "  origin:     $REMOTE_URL"
echo "  HEAD:       $REMOTE_HEAD"
echo "  local edits: $DIRTY file(s)"
if [[ "$UNFOLD" -gt 0 ]] 2>/dev/null; then
  echo "  unfold in INSTALLED_APPS: yes"
else
  echo "  unfold in INSTALLED_APPS: NO   <-- cause of the admin outage"
fi

step "2. Uncommitted changes on the server (these are NOT in any git remote)"
r "cd $REMOTE_DIR && git status --short" || true

step "3. Required environment variables"
ENV_PATH="$REMOTE_DIR/config/.env.$ENV_NAME"
MISSING=()
for v in DJANGO_SECRET_KEY POSTGRES_PASSWORD REDIS_PASSWORD EMAIL_HOST_PASSWORD \
         DJANGO_SUPERUSER_PASSWORD SMS_TELNYX_API_KEY SMS_TELNYX_SENDER_ID \
         SMS_TELNYX_MESSAGING_PROFILE_ID; do
  if r "grep -qE '^(export )?$v=' $ENV_PATH" 2>/dev/null; then
    printf '  present  %s\n' "$v"
  else
    printf '  MISSING  %s\n' "$v"
    MISSING+=("$v")
  fi
done
echo
echo "  NOTE: SMS_TELNYX_* are only required by the NEWER code (--full-upgrade)."
echo "        --fix-admin keeps the server on its current commit and does not need them."

step "4. Bug markers in the deployed source"
echo "  \"pk\" entries in HistoricalRecords(excluded_fields=...): $(rqd "cd $REMOTE_DIR && grep -rc '\"pk\",' whimo/db/models/ | awk -F: '{s+=\$2} END {print s+0}'" "?")"
echo "  NotificationAdmin readonly_fields:                       $(rqd "cd $REMOTE_DIR && grep -c readonly_fields whimo/contrib/admin/notifications.py" "0")"

if [[ "$MODE" == "dry" ]]; then
  echo; bold "--dry-run complete. Nothing was changed."
  echo "Next: --fix-admin (surgical, recommended) or --full-upgrade (5 commits, 62 files)."
  exit 0
fi

# ------------------------------------------------------------------- gate ---
step "5. Confirm"
if [[ "$MODE" == "fix" ]]; then
cat <<EOF
--fix-admin will, on $SSH_HOST:
  - tar the whole working tree to $BACKUP_DIR (your $DIRTY local edits included)
  - back up the database
  - edit 3 things in $REMOTE_DIR:
      * uncomment the six "unfold*" entries in whimo/settings.py
      * drop the no-op "pk" entries from HistoricalRecords(excluded_fields=...)
      * add readonly_fields to NotificationAdmin
  - copy those files into the RUNNING $API_CONTAINER and restart it
    (no image rebuild: the running image is 3 months old and rebuilding it is a
     bigger, less predictable change than this repair)
  - refresh $STATIC_DIR

It does NOT change the commit, dependencies, or database schema.
The API is briefly unavailable during the container restart.
EOF
else
cat <<EOF
--full-upgrade will fast-forward the server 5 commits (62 files, +5386/-2162),
which brings Telnyx (needs the 3 missing env vars), django-unfold 0.99, the
poetry migration, and data migration 0004 that REWRITES name_variants on every
Commodity and CommodityGroup row.

It also has to reconcile the $DIRTY uncommitted local edits on the server.
Do --fix-admin first to restore service; treat this as a separate planned upgrade.
EOF
fi
echo
read -r -p "Type $( [[ "$MODE" == fix ]] && echo FIX || echo UPGRADE ) to continue: " CONFIRM
EXPECT=$( [[ "$MODE" == fix ]] && echo FIX || echo UPGRADE )
[[ "$CONFIRM" == "$EXPECT" ]] || { err "aborted"; exit 1; }

# ----------------------------------------------------------------- backup ---
STAMP=$(date +%Y%m%d%H%M%S)
step "6. Back up the working tree and the database"
r "mkdir -p $BACKUP_DIR"
r "tar czf $BACKUP_DIR/worktree-$STAMP.tar.gz -C $(dirname $REMOTE_DIR) $(basename $REMOTE_DIR)"
echo "  worktree: $BACKUP_DIR/worktree-$STAMP.tar.gz"
r "cd $REMOTE_DIR && ENV=$ENV_NAME BACKUP_DIR=$BACKUP_DIR UPLOAD_METHOD=none ./deploy/backup/pg_backup_daily.sh" \
  || warn "  backup script failed — continuing is your call (Ctrl-C to stop)"

if [[ "$MODE" == "full" ]]; then
  step "7. Fast-forward"
  r "cd $REMOTE_DIR && git remote get-url prosygma >/dev/null 2>&1 || git remote add prosygma https://github.com/prosygma/whimo-backend.git"
  r "cd $REMOTE_DIR && git fetch prosygma && git stash push -m predeploy-$STAMP && git merge --ff-only prosygma/main"
  warn "  your $DIRTY local edits are in 'git stash' — reapply with: git stash pop"
  step "8. Rebuild + migrate + restart"
  r "cd $REMOTE_DIR/deploy && ENV=$ENV_NAME docker compose build api"
  r "cd $REMOTE_DIR/deploy && ENV=$ENV_NAME docker compose run --rm api poetry run ./manage.py migrate"
  r "cd $REMOTE_DIR/deploy && ENV=$ENV_NAME docker compose up -d api celery-worker celery-beat"
else
  step "7. Apply the three fixes to $REMOTE_DIR"
  r "cd $REMOTE_DIR && python3 - <<'PY'
import pathlib, re
changed = []

# 1. unfold back into INSTALLED_APPS
p = pathlib.Path('whimo/settings.py'); s = p.read_text()
s2 = re.sub(r'^(\s*)#\s*(\"unfold(?:\.contrib\.[a-z_]+)?\",)$', r'\1\2', s, flags=re.M)
if s2 != s: p.write_text(s2); changed.append('settings.py: unfold re-enabled')

# 2. the no-op \"pk\" entries
n = 0
for f in sorted(pathlib.Path('whimo/db/models').glob('*.py')):
    t = f.read_text(); out = []; inx = False; hit = 0
    for line in t.splitlines(keepends=True):
        if 'excluded_fields=(' in line: inx = True; out.append(line); continue
        if inx:
            if line.strip() == '\"pk\",': hit += 1; continue
            if line.strip().startswith(')'): inx = False
        out.append(line)
    if hit: f.write_text(''.join(out)); n += hit
if n: changed.append(f'models: removed {n} no-op \"pk\" entries')

# 3. NotificationAdmin readonly_fields
p = pathlib.Path('whimo/contrib/admin/notifications.py'); s = p.read_text()
anchor = '(_(\"Metadata\"), {\"fields\": (\"id\", \"created_at\", \"updated_at\")}),\n    )\n'
if 'readonly_fields' not in s and anchor in s:
    p.write_text(s.replace(anchor, anchor + '\n    readonly_fields = (\"id\", \"created_at\", \"updated_at\")\n', 1))
    changed.append('notifications.py: readonly_fields added')

print('\n'.join('    ' + c for c in changed) or '    nothing to change (already fixed?)')
PY"

  step "8. Copy the fixed files into the running container and restart it"
  for f in whimo/settings.py whimo/contrib/admin/notifications.py; do
    r "docker cp $REMOTE_DIR/$f $API_CONTAINER:/app/$f" && echo "  copied $f"
  done
  r "for f in $REMOTE_DIR/whimo/db/models/*.py; do docker cp \$f $API_CONTAINER:/app/whimo/db/models/\$(basename \$f); done"
  echo "  copied whimo/db/models/*.py"
  warn "  these live in the container's writable layer: re-run --fix-admin after any"
  warn "  'docker compose up --force-recreate' or rebuild, until the fix is committed."
  r "docker restart $API_CONTAINER"
fi

# ------------------------------------------------------------------ check ---
step "9. Wait for the API"
ELAPSED=0; CODE=000
for _ in $(seq 1 30); do
  CODE=$(rqd "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/system/healthcheck/" "000")
  [[ "$CODE" == "200" ]] && { echo "  healthcheck 200 after ${ELAPSED}s"; break; }
  sleep 10; ELAPSED=$((ELAPSED + 10))
done
if [[ "$CODE" != "200" ]]; then
  err "API did not come back. Last 40 log lines:"
  r "docker logs $API_CONTAINER --tail 40" || true
  err "ROLLBACK: tar xzf $BACKUP_DIR/worktree-$STAMP.tar.gz -C $(dirname $REMOTE_DIR) && docker restart $API_CONTAINER"
  exit 1
fi

step "10. Refresh host static files"
r "rm -rf /tmp/whimo-static-new && docker cp $API_CONTAINER:/app/static /tmp/whimo-static-new"
r "mkdir -p $STATIC_DIR && rsync -a /tmp/whimo-static-new/ $STATIC_DIR/ && rm -rf /tmp/whimo-static-new"
r "ls $STATIC_DIR | sed 's/^/    /'"

step "11. Verify"
for u in /admin/ /admin/db/season/add/ /admin/db/commodity/ /admin/db/commoditygroup/; do
  printf "  direct  %-32s %s\n" "$u" "$(rqd "curl -s -o /dev/null -w '%{http_code}' -H 'Host: camertrace.cm' http://127.0.0.1:8000$u" "000")"
done
for u in /api/v1/system/healthcheck/ /admin/; do
  printf "  public  %-32s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' "https://camertrace.cm$u" || echo 000)"
done

step "Done"
cat <<EOF
Confirm by hand at https://camertrace.cm/admin/ :
  /admin/db/season/add/   -> was TemplateDoesNotExist, expect the form to render
  a history page          -> was 500, expect 200
  admin CSS/JS loads      -> confirms step 10

Backups from this run:
  worktree  $BACKUP_DIR/worktree-$STAMP.tar.gz
  database  $BACKUP_DIR/ (newest .sql)

Rollback:
  ssh $SSH_TARGET
  tar xzf $BACKUP_DIR/worktree-$STAMP.tar.gz -C $(dirname $REMOTE_DIR)
  docker restart $API_CONTAINER
EOF
