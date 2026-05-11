"""Per-model USD pricing.

Hardcoded table for v1 — sufficient for the major providers and
predictable enough that admins can audit it. A future iteration
moves this to a ``model_pricing`` table so admins can update rates
without a deploy (and so the cost dashboard can replay historical
spend against the rates that were active at the time).

Prices are USD per 1M tokens, sourced from each provider's pricing
page. Rates shift; treat these as a baseline + override when a
deal moves the needle. Unknown models return zero — cost row gets
NULL and the analytics dashboard surfaces it as "unknown pricing".
"""
from __future__ import annotations

from decimal import Decimal

# Per 1M tokens, USD. {provider: {model_substring: (prompt_rate, completion_rate)}}.
# Matching is "longest prefix wins" so we can have "claude-sonnet" and
# "claude-sonnet-4" route differently.
_PRICING: dict[str, dict[str, tuple[Decimal, Decimal]]] = {
    "openai": {
        "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
        "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
        "gpt-4-turbo": (Decimal("10.00"), Decimal("30.00")),
        "gpt-4": (Decimal("30.00"), Decimal("60.00")),
        "gpt-3.5-turbo": (Decimal("0.50"), Decimal("1.50")),
        "o1": (Decimal("15.00"), Decimal("60.00")),
        "o1-mini": (Decimal("3.00"), Decimal("12.00")),
    },
    "anthropic": {
        "claude-opus-4": (Decimal("15.00"), Decimal("75.00")),
        "claude-sonnet-4": (Decimal("3.00"), Decimal("15.00")),
        "claude-haiku-4": (Decimal("0.80"), Decimal("4.00")),
        "claude-3-opus": (Decimal("15.00"), Decimal("75.00")),
        "claude-3-sonnet": (Decimal("3.00"), Decimal("15.00")),
        "claude-3-haiku": (Decimal("0.25"), Decimal("1.25")),
    },
    "google": {
        "gemini-2.5-pro": (Decimal("1.25"), Decimal("5.00")),
        "gemini-2.5-flash": (Decimal("0.075"), Decimal("0.30")),
        "gemini-1.5-pro": (Decimal("1.25"), Decimal("5.00")),
        "gemini-1.5-flash": (Decimal("0.075"), Decimal("0.30")),
    },
    # Self-hosted models — zero rate. We still log tokens so analytics
    # works; cost just rolls in as zero.
    "ollama": {},
}


def estimate_cost_usd(
    *,
    provider: str | None,
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> Decimal | None:
    """Return the estimated cost or ``None`` when pricing is unknown.

    Matches model by longest-prefix so "gpt-4o-2024-08-06" hits the
    "gpt-4o" entry. Adding a model release variant is a no-op as
    long as the prefix matches.
    """
    if not provider or not model:
        return None
    p = provider.lower().strip()
    m = (model or "").lower().strip()
    table = _PRICING.get(p)
    if table is None:
        return None

    # Longest-prefix match. Sort keys by length desc so "gpt-4o-mini"
    # wins over "gpt-4o" when both prefix the lookup.
    best: tuple[Decimal, Decimal] | None = None
    for key in sorted(table.keys(), key=len, reverse=True):
        if m.startswith(key):
            best = table[key]
            break
    if best is None:
        return None

    prompt_rate, completion_rate = best
    pt = Decimal(prompt_tokens or 0)
    ct = Decimal(completion_tokens or 0)
    # Rates are per 1M tokens.
    return (pt * prompt_rate + ct * completion_rate) / Decimal("1000000")
