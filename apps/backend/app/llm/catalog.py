"""Source of truth cho danh sách model/provider LLM hỗ trợ.

Backend dùng catalog này để:
  - Validate provider whitelist khi user tạo credential
  - Serve catalog qua endpoint GET /api/llm/catalog cho frontend

Frontend fetch catalog 1 lần (TanStack staleTime Infinity) và cache lại.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ModelCapability(str, Enum):
    tools = "tools"
    vision = "vision"
    json_mode = "json_mode"
    thinking = "thinking"


class ProviderEntry(BaseModel):
    id: str
    label: str
    description: str


class ModelCatalogEntry(BaseModel):
    id: str                                    # "openai/gpt-4o"
    provider: str
    model: str
    name: str
    context_window: int
    max_output: int
    capabilities: list[ModelCapability]
    description: str


PROVIDERS: list[ProviderEntry] = [
    ProviderEntry(id="openai", label="OpenAI", description="GPT-4o, GPT-4 Turbo, o-series"),
    ProviderEntry(id="anthropic", label="Anthropic", description="Claude Sonnet, Opus, Haiku"),
    ProviderEntry(id="google", label="Google", description="Gemini 2.5, 2.0, 1.5 Pro/Flash"),
    ProviderEntry(id="ollama", label="Ollama (Local)", description="Llama, Mistral, Code Llama"),
]


MODEL_CATALOG: list[ModelCatalogEntry] = [
    # OpenAI
    ModelCatalogEntry(
        id="openai/gpt-4o", provider="openai", model="gpt-4o", name="GPT-4o",
        context_window=128_000, max_output=16_384,
        capabilities=[ModelCapability.tools, ModelCapability.vision, ModelCapability.json_mode],
        description="Flagship multimodal model — strong reasoning, vision, tool use.",
    ),
    ModelCatalogEntry(
        id="openai/gpt-4o-mini", provider="openai", model="gpt-4o-mini", name="GPT-4o Mini",
        context_window=128_000, max_output=16_384,
        capabilities=[ModelCapability.tools, ModelCapability.vision, ModelCapability.json_mode],
        description="Cost-effective small model — faster, cheaper GPT-4o tier.",
    ),
    ModelCatalogEntry(
        id="openai/gpt-4-turbo", provider="openai", model="gpt-4-turbo", name="GPT-4 Turbo",
        context_window=128_000, max_output=4_096,
        capabilities=[ModelCapability.tools, ModelCapability.vision, ModelCapability.json_mode],
        description="Previous-gen flagship. Solid reasoning, slower than GPT-4o.",
    ),
    ModelCatalogEntry(
        id="openai/o3-mini", provider="openai", model="o3-mini", name="o3-mini",
        context_window=200_000, max_output=100_000,
        capabilities=[ModelCapability.tools, ModelCapability.thinking],
        description="Reasoning model optimized for coding and math with chain-of-thought.",
    ),
    # Anthropic
    ModelCatalogEntry(
        id="anthropic/claude-sonnet-4-20250514", provider="anthropic",
        model="claude-sonnet-4-20250514", name="Claude Sonnet 4",
        context_window=200_000, max_output=64_000,
        capabilities=[ModelCapability.tools, ModelCapability.vision, ModelCapability.thinking],
        description="Balanced flagship — state-of-the-art coding, tool use, agentic tasks.",
    ),
    ModelCatalogEntry(
        id="anthropic/claude-opus-4-20250514", provider="anthropic",
        model="claude-opus-4-20250514", name="Claude Opus 4",
        context_window=200_000, max_output=32_000,
        capabilities=[ModelCapability.tools, ModelCapability.vision, ModelCapability.thinking],
        description="Most capable Claude — best for complex reasoning and long horizons.",
    ),
    ModelCatalogEntry(
        id="anthropic/claude-haiku-4-5-20251001", provider="anthropic",
        model="claude-haiku-4-5-20251001", name="Claude Haiku 4.5",
        context_window=200_000, max_output=8_192,
        capabilities=[ModelCapability.tools, ModelCapability.vision],
        description="Fastest, cheapest Claude — low-latency agents, high-throughput tasks.",
    ),
    # Google
    ModelCatalogEntry(
        id="google/gemini-2.5-pro", provider="google", model="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        context_window=1_048_576, max_output=65_536,
        capabilities=[ModelCapability.tools, ModelCapability.vision, ModelCapability.thinking],
        description="Google's flagship — 1M context, deep thinking, multimodal.",
    ),
    ModelCatalogEntry(
        id="google/gemini-2.5-flash", provider="google", model="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        context_window=1_048_576, max_output=65_536,
        capabilities=[ModelCapability.tools, ModelCapability.vision],
        description="Fast, large-context model. Great for high-volume workloads.",
    ),
    ModelCatalogEntry(
        id="google/gemini-2.0-flash", provider="google", model="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        context_window=1_048_576, max_output=8_192,
        capabilities=[ModelCapability.tools, ModelCapability.vision],
        description="Earlier Flash generation — still very capable, lower cost.",
    ),
    ModelCatalogEntry(
        id="google/gemini-1.5-pro", provider="google", model="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        context_window=2_000_000, max_output=8_192,
        capabilities=[ModelCapability.tools, ModelCapability.vision],
        description="Legacy 2M-context model — best-in-class context length.",
    ),
    # Ollama
    ModelCatalogEntry(
        id="ollama/llama3.1", provider="ollama", model="llama3.1", name="Llama 3.1",
        context_window=128_000, max_output=4_096,
        capabilities=[ModelCapability.tools],
        description="Meta's open Llama 3.1 — runs locally via Ollama.",
    ),
    ModelCatalogEntry(
        id="ollama/mistral", provider="ollama", model="mistral", name="Mistral 7B",
        context_window=32_000, max_output=4_096,
        capabilities=[],
        description="Open-source 7B model from Mistral — fast local inference.",
    ),
    ModelCatalogEntry(
        id="ollama/codellama", provider="ollama", model="codellama", name="Code Llama",
        context_window=16_000, max_output=4_096,
        capabilities=[],
        description="Code-specialized Llama variant for local coding agents.",
    ),
]


def allowed_providers() -> set[str]:
    """Whitelist tên provider, dùng cho credential validator."""
    return {p.id for p in PROVIDERS}


def get_model(model_id: str) -> ModelCatalogEntry | None:
    return next((m for m in MODEL_CATALOG if m.id == model_id), None)
