"""Pytest fixtures shared across the test suite.

Pure unit tests don't need a DB or app instance — they import the module
under test directly. Integration tests (marked ``integration``) require a
live Postgres + run alembic at session start; they're opt-in via
``pytest -m integration``.

V1 of the test suite skips integration tests entirely — bootstrap focuses
on pure-unit coverage of the high-leverage modules (expression engine,
url guard, role hierarchy). DB-backed tests come later.
"""
from __future__ import annotations

import os

# Provide harmless defaults for any module that reads env at import time.
# Real values are required only for integration tests.
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-not-for-production")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/agentforge_test")
os.environ.setdefault("REDIS_URL", "")
