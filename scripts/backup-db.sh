#!/usr/bin/env bash
# Daily Postgres backup → rotating local copy + optional remote upload.
#
# What it does:
#   1. pg_dump --format=custom of the running Postgres container.
#   2. gzip-compressed timestamped file in $BACKUP_DIR.
#   3. Keeps the last $BACKUP_KEEP files; older ones deleted.
#   4. If $BACKUP_REMOTE_CMD is set, runs it with the new filename as
#      $1 so you can rclone/aws-cli/scp it offsite.
#
# What it does NOT do:
#   * Encrypt at rest. The dump contains every secret in the DB,
#     including Fernet-encrypted secrets (still ciphertext, but the
#     row metadata reveals usage). If your $BACKUP_DIR is shared,
#     wrap this in `age` or `gpg -e` before storing.
#   * Snapshot the uploads/ volume. Add a sibling rsync if you store
#     user uploads on local disk; skip if you're on S3.
#
# Usage:
#   * Local once: ./scripts/backup-db.sh
#   * Cron (recommended): 30 2 * * * /path/to/scripts/backup-db.sh >> /var/log/agentforge-backup.log 2>&1
#
# Env knobs (with sane defaults so the script works zero-config):
#   POSTGRES_CONTAINER  postgres        # docker compose service name
#   POSTGRES_DB         lc_agent
#   POSTGRES_USER       postgres
#   BACKUP_DIR          ./backups
#   BACKUP_KEEP         14              # keep last N daily dumps
#   BACKUP_REMOTE_CMD   ""              # optional offsite hook
#
# Test the restore drill quarterly — a backup you can't restore is
# fiction. See scripts/restore-db.sh for the reverse path.

set -euo pipefail

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-lc_agent}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
BACKUP_REMOTE_CMD="${BACKUP_REMOTE_CMD:-}"

mkdir -p "$BACKUP_DIR"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
out="${BACKUP_DIR}/agentforge-${ts}.dump.gz"

echo "[backup] starting at $(date -u -Iseconds)"
echo "[backup] container=${POSTGRES_CONTAINER} db=${POSTGRES_DB} out=${out}"

# --format=custom is pg_restore-friendly and parallelisable on restore.
# --no-owner so dump replays cleanly on a fresh cluster with a
# different owner.
docker exec -i "$POSTGRES_CONTAINER" \
    pg_dump --format=custom --no-owner --no-acl \
            -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    | gzip -9 > "$out"

size="$(du -h "$out" | cut -f1)"
echo "[backup] wrote ${out} (${size})"

# Rotate: keep last $BACKUP_KEEP files, drop older ones.
keep="$BACKUP_KEEP"
mapfile -t old < <(ls -1t "${BACKUP_DIR}"/agentforge-*.dump.gz 2>/dev/null | tail -n +"$((keep + 1))")
for f in "${old[@]:-}"; do
    [[ -n "$f" ]] || continue
    echo "[backup] rotating out ${f}"
    rm -f "$f"
done

# Optional offsite copy. Caller passes a one-line command; we pass
# the absolute filename as $1.
if [[ -n "$BACKUP_REMOTE_CMD" ]]; then
    abs="$(cd "$(dirname "$out")" && pwd)/$(basename "$out")"
    echo "[backup] uploading offsite: ${BACKUP_REMOTE_CMD} ${abs}"
    eval "$BACKUP_REMOTE_CMD" "$abs"
fi

echo "[backup] done at $(date -u -Iseconds)"
