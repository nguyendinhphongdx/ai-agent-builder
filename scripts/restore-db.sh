#!/usr/bin/env bash
# Restore Postgres from a backup-db.sh dump.
#
# DESTRUCTIVE: drops + recreates the target database. Confirm prompt
# unless RESTORE_FORCE=1 is set (CI / scripted DR drills).
#
# Usage:
#   ./scripts/restore-db.sh ./backups/agentforge-20260515T020000Z.dump.gz
#
# Env knobs (mirror backup-db.sh):
#   POSTGRES_CONTAINER  postgres
#   POSTGRES_DB         lc_agent
#   POSTGRES_USER       postgres
#   RESTORE_FORCE       (unset)  set to 1 to skip the confirm prompt

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <dump.gz>" >&2
    exit 64
fi

dump="$1"
if [[ ! -f "$dump" ]]; then
    echo "[restore] file not found: $dump" >&2
    exit 66
fi

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-lc_agent}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

if [[ "${RESTORE_FORCE:-0}" != "1" ]]; then
    echo "WARNING: this will DROP and recreate database '${POSTGRES_DB}'"
    echo "         on container '${POSTGRES_CONTAINER}'."
    read -r -p "Type the database name to confirm: " confirm
    if [[ "$confirm" != "$POSTGRES_DB" ]]; then
        echo "[restore] aborted (input did not match)"
        exit 1
    fi
fi

echo "[restore] dropping + recreating $POSTGRES_DB"
docker exec -i "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker exec -i "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"

echo "[restore] loading $dump"
gunzip -c "$dump" | docker exec -i "$POSTGRES_CONTAINER" \
    pg_restore --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "[restore] done — run 'alembic upgrade head' if the dump pre-dates current migrations"
