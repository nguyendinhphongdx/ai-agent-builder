"""Phase 1.1 step-3 — backfill ``workspace_id`` on existing rows.

Usage:
    python -m app.cli.backfill_tenancy [--dry-run] [--batch-size 5000]
    python -m app.cli.backfill_tenancy --users-only      # phase A only
    python -m app.cli.backfill_tenancy --resources-only  # phase B only

Two phases, run in order:

  Phase A (users): for every ``User`` with ``default_workspace_id IS
  NULL``, materialise a personal Org+Workspace+owner-Member tuple via
  :func:`ensure_personal_workspace`. Idempotent — running the same
  command twice on a fully-backfilled DB is a no-op.

  Phase B (resources): for every resource table with a
  ``workspace_id`` column, set rows where it's NULL by deriving from
  the owning user's personal workspace (direct ``user_id`` link) or
  from a parent row's workspace (denormalised child tables).

Safe to run while traffic is live: every UPDATE is bounded by a LIMIT
batch + WHERE workspace_id IS NULL so concurrent writes don't get
overwritten. Dry-run prints per-table NULL counts without touching
data.

Once this run reports zero NULL rows across every table, the lock
migration in step 4 can flip every workspace_id column to NOT NULL.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.user import User
from app.workspaces.service import ensure_personal_workspace


# (table, parent_table, parent_fk_column, parent_id_column)
#   parent_table=None  → user_id direct lookup against users
#   parent_table=<name> → join through parent's workspace_id
_RESOURCE_TABLES: list[tuple[str, str | None, str | None]] = [
    # (table, parent_table_for_deriving_workspace_id, parent_fk_in_self)
    # Direct user_id link → users.default_workspace_id
    ("agents", None, None),
    ("tools", None, None),
    ("knowledge_bases", None, None),
    ("conversations", None, None),
    ("ai_credentials", None, None),
    ("personal_access_tokens", None, None),
    ("workflows", None, None),
    # Child tables — derive through a parent that already has workspace_id.
    # Order matters: parents must be backfilled FIRST.
    ("documents", "knowledge_bases", "knowledge_base_id"),
    ("document_chunks", "knowledge_bases", "knowledge_base_id"),
    ("messages", "conversations", "conversation_id"),
    ("workflow_nodes", "workflows", "workflow_id"),
    ("workflow_edges", "workflows", "workflow_id"),
    ("workflow_runs", "workflows", "workflow_id"),
]


async def _count_null_workspace(db: AsyncSession, table: str) -> int:
    result = await db.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE workspace_id IS NULL")
    )
    return int(result.scalar() or 0)


async def _phase_a_users(
    db: AsyncSession, *, dry_run: bool, batch_size: int
) -> int:
    """Materialise personal workspace for every user that lacks one.

    Returns the number of users provisioned (or that *would* be).
    """
    # Stream the user list in batches so a million-user DB doesn't OOM.
    total = 0
    offset = 0
    while True:
        rows = (
            await db.execute(
                select(User)
                .where(User.default_workspace_id.is_(None))
                .order_by(User.id)
                .offset(offset)
                .limit(batch_size)
            )
        ).scalars().all()
        if not rows:
            break

        for user in rows:
            if dry_run:
                total += 1
                continue
            await ensure_personal_workspace(db, user)
            total += 1
        if not dry_run:
            await db.commit()
        # When dry-run, ``default_workspace_id`` stays NULL → step the
        # offset forward so we don't re-read the same page.
        offset += len(rows) if dry_run else 0

    return total


async def _backfill_table_from_user(
    db: AsyncSession, table: str, *, dry_run: bool, batch_size: int
) -> int:
    """UPDATE rows where workspace_id IS NULL using owning user's
    default_workspace_id. For tables with a direct user_id column."""
    total = 0
    while True:
        if dry_run:
            count = await _count_null_workspace(db, table)
            return count
        # PostgreSQL UPDATE … FROM with subquery LIMIT. Batched so a
        # 50M-row UPDATE doesn't lock the table for minutes.
        result = await db.execute(
            text(
                f"""
                WITH targets AS (
                  SELECT id FROM {table}
                  WHERE workspace_id IS NULL
                  LIMIT :batch
                )
                UPDATE {table} AS t
                SET workspace_id = u.default_workspace_id
                FROM targets, users AS u
                WHERE t.id = targets.id
                  AND t.user_id = u.id
                  AND u.default_workspace_id IS NOT NULL
                """
            ),
            {"batch": batch_size},
        )
        await db.commit()
        affected = result.rowcount or 0
        total += affected
        if affected < batch_size:
            break
    return total


async def _backfill_child_table(
    db: AsyncSession,
    table: str,
    parent: str,
    fk_column: str,
    *,
    dry_run: bool,
    batch_size: int,
) -> int:
    """UPDATE rows where workspace_id IS NULL by inheriting from the
    parent row's workspace_id. Parent table must already be backfilled."""
    total = 0
    while True:
        if dry_run:
            count = await _count_null_workspace(db, table)
            return count
        result = await db.execute(
            text(
                f"""
                WITH targets AS (
                  SELECT id FROM {table}
                  WHERE workspace_id IS NULL
                  LIMIT :batch
                )
                UPDATE {table} AS t
                SET workspace_id = p.workspace_id
                FROM targets, {parent} AS p
                WHERE t.id = targets.id
                  AND t.{fk_column} = p.id
                  AND p.workspace_id IS NOT NULL
                """
            ),
            {"batch": batch_size},
        )
        await db.commit()
        affected = result.rowcount or 0
        total += affected
        if affected < batch_size:
            break
    return total


