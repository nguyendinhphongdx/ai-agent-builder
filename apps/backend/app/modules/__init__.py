"""Feature modules — one folder per business domain.

Each module follows the 4-layer convention from
``docs/conventions/``:
  router.py   — HTTP layer (FastAPI APIRouter)
  service.py  — business logic, async, takes db: AsyncSession
  schemas.py  — Pydantic request/response shapes
  models live in ``app.models.*`` so alembic can see them

Heavy engines used by these modules live in ``app.core``; cross-
cutting infrastructure (config, db, security, …) lives in
``app.platform``; async background loops live in
``app.background``.
"""
