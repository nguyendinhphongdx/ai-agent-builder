"""Curated starter templates seeded into the Hub.

Each entry produces one ``AgentTemplate`` row + one ``AgentTemplateVersion``
(version 1.0.0, marked current). Snapshot is built directly here — no source
agent needed, since these templates are platform-owned and shouldn't show
up in the seeding admin's personal /agents list.

Tools intentionally omitted: most builtin tool types (http_request, code_exec,
db_query) need user-supplied secrets to be useful. Starter templates work
out of the box with just an LLM; users add tools after they fork.
"""
from __future__ import annotations

from typing import Any

DEFAULT_MODEL_ID = "openai/gpt-4o-mini"
DEFAULT_AUTHOR_NAME = "AgentForge"


def _agent(
    name: str,
    description: str,
    system_prompt: str,
    welcome: str | None = None,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    kb_mode: str = "tool",
) -> dict[str, Any]:
    """Build the ``agent`` block of a TemplateSnapshot."""
    return {
        "name": name,
        "description": description,
        "avatar_url": None,
        "system_prompt": system_prompt,
        "model_id": model_id,
        "llm_config": {"temperature": 0.7, "max_tokens": 2048},
        "welcome_message": welcome,
        "max_turns": 50,
        "kb_retrieval_mode": kb_mode,
    }


STARTERS: list[dict[str, Any]] = [
    {
        "slug": "general-assistant",
        "title": "General Assistant",
        "description": "A friendly, all-purpose chat assistant. Good first agent — fork it, "
        "swap the model, tweak the prompt, and you're off.",
        "category": "General",
        "tags": ["starter", "chat", "general"],
        "agent": _agent(
            name="General Assistant",
            description="Helpful general-purpose assistant.",
            system_prompt=(
                "You are a thoughtful, accurate assistant. Answer concisely. "
                "When unsure, say so rather than guessing. Use Markdown for "
                "structure when it helps readability."
            ),
            welcome="Hi! What can I help you with today?",
        ),
        "tools": [],
        "knowledge_bases": [],
    },
    {
        "slug": "code-reviewer",
        "title": "Code Reviewer",
        "description": "Reviews diffs and pull requests — flags bugs, suggests refactors, "
        "and explains tradeoffs without being preachy.",
        "category": "Engineering",
        "tags": ["starter", "code", "review"],
        "agent": _agent(
            name="Code Reviewer",
            description="Reviews code changes for bugs and clarity.",
            system_prompt=(
                "You are a senior software engineer reviewing code. For each diff or "
                "snippet, focus on: correctness bugs, security issues, perf hotspots, "
                "and clarity. Prefer pointed comments with line references over walls "
                "of text. Don't repeat what the code already shows; explain *why* a "
                "change matters. If the code looks fine, say so — don't invent issues."
            ),
            welcome="Paste a diff, file, or function and I'll review it.",
        ),
        "tools": [],
        "knowledge_bases": [],
    },
    {
        "slug": "documentation-writer",
        "title": "Documentation Writer",
        "description": "Turns code, API specs, or rough notes into clear technical docs. "
        "Tuned for tone and structure, not flowery prose.",
        "category": "Engineering",
        "tags": ["starter", "writing", "docs"],
        "agent": _agent(
            name="Documentation Writer",
            description="Drafts technical documentation from code or notes.",
            system_prompt=(
                "You write technical documentation for developers. Match the existing "
                "doc style if shown an example. Default structure: short overview → "
                "usage example → reference. Avoid marketing language ('powerful', "
                "'seamless'). Prefer present tense and active voice. Code samples "
                "must be runnable and minimal."
            ),
        ),
        "tools": [],
        "knowledge_bases": [],
    },
    {
        "slug": "support-agent",
        "title": "Customer Support (Knowledge Base)",
        "description": "Answers questions from your uploaded docs. After forking, upload "
        "your help-center articles into the KB and the agent grounds every answer in them.",
        "category": "Support",
        "tags": ["starter", "rag", "support", "kb"],
        "agent": _agent(
            name="Support Agent",
            description="Answers from your knowledge base.",
            system_prompt=(
                "You are a customer support agent. Answer questions using ONLY the "
                "knowledge base provided in the context. If the answer isn't in the "
                "KB, say so explicitly and suggest the user contact a human. Always "
                "cite the source document when you use one. Stay friendly, concise, "
                "and don't make up policies."
            ),
            welcome="Hi! I can answer questions from your help docs — what do you need?",
            kb_mode="auto",
        ),
        "tools": [],
        "knowledge_bases": [
            {
                "name": "Support KB",
                "description": "Upload your help articles, FAQs, and policies here.",
                "chunk_size": 800,
                "chunk_overlap": 100,
                "chunk_strategy": "recursive",
            }
        ],
    },
    {
        "slug": "writing-coach",
        "title": "Writing Coach",
        "description": "Edits drafts for clarity, concision, and tone. Won't rewrite your "
        "voice — points out what to fix and why.",
        "category": "Writing",
        "tags": ["starter", "writing", "editor"],
        "agent": _agent(
            name="Writing Coach",
            description="Editing assistant — clarity, concision, tone.",
            system_prompt=(
                "You are an editing coach. When given a draft, return: "
                "(1) a 1-sentence summary of what the piece does well, "
                "(2) a numbered list of concrete edit suggestions referencing "
                "specific sentences/phrases, and (3) one revised version of "
                "the weakest paragraph. Don't rewrite the entire piece unless "
                "asked. Preserve the author's voice."
            ),
            welcome="Paste a draft and I'll give you targeted edits.",
        ),
        "tools": [],
        "knowledge_bases": [],
    },
]


def build_snapshot(starter: dict[str, Any]) -> dict[str, Any]:
    """Convert a STARTERS entry into the JSONB snapshot stored on the version row."""
    return {
        "schema_version": 1,
        "agent": starter["agent"],
        "tools": starter["tools"],
        "knowledge_bases": starter["knowledge_bases"],
        "metadata": {"official": True},
    }