async def _phase_b_resources(
    db: AsyncSession, *, dry_run: bool, batch_size: int
) -> dict[str, int]:
    """Run the resource-table backfill in dependency order."""
    counts: dict[str, int] = {}
    for table, parent, fk_column in _RESOURCE_TABLES:
        before = await _count_null_workspace(db, table)
        if before == 0:
            counts[table] = 0
            continue
        if parent is None:
            updated = await _backfill_table_from_user(
                db, table, dry_run=dry_run, batch_size=batch_size
            )
        else:
            assert fk_column is not None
            updated = await _backfill_child_table(
                db, table, parent, fk_column, dry_run=dry_run, batch_size=batch_size
            )
        counts[table] = updated
    return counts


async def _run(
    *,
    dry_run: bool,
    batch_size: int,
    users_only: bool,
    resources_only: bool,
) -> int:
    started = time.time()
    async with async_session_factory() as session:
        if not resources_only:
            print(f"{'[dry-run] ' if dry_run else ''}Phase A — provisioning personal workspaces…")
            users_count = await _phase_a_users(
                session, dry_run=dry_run, batch_size=batch_size
            )
            verb = "would provision" if dry_run else "provisioned"
            print(f"  ✓ {verb} {users_count} user(s)")

        if not users_only:
            print(
                f"{'[dry-run] ' if dry_run else ''}Phase B — stamping workspace_id on resource rows…"
            )
            counts = await _phase_b_resources(
                session, dry_run=dry_run, batch_size=batch_size
            )
            total = sum(counts.values())
            for table, n in counts.items():
                if n == 0:
                    print(f"  · {table:30s} already clean")
                else:
                    verb = "would update" if dry_run else "updated"
                    print(f"  ✓ {table:30s} {verb} {n} row(s)")
            print(
                f"  {'Total (would)' if dry_run else 'Total'}: {total} row(s) "
                f"across {len(counts)} table(s)"
            )

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.2f}s.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="backfill_tenancy",
        description="Phase 1.1 step-3 backfill — stamp workspace_id on every legacy row.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write anything; print what would be updated.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Rows per UPDATE batch (default 5000). Smaller = lower lock contention.",
    )
    parser.add_argument(
        "--users-only",
        action="store_true",
        help="Run only Phase A (provision personal workspaces). Skip resource backfill.",
    )
    parser.add_argument(
        "--resources-only",
        action="store_true",
        help="Run only Phase B (stamp resource rows). Assumes Phase A already done.",
    )
    args = parser.parse_args()

    if args.users_only and args.resources_only:
        print("ERROR: --users-only and --resources-only are mutually exclusive.", file=sys.stderr)
        return 2

    return asyncio.run(
        _run(
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            users_only=args.users_only,
            resources_only=args.resources_only,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
