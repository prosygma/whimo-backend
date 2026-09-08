# Postgres daily backup (Docker Compose)

This backs up the running `postgres` service from `deploy/docker-compose.yaml`, creates a `.zip`, keeps a retention window locally, then uploads the `.zip` to a remote server via FTP/FTPS.

There are two scripts:

- `deploy/backup/pg_backup_daily.sh` — recommended. Uses `curl` for FTP/FTPS, supports `~/.netrc`, and stores backups as `.sql.zip`.
- `backup_and_upload.sh` (repo root) — the original `ftp`-based job documented in §1.8, storing plain `.sql` files with 7-day retention.

Neither script stores credentials. All connection details come from environment variables.

## 1) Prepare FTP credentials (recommended: use `~/.netrc`)

Create `~/.netrc` on the app server (the one running Docker Compose):

```bash
cat > ~/.netrc <<'EOF'
machine <FTP_HOST>
login <FTP_USER>
password <YOUR_FTP_PASSWORD>
EOF

chmod 600 ~/.netrc
```

Alternatively, pass `FTP_PASS` via the environment (less secure for cron).

## 2) Install zip (if missing)

```bash
sudo apt-get update && sudo apt-get install -y zip
```

## 3) Run once (manual test)

```bash
sudo mkdir -p /var/backups/whimo-postgres
sudo chown -R "$USER":"$USER" /var/backups/whimo-postgres

chmod +x deploy/backup/pg_backup_daily.sh

BACKUP_DIR="/var/backups/whimo-postgres" \
RETENTION_DAYS="14" \
ENV="local" \
FTP_SCHEME="ftp" \
FTP_HOST="<FTP_HOST>" \
FTP_USER="<FTP_USER>" \
FTP_DIR="/backups/whimo" \
./deploy/backup/pg_backup_daily.sh
```

`PROJECT_ROOT` is auto-detected as the repository root; override it only if you run the script from outside the repo.

If `FTP_SCHEME="ftp"` fails due to TLS requirements, retry with:

```bash
FTP_SCHEME="ftps" FTP_TLS_REQUIRED="1" ./deploy/backup/pg_backup_daily.sh
```

## 4) Schedule daily with cron (02:00 UTC)

Edit cron:

```bash
crontab -e
```

Add (adjust the repo path and FTP details):

```cron
0 2 * * * BACKUP_DIR="/var/backups/whimo-postgres" RETENTION_DAYS="14" ENV="local" FTP_SCHEME="ftp" FTP_HOST="<FTP_HOST>" FTP_USER="<FTP_USER>" FTP_DIR="/backups/whimo" /var/www/html/whimo/whimo-backend/deploy/backup/pg_backup_daily.sh >> /var/log/whimo_pg_backup.log 2>&1
```

## Notes

- The scripts run `pg_dump` inside the `postgres` container, so you do **not** need to expose port 5432 publicly.
- Prefer `~/.netrc` so cron can run without embedding FTP passwords in `crontab`.
- `pg_backup_daily.sh` names backups like `whimo_YYYY-MM-DD_HHMMSS.sql.zip`; `backup_and_upload.sh` names them `whimo_YYYYMMDD_HHMMSS.sql`.
