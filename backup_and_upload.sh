#!/bin/bash
# =============================================================================
# backup_and_upload.sh
# Postgres backup → FTP upload → cleanup old backups (keep last 7 days)
#
# Credentials and targets are read from environment variables (never hardcode
# secrets in this file). Required: FTP_PASS. See deploy/backup/README.md.
#
# Example:
#   DB_USER=whimo_user DB_NAME=whimo \
#   FTP_HOST=ftp.example.com FTP_USER=backup FTP_PASS=*** \
#   FTP_REMOTE_DIR=/backups/whimo ./backup_and_upload.sh
# =============================================================================

# ─── CONFIG (override via environment) ───────────────────────────────────────
DB_USER="${DB_USER:-whimo_user}"
DB_NAME="${DB_NAME:-whimo}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/whimo}"   # local staging folder
KEEP_DAYS="${KEEP_DAYS:-7}"                       # days to retain on FTP

FTP_HOST="${FTP_HOST:-}"
FTP_USER="${FTP_USER:-}"
FTP_PASS="${FTP_PASS:-}"                          # MUST be provided via env
FTP_REMOTE_DIR="${FTP_REMOTE_DIR:-/backups/whimo}"

LOG_FILE="${LOG_FILE:-/var/log/whimo_backup.log}"
# ─────────────────────────────────────────────────────────────────────────────

if [[ -z "$FTP_HOST" || -z "$FTP_USER" || -z "$FTP_PASS" ]]; then
    echo "ERROR: FTP_HOST, FTP_USER and FTP_PASS must be set in the environment." >&2
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/whimo_${TIMESTAMP}.sql"

# Ensure local backup directory exists
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ─── STEP 1 · Create Postgres backup ─────────────────────────────────────────
log "Starting backup: $BACKUP_FILE"

docker compose exec -T postgres \
    pg_dump -U "$DB_USER" -d "$DB_NAME" -F c > "$BACKUP_FILE"

if [[ $? -ne 0 || ! -s "$BACKUP_FILE" ]]; then
    log "ERROR: Backup failed or file is empty. Aborting."
    exit 1
fi

log "Backup created successfully ($(du -sh "$BACKUP_FILE" | cut -f1))"

# ─── STEP 2 · Upload to FTP ───────────────────────────────────────────────────
log "Uploading to FTP $FTP_HOST …"

ftp -inv "$FTP_HOST" <<EOF
user $FTP_USER $FTP_PASS
binary
mkdir $FTP_REMOTE_DIR
cd $FTP_REMOTE_DIR
put $BACKUP_FILE $(basename "$BACKUP_FILE")
bye
EOF

if [[ $? -ne 0 ]]; then
    log "ERROR: FTP upload failed."
    exit 1
fi

log "Upload complete: $(basename "$BACKUP_FILE")"

# ─── STEP 3 · Remove remote backups older than KEEP_DAYS ─────────────────────
log "Cleaning FTP files older than ${KEEP_DAYS} days …"

# List remote files, filter those matching our naming pattern, delete old ones
ftp -inv "$FTP_HOST" <<EOF | grep "whimo_" | awk '{print $NF}' | while read -r remote_file; do
user $FTP_USER $FTP_PASS
cd $FTP_REMOTE_DIR
ls
bye
EOF
    # Extract date from filename: whimo_YYYYMMDD_HHMMSS.sql
    file_date=$(echo "$remote_file" | grep -oP '\d{8}(?=_)')
    if [[ -n "$file_date" ]]; then
        file_epoch=$(date -d "$file_date" +%s 2>/dev/null)
        cutoff_epoch=$(date -d "-${KEEP_DAYS} days" +%s)
        if [[ -n "$file_epoch" && "$file_epoch" -lt "$cutoff_epoch" ]]; then
            log "Deleting old remote file: $remote_file"
            ftp -inv "$FTP_HOST" <<FTPDEL
user $FTP_USER $FTP_PASS
cd $FTP_REMOTE_DIR
delete $remote_file
bye
FTPDEL
        fi
    fi
done

# ─── STEP 4 · Remove local staging copies older than KEEP_DAYS ───────────────
log "Cleaning local backups older than ${KEEP_DAYS} days …"
find "$BACKUP_DIR" -name "whimo_*.sql" -mtime +"$KEEP_DAYS" -exec rm -v {} \; | tee -a "$LOG_FILE"

log "Backup job finished successfully."
exit 0
