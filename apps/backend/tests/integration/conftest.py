"""Integration-test fixtures.

Spins up a real Postgres+pgvector container once per session, applies
``alembic upgrade head`` against it, and hands each test a fresh
async session wrapped in a transaction that rolls back at teardown —
so tests share the migrated schema but never see each other's writes.

Opt-in: tests under ``tests/integration/`` carry the ``integration``
marker (auto-applied by ``pytest_collection_modifyitems`` below). CI
and local quick-loops run ``pytest -m "not integration"`` and skip
container startup entirely.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command

# Reuse the prod image so pgvector + pg16 behavior matches what migrations
# were written against. Keep this in sync with services/postgres/docker-compose.yml.
PG_IMAGE = "pgvector/pgvector:pg16"

# Repo root for backend (pyproject lives here, alembic.ini next to it).
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-mark every test in this dir with `integration` so users can
    opt out via `-m "not integration"` without decorating each file."""
    integration_marker = pytest.mark.integration
    for item in items:
        if "tests/integration" in str(item.path).replace("\\", "/"):
            item.add_marker(integration_marker)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    """Start a single Postgres container for the whole test session.

    Container takes ~3-5s to come up — that cost is paid once and
    amortized across every integration test.
    """
    container = PostgresContainer(
        image=PG_IMAGE,
        username="postgres",
        password="postgres",
        dbname="agentforge_test",
        driver=None,  # let us build URLs ourselves; testcontainers' default is psycopg2
    )
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def database_urls(postgres_container: PostgresContainer) -> tuple[str, str]:
    """Return (async_url, sync_url) for the running container."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname
    async_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
    sync_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return async_url, sync_url


@pytest.fixture(scope="session", autouse=True)
def _patch_settings_env(database_urls: tuple[str, str]) -> Iterator[None]:
    """Override DATABASE_URL{,_SYNC} env BEFORE app.config is imported by
    tests, then reload the settings singleton so any later import sees
    the container URLs.

    ``autouse=True`` so every integration-test module picks this up
    without having to depend on it explicitly.
    """
    async_url, sync_url = database_urls
    prev_async = os.environ.get("DATABASE_URL")
    prev_sync = os.environ.get("DATABASE_URL_SYNC")
    os.environ["DATABASE_URL"] = async_url
    os.environ["DATABASE_URL_SYNC"] = sync_url

    # Reload settings so anything that already imported `app.config`
    # picks up the new URLs. Same trick the alembic env uses.
    from app import config as app_config  # noqa: PLC0415

    app_config.settings = app_config.Settings()

    try:
        yield
    finally:
        if prev_async is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev_async
        if prev_sync is None:
            os.environ.pop("DATABASE_URL_SYNC", None)
        else:
            os.environ["DATABASE_URL_SYNC"] = prev_sync


@pytest.fixture(scope="session")
def _migrated_db(database_urls: tuple[str, str], _patch_settings_env: None) -> None:
    """Apply ``alembic upgrade head`` against the container.

    Runs once per session — schema persists for the full test run.
    Per-test isolation comes from the transaction-rollback wrapper in
    ``db_session`` below.
    """
    _, sync_url = database_urls
    cfg = AlembicConfig(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(scope="session")
async def async_engine(database_urls: tuple[str, str], _migrated_db: None):
    """Session-scoped async engine bound to the migrated container."""
    async_url, _ = database_urls
    engine = create_async_engine(async_url, echo=False, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncIterator[AsyncSession]:
    """Per-test async session wrapped in a transaction that always
    rolls back at teardown.

    Pattern: open a connection, begin an outer transaction, bind a
    session to that connection. Tests can call ``commit()`` and the
    ORM thinks it persisted, but the outer transaction is what really
    commits — and we roll it back instead. Result: no leaked rows
    between tests, no per-test alembic re-run.
    """
    connection = await async_engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()
