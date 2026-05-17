"""Aggregation queries for the personal dashboard.

All queries scope by ``current_user_id``. We pick aggregate-only queries
where possible (no fetching rows just to count) so the dashboard stays
cheap even for power users with thousands of conversations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.conversation import Conversation
from app.models.message import Message
from app.modules.ops.dashboard.schemas import (
    AgentsStats,
    ConversationsStats,
    CurrencyRevenue,
    DashboardResponse,
    MessagesStats,
    RevenueSummary,
    TokensByModel,
    TokensStats,
)
from app.platform.context import current_user_id


async def _agents_stats(db: AsyncSession, user_id) -> AgentsStats:
    rows = await db.execute(
        select(Agent.status, func.count())
        .where(Agent.user_id == user_id)
        .group_by(Agent.status)
    )
    by_status = {status: count for status, count in rows.all()}
    return AgentsStats(total=sum(by_status.values()), by_status=by_status)


async def _conversations_stats(db: AsyncSession, user_id) -> ConversationsStats:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    row = await db.execute(
        select(
            func.count(Conversation.id),
            func.count(case((Conversation.created_at >= cutoff, 1))),
        ).where(Conversation.user_id == user_id)
    )
    total, last_30d = row.one()
    return ConversationsStats(total=total or 0, last_30d=last_30d or 0)


async def _messages_stats(db: AsyncSession, user_id) -> MessagesStats:
    """Count of assistant + user messages across the user's conversations."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    row = await db.execute(
        select(
            func.count(Message.id),
            func.count(case((Message.created_at >= cutoff, 1))),
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.user_id == user_id)
    )
    total, last_30d = row.one()
    return MessagesStats(total=total or 0, last_30d=last_30d or 0)


async def _tokens_stats(db: AsyncSession, user_id) -> TokensStats:
    """Tokens — total from the per-conversation counter, breakdown from messages.

    The counter on Conversation is what the chat runner increments live,
    so it's authoritative for the headline number even if `token_usage`
    JSONB on individual messages is missing.
    """
    total_row = await db.execute(
        select(func.coalesce(func.sum(Conversation.total_tokens), 0)).where(
            Conversation.user_id == user_id
        )
    )
    total = total_row.scalar_one() or 0

    # Per-model — only assistant messages carry `llm_model`. Pull
    # `total_tokens` out of the JSONB; rows missing it count as 0 so the
    # column doesn't silently disappear from the breakdown.
    tokens_expr = func.coalesce(
        func.sum(Message.token_usage["total_tokens"].astext.cast(Integer)),
        0,
    ).label("tokens")
    rows = await db.execute(
        select(Message.llm_model, tokens_expr)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.user_id == user_id)
        .where(Message.llm_model.is_not(None))
        .group_by(Message.llm_model)
        .order_by(tokens_expr.desc())
        .limit(10)
    )
    by_model = [
        TokensByModel(model=m or "unknown", tokens=int(t or 0))
        for m, t in rows.all()
    ]
    return TokensStats(total=int(total), by_model=by_model)


async def _revenue_stats(db: AsyncSession, user_id) -> RevenueSummary:
    """Author-side revenue — purchases of templates owned by the user.

    Free purchases (price=0) are excluded — they don't represent revenue.
    Platform fee is computed deterministically from the Stripe provider
    config's ``platform_fee_bps`` (defaults to ``DEFAULT_PLATFORM_FEE_BPS``
    when no row exists). MoMo currently takes no fee on our side —
    platform-collects, we settle authors out-of-band, full amount counted
    as gross + net.
    """
    from app.models.payment_provider_config import PROVIDER_STRIPE
    from app.modules.commerce.payments.checkout.providers.stripe import (
        DEFAULT_PLATFORM_FEE_BPS,
    )
    from app.modules.commerce.payments.config import get_provider_config

    stripe_config = await get_provider_config(PROVIDER_STRIPE)
    bps = (
        int(stripe_config.config.get("platform_fee_bps", DEFAULT_PLATFORM_FEE_BPS))
        if stripe_config
        else DEFAULT_PLATFORM_FEE_BPS
    )

    rows = await db.execute(
        select(
            AgentTemplatePurchase.currency,
            AgentTemplatePurchase.provider,
            AgentTemplatePurchase.status,
            func.count(),
            func.coalesce(func.sum(AgentTemplatePurchase.price_paid_cents), 0),
        )
        .join(
            AgentTemplate,
            AgentTemplate.id == AgentTemplatePurchase.template_id,
        )
        .where(AgentTemplate.user_id == user_id)
        .where(AgentTemplatePurchase.price_paid_cents > 0)
        .group_by(
            AgentTemplatePurchase.currency,
            AgentTemplatePurchase.provider,
            AgentTemplatePurchase.status,
        )
    )

    # Aggregate by currency across providers/status.
    by_currency: dict[str, dict[str, int]] = {}
    total_paid = 0
    total_refunded = 0
    for currency, provider, status, count, gross in rows.all():
        cur = (currency or "USD").upper()
        agg = by_currency.setdefault(
            cur,
            {"gross": 0, "fees": 0, "net": 0, "count": 0},
        )
        if status == "paid":
            total_paid += count
            agg["count"] += count
            agg["gross"] += int(gross or 0)
            # Stripe destination charges deduct the platform fee from
            # the author's transfer; MoMo doesn't (we settle manually).
            fee = (int(gross or 0) * bps // 10_000) if provider == "stripe" else 0
            agg["fees"] += fee
            agg["net"] += int(gross or 0) - fee
        elif status == "refunded":
            total_refunded += count
            # Refunds reverse both the gross + the fee, so their net
            # contribution is zero — don't add to aggregate counts.

    return RevenueSummary(
        by_currency=[
            CurrencyRevenue(
                currency=cur,
                gross_cents=v["gross"],
                fees_cents=v["fees"],
                net_cents=v["net"],
                count=v["count"],
            )
            for cur, v in sorted(by_currency.items())
        ],
        total_paid=total_paid,
        total_refunded=total_refunded,
    )


async def get_dashboard(db: AsyncSession) -> DashboardResponse:
    user_id = current_user_id()
    return DashboardResponse(
        agents=await _agents_stats(db, user_id),
        conversations=await _conversations_stats(db, user_id),
        messages=await _messages_stats(db, user_id),
        tokens=await _tokens_stats(db, user_id),
        revenue=await _revenue_stats(db, user_id),
    )
