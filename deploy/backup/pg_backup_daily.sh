#!/usr/bin/env bash
set -euo pipefail

#
# Daily Postgres backup for Docker Compose deployments.
# - Runs pg_dump inside the `postgres` service container
# - Stores .sql and .zip on the host
# - Deletes old backups locally (retention)
# - Copies the .zip to a remote host via FTP/FTPS (no password stored in script)
#

# PROJECT_ROOT defaults to the repository root (two levels up from this script).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-$PROJECT_ROOT/deploy/docker-compose.yaml}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/config/.env.${ENV:-local}}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/whimo-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

UPLOAD_METHOD="${UPLOAD_METHOD:-ftp}" # ftp | none

# FTP upload target (no password stored in script; pass via env or .netrc)
FTP_SCHEME="${FTP_SCHEME:-ftp}" # ftp or ftps
FTP_HOST="${FTP_HOST:-}"
FTP_PORT="${FTP_PORT:-}" # optional, e.g. 21 or 990
FTP_USER="${FTP_USER:-}"
FTP_PASS="${FTP_PASS:-}" # optional if using ~/.netrc
FTP_DIR="${FTP_DIR:-/backups/whimo}"
FTP_TLS_REQUIRED="${FTP_TLS_REQUIRED:-0}" # 1 => require TLS (for ftps)

DATE_TAG="$(date -u +%F_%H%M%S)"

mkdir -p "$BACKUP_DIR"

SQL_FILE="$BACKUP_DIR/whimo_${DATE_TAG}.sql"
ZIP_FILE="$BACKUP_DIR/whimo_${DATE_TAG}.sql.zip"

compose() {
  if [[ -f "$ENV_FILE" ]]; then
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
  else
    docker compose -f "$COMPOSE_FILE" "$@"
  fi
}

echo "Starting Postgres backup at $(date -u +'%F %T UTC')"
echo "Compose file: $COMPOSE_FILE"
echo "Env file: $ENV_FILE"
echo "Backup dir: $BACKUP_DIR"

# Dump database from within the running container.
# The postgres container already has POSTGRES_USER/POSTGRES_DB env vars.
compose exec -T "$POSTGRES_SERVICE" sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$SQL_FILE"

zip -j -q "$ZIP_FILE" "$SQL_FILE"
rm -f "$SQL_FILE"

echo "Created: $ZIP_FILE"

if [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  find "$BACKUP_DIR" -type f -name 'whimo_*.sql.zip' -mtime +"$RETENTION_DAYS" -print -delete || true
fi

if [[ "$UPLOAD_METHOD" == "none" ]]; then
  echo "UPLOAD_METHOD=none, skipping upload."
  echo "Done."
  exit 0
fi

if [[ "$UPLOAD_METHOD" != "ftp" ]]; then
  echo "Unsupported UPLOAD_METHOD: $UPLOAD_METHOD"
  exit 2
fi

if [[ "$FTP_SCHEME" != "ftp" && "$FTP_SCHEME" != "ftps" ]]; then
  echo "FTP_SCHEME must be ftp or ftps (got: $FTP_SCHEME)"
  exit 2
fi

if [[ -z "$FTP_HOST" || -z "$FTP_USER" ]]; then
  echo "FTP_HOST and FTP_USER must be set (use UPLOAD_METHOD=none to skip upload)."
  exit 2
fi

FTP_PORT_PART=""
if [[ -n "$FTP_PORT" ]]; then
  FTP_PORT_PART=":$FTP_PORT"
fi

FTP_BASE_URL="${FTP_SCHEME}://${FTP_HOST}${FTP_PORT_PART}${FTP_DIR%/}/"

echo "Uploading via FTP to: ${FTP_BASE_URL}"

# Prefer ~/.netrc (more secure for cron) but allow env password too.
AUTH_ARGS=()
if [[ -n "$FTP_PASS" ]]; then
  AUTH_ARGS+=(-u "${FTP_USER}:${FTP_PASS}")
else
  AUTH_ARGS+=(--netrc-optional -u "${FTP_USER}:")
fi

TLS_ARGS=()
if [[ "$FTP_SCHEME" == "ftps" || "$FTP_TLS_REQUIRED" == "1" ]]; then
  TLS_ARGS+=(--ssl-reqd)
fi

curl -f --ftp-create-dirs "${TLS_ARGS[@]}" "${AUTH_ARGS[@]}" -T "$ZIP_FILE" "${FTP_BASE_URL}"

echo "Done."
