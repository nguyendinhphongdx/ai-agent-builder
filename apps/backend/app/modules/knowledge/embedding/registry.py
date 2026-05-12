"""Minimal provider dispatch. Each provider registers a builder function."""
from __future__ import annotations

from collections.abc import Callable

from langchain_core.embeddings import Embeddings

Builder = Callable[[str, int], Embeddings]

_PROVIDERS: dict[str, Builder] = {}


def register(provider: str, builder: Builder) -> None:
    """Register a builder for a provider name. Call at module import time."""
    _PROVIDERS[provider] = builder


def build(provider: str, model: str, dim: int) -> Embeddings:
    """Instantiate embeddings for (provider, model, dim).

    Raises ``ValueError`` if provider unknown. Provider-specific validation
    (missing env keys, bad model/dim) is raised by the builder itself.
    """
    builder = _PROVIDERS.get(provider)
    if builder is None:
        raise ValueError(
            f"Unknown embedding provider: {provider!r}. "
            f"Registered: {sorted(_PROVIDERS)}"
        )
    return builder(model, dim)


def registered_providers() -> list[str]:
    return sorted(_PROVIDERS)
