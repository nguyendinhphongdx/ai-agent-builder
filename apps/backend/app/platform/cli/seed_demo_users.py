"""Seed two demo users for local dev / preview environments.

Idempotent: re-running flips ``is_active`` / ``is_verified`` true and resets
the password (so credentials stay predictable for screencasts).

Usage:
    python -m app.platform.cli.seed_demo_users

Creates:
    alice@demo.local  / demo1234   (workspace owner — for demos)
    bob@demo.local    / demo1234   (regular member  — for sharing scenarios)
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.models.user import User
from app.modules.identity.auth.service import hash_password
from app.modules.identity.workspaces.service import ensure_personal_workspace
from app.platform.db.session import async_session_factory

DEMO_USERS = [
    {"email": "alice@demo.local", "name": "Alice (Demo)", "password": "demo1234"},
    {"email": "bob@demo.local", "name": "Bob (Demo)", "password": "demo1234"},
]


async def _seed() -> int:
    async with async_session_factory() as session:
        for spec in DEMO_USERS:
            result = await session.execute(
                select(User).where(User.email == spec["email"])
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    email=spec["email"],
                    hashed_password=hash_password(spec["password"]),
                    full_name=spec["name"],
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.flush()
                await ensure_personal_workspace(session, user)
                print(f"✓ Created {spec['email']} (id={user.id})")
            else:
                user.hashed_password = hash_password(spec["password"])
                user.is_active = True
                user.is_verified = True
                print(f"✓ Reset {spec['email']} (id={user.id})")

        await session.commit()
    print("\nLogin with any demo user using password: demo1234")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_seed()))
