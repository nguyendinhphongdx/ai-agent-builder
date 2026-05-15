"""Unit tests for the in-process event bus.

Covers the documented contract: ordered fan-out, isolation between
event types, error containment, and idempotent re-subscription.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

import pytest

from app.platform.events import DomainEvent, EventBus

# ─── Fixtures ────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class _Created(DomainEvent):
    name: str


@dataclass(frozen=True, kw_only=True)
class _Deleted(DomainEvent):
    name: str


@pytest.fixture
def bus() -> EventBus:
    """Fresh bus per test so subscriptions don't leak across cases."""
    return EventBus()


# ─── Base type ────────────────────────────────────────────────────────


def test_domain_event_has_id_and_timestamp() -> None:
    e1 = _Created(name="a")
    e2 = _Created(name="a")
    assert isinstance(e1.event_id, UUID)
    assert e1.event_id != e2.event_id  # uuid4 per construction
    assert e1.occurred_at is not None
    # frozen
    with pytest.raises(Exception):
        e1.name = "b"  # type: ignore[misc]


# ─── Subscribe + emit ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_fans_out_to_subscribed_handlers(bus: EventBus) -> None:
    calls: list[str] = []

    @bus.on(_Created)
    async def first(event: _Created) -> None:
        calls.append(f"first:{event.name}")

    @bus.on(_Created)
    async def second(event: _Created) -> None:
        calls.append(f"second:{event.name}")

    await bus.emit(_Created(name="alpha"))

    assert calls == ["first:alpha", "second:alpha"]


@pytest.mark.asyncio
async def test_emit_with_no_handlers_is_noop(bus: EventBus) -> None:
    # Should not raise even when nobody listens.
    await bus.emit(_Created(name="silent"))


@pytest.mark.asyncio
async def test_handlers_for_different_event_types_are_isolated(
    bus: EventBus,
) -> None:
    created_calls = 0
    deleted_calls = 0

    @bus.on(_Created)
    async def on_created(_: _Created) -> None:
        nonlocal created_calls
        created_calls += 1

    @bus.on(_Deleted)
    async def on_deleted(_: _Deleted) -> None:
        nonlocal deleted_calls
        deleted_calls += 1

    await bus.emit(_Created(name="x"))
    await bus.emit(_Created(name="y"))
    await bus.emit(_Deleted(name="z"))

    assert created_calls == 2
    assert deleted_calls == 1


# ─── Error containment ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_failing_handler_does_not_break_peers(
    bus: EventBus, caplog: pytest.LogCaptureFixture
) -> None:
    survivor_calls: list[str] = []

    @bus.on(_Created)
    async def crasher(_: _Created) -> None:
        raise RuntimeError("boom")

    @bus.on(_Created)
    async def survivor(event: _Created) -> None:
        survivor_calls.append(event.name)

    with caplog.at_level(logging.ERROR, logger="agentforge.events"):
        await bus.emit(_Created(name="alpha"))

    # Survivor ran even though crasher raised.
    assert survivor_calls == ["alpha"]
    # And the error was logged with the event type name.
    assert any("_Created" in r.message for r in caplog.records)


# ─── Manual subscribe + clear ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_manual_subscribe_equivalent_to_decorator(bus: EventBus) -> None:
    seen: list[str] = []

    async def handler(event: _Created) -> None:
        seen.append(event.name)

    bus.subscribe(_Created, handler)
    await bus.emit(_Created(name="manual"))

    assert seen == ["manual"]


@pytest.mark.asyncio
async def test_clear_removes_all_handlers(bus: EventBus) -> None:
    seen: list[str] = []

    @bus.on(_Created)
    async def handler(event: _Created) -> None:
        seen.append(event.name)

    bus.clear()
    await bus.emit(_Created(name="ignored"))

    assert seen == []
