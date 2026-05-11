"""Canonical job type names. One source of truth so consumers,
producers, and dashboards never drift.

Convention: dotted, lowercase, ``<domain>.<verb>.<noun>``.
"""
from __future__ import annotations

# ─── Knowledge base ────────────────────────────────────────────────
JOB_KB_INGEST_DOCUMENT = "kb.ingest.document"
"""Process a freshly-uploaded document — extract, chunk, embed."""

JOB_KB_REINDEX = "kb.reindex"
"""Re-embed an entire KB (model swap, dim change, …)."""


# ─── Workflows ─────────────────────────────────────────────────────
JOB_WORKFLOW_RUN = "workflow.run"
"""Execute a workflow asynchronously. ``WorkflowRun`` row tracks
status; this Job row dedupes + holds dispatcher metadata."""

JOB_WORKFLOW_RUN_SCHEDULED = "workflow.run.scheduled"
"""Triggered by APScheduler when a ``scheduled_triggers`` row fires."""


# ─── Webhooks ──────────────────────────────────────────────────────
JOB_WEBHOOK_DELIVER = "webhook.deliver"
"""Outbound webhook POST with retry/backoff. Used by workflow
``webhook_outbound`` nodes once they exist; legacy
``asyncio.create_task`` in webhooks/router.py should migrate here."""


# ─── Mail (already routed through dispatcher; tracked here for visibility) ──
JOB_EMAIL_SEND = "email.send"
"""Outgoing transactional email (welcome, password reset, invite)."""


# ─── Embeddings batch ──────────────────────────────────────────────
JOB_EMBED_BATCH = "embed.batch"
"""Generate embeddings for an arbitrary text batch — used by
:func:`kb.reindex` and future RAG features."""


ALL_JOB_TYPES = (
    JOB_KB_INGEST_DOCUMENT,
    JOB_KB_REINDEX,
    JOB_WORKFLOW_RUN,
    JOB_WORKFLOW_RUN_SCHEDULED,
    JOB_WEBHOOK_DELIVER,
    JOB_EMAIL_SEND,
    JOB_EMBED_BATCH,
)
