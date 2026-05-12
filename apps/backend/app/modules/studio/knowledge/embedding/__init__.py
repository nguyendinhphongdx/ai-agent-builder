"""Embedding provider registry + factory.

Providers are platform-owned (not per-user credentials). Admin configures
provider/model/dimensions via env (EMBEDDING_PROVIDER, EMBEDDING_MODEL,
EMBEDDING_DIMENSIONS) plus provider-specific keys (OPENAI_EMBEDDING_API_KEY, ...).

Usage:
    from app.modules.studio.knowledge.embedding import build_default, build_for_kb
    emb = build_default()         # uses settings.EMBEDDING_*
    emb = build_for_kb(kb)        # uses KB's snapshot fields
"""

# Import providers to trigger registration
from . import providers  # noqa: F401
from .factory import build_default, build_for_kb
from .registry import build, register

__all__ = ["build_default", "build_for_kb", "build", "register"]
