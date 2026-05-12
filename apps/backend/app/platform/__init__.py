"""Platform layer — cross-cutting infrastructure that every feature
module imports from but no feature owns.

What lives here:
  * config       — Pydantic Settings + env wiring
  * context      — request-scoped ContextVar (tenant, user, request id)
  * db           — SQLAlchemy engine + AsyncSession factory + Base
  * security     — crypto primitives (Fernet, JWT-shared helpers)
  * storage      — pluggable blob storage backends (local / S3 / GCS)
  * observability — Sentry, OpenTelemetry, Prometheus, JSON logging
  * permissions  — permission catalogue + role bindings + RBAC dep
  * schemas      — shared Pydantic response shapes
  * extractors   — file-format → text extractors used by ingestion
  * cli          — admin scripts (seed, backfill)
  * rate_limit   — per-route limiter helpers
  * dispatcher_client — outbound HTTP to the jobs dispatcher

The split from ``app.core`` is intentional: core/ holds the
business-domain engines (workflow runner, retrieval, ingestion,
KB connectors), while platform/ holds primitives those engines —
and every feature module — depend on.
"""
