"""Seed or promote a root platform admin.

Usage:
    python -m app.platform.cli.seed_admin --email admin@example.com --password 'S3cret!'
    python -m app.platform.cli.seed_admin --email admin@example.com   # prompts (or $ADMIN_PASSWORD)
    python -m app.platform.cli.seed_admin --email admin@example.com --promote-only

Idempotent — re-running with an existing email promotes the row to
``role=admin`` and flips ``is_active`` / ``is_verified`` true. Pass
``--promote-only`` to leave the password untouched.

Run inside the backend container:
    docker compose exec backend python -m app.platform.cli.seed_admin --email ...
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.models.user import User
from app.modules.identity.auth.permissions import UserRole
from app.modules.identity.auth.service import hash_password
from app.platform.db.session import async_session_factory


async def _seed(
    email: str,
    password: str | None,
    name: str | None,
    promote_only: bool,
) -> int:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is not None:
            user.role = UserRole.ADMIN.value
            user.is_active = True
            user.is_verified = True
            if password and not promote_only:
                user.hashed_password = hash_password(password)
                print(f"✓ Promoted {email} → admin and reset password (id={user.id})")
            else:
                print(f"✓ Promoted {email} → admin (id={user.id})")
        else:
            if not password:
                print(
                    "ERROR: --password (or $ADMIN_PASSWORD, or interactive prompt) "
                    "required to create a new admin.",
                    file=sys.stderr,
                )
                return 1
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=name or "Root Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
            # Admins still get a personal workspace — they need somewhere
            # to land when they hit the dashboard, same as any user. Their
            # platform-level admin role is orthogonal to workspace tenancy.
            from app.modules.identity.workspaces.service import ensure_personal_workspace
            await ensure_personal_workspace(session, user)
            print(f"✓ Created admin {email} (id={user.id})")

        await session.commit()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="seed_admin",
        description="Create or promote a platform admin account.",
    )
    parser.add_argument("--email", required=True, help="Account email")
    parser.add_argument(
        "--password",
        help="Password to set. Omit to read $ADMIN_PASSWORD or prompt.",
    )
    parser.add_argument("--name", help="Display name (only used when creating)")
    parser.add_argument(
        "--promote-only",
        action="store_true",
        help="If the user already exists, only update role — leave password untouched.",
    )
    args = parser.parse_args()

    password = args.password
    if not password and not args.promote_only:
        password = os.environ.get("ADMIN_PASSWORD")
        if not password and sys.stdin.isatty():
            password = getpass.getpass("Password: ")

    return asyncio.run(_seed(args.email, password, args.name, args.promote_only))


if __name__ == "__main__":
    sys.exit(main())
