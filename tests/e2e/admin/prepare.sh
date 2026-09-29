#!/usr/bin/env bash
# Bring the local stack to the state the Playwright suite expects.
#
#   ./tests/e2e/admin/prepare.sh            # migrate, superuser, seed, inventory
#   ./tests/e2e/admin/prepare.sh --no-seed  # skip the factory-generated rows
set -euo pipefail

cd "$(dirname "$0")/../../.."

COMPOSE=(docker compose -p whimo-local -f deploy/docker-compose.local.yaml)
SEED=1
[[ "${1:-}" == "--no-seed" ]] && SEED=0

echo "==> Starting services"
"${COMPOSE[@]}" up -d

echo "==> Waiting for the API"
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/api/v1/system/healthcheck/ >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "==> Django checks"
"${COMPOSE[@]}" exec -T api poetry run ./manage.py check

echo "==> Migrations"
"${COMPOSE[@]}" exec -T api poetry run ./manage.py migrate --noinput

echo "==> Superuser (ignored if it already exists)"
"${COMPOSE[@]}" exec -T api poetry run ./manage.py createsuperuser --noinput 2>&1 | tail -1 || true

if [[ "$SEED" == "1" ]]; then
  echo "==> Seeding rows the admin cannot create (Transaction/Balance/Notification)"
  "${COMPOSE[@]}" exec -T api poetry run ./manage.py seed_e2e_data
fi

echo "==> Admin inventory"
"${COMPOSE[@]}" exec -T api poetry run ./manage.py dump_admin_inventory

echo "==> Ready: http://127.0.0.1:8000/admin/"
