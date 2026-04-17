---
id: backend-llm-providers
title: LLM Providers
domain: backend
tags: [llm, openai, anthropic, ollama, langchain, provider]
related: [backend-agents, backend-config]
summary: Unified LLM factory producing LangChain BaseChatModel instances from provider name and config, supporting OpenAI, Anthropic, and Ollama.
---

# LLM Providers

## Overview

The LLM provider module is a factory that creates LangChain `BaseChatModel`
instances from a provider name and configuration parameters. It centralizes all
LLM instantiation so that the executor, workflow nodes, and other consumers use a
single entry point. Three providers are supported: OpenAI, Anthropic, and Ollama.

## Specification

### Supported Providers and Models

**OpenAI** (default provider):

| Model ID | Name | Context Window |
|---|---|---|
| `gpt-4o` | GPT-4o | 128,000 |
| `gpt-4o-mini` | GPT-4o Mini | 128,000 |
| `gpt-4-turbo` | GPT-4 Turbo | 128,000 |
| `o3-mini` | o3-mini | 200,000 |

**Anthropic:**

| Model ID | Name | Context Window |
|---|---|---|
| `claude-sonnet-4-20250514` | Claude Sonnet 4 | 200,000 |
| `claude-opus-4-20250514` | Claude Opus 4 | 200,000 |
| `claude-haiku-4-20250414` | Claude Haiku 4 | 200,000 |

**Ollama** (local):

| Model ID | Name | Context Window |
|---|---|---|
| `llama3.1` | Llama 3.1 | 128,000 |
| `mistral` | Mistral | 32,000 |
| `codellama` | Code Llama | 16,000 |
| `gemma2` | Gemma 2 | 8,192 |

### Default Models

| Provider | Default Model |
|---|---|
| `openai` | `gpt-4o` |
| `anthropic` | `claude-sonnet-4-20250514` |
| `ollama` | `llama3.1` |

### `build_llm` Function

```python
def build_llm(
    provider: str = "openai",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    base_url: str | None = None,
    **kwargs,
) -> BaseChatModel
```

| Parameter | Description |
|---|---|
| `provider` | `"openai"`, `"anthropic"`, or `"ollama"` |
| `model` | Model ID; falls back to provider default if `None` |
| `temperature` | Creativity (0.0 - 1.0) |
| `max_tokens` | Maximum tokens in response |
| `base_url` | Custom API URL (Ollama default: `http://localhost:11434`) |
| `**kwargs` | Passed directly to the LangChain constructor |

**Provider mapping:**

| Provider | LangChain Class | Notes |
|---|---|---|
| `openai` | `ChatOpenAI` | Accepts optional `base_url` for proxies |
| `anthropic` | `ChatAnthropic` | Uses `ANTHROPIC_API_KEY` from env |
| `ollama` | `ChatOllama` | `max_tokens` mapped to `num_predict` |

### `build_llm_from_agent` Function

```python
def build_llm_from_agent(agent) -> BaseChatModel
```

Convenience wrapper that extracts config from an `Agent` model:

- `agent.llm_provider` -> `provider`
- `agent.llm_model` -> `model`
- `agent.llm_config.get("temperature", 0.7)` -> `temperature`
- `agent.llm_config.get("max_tokens", 4096)` -> `max_tokens`
- `agent.llm_config.get("base_url")` -> `base_url`

### `AVAILABLE_MODELS` Dictionary

Exported for frontend consumption. Structure:

```python
AVAILABLE_MODELS = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "context_window": 128000},
        ...
    ],
    ...
}
```

## File Structure

```
apps/backend/app/llm/
  __init__.py
  provider.py        # build_llm, build_llm_from_agent, DEFAULT_MODELS, AVAILABLE_MODELS
```

## Key Functions / Classes

| Symbol | Purpose |
|---|---|
| `build_llm` | Create a LangChain chat model from provider + params |
| `build_llm_from_agent` | Create a chat model from an Agent ORM instance |
| `DEFAULT_MODELS` | Dict mapping provider name to default model ID |
| `AVAILABLE_MODELS` | Dict mapping provider name to list of model metadata |

## Examples

```python
from app.llm.provider import build_llm, build_llm_from_agent

# Direct construction
llm = build_llm(provider="anthropic", model="claude-sonnet-4-20250514", temperature=0.3)

# From agent config
llm = build_llm_from_agent(agent)
response = await llm.ainvoke([HumanMessage(content="Hello")])
```

```python
# Using Ollama with custom base_url
llm = build_llm(provider="ollama", model="llama3.1", base_url="http://gpu-server:11434")
```

### Constraints

- `provider` MUST be one of `"openai"`, `"anthropic"`, `"ollama"`. Unknown values fall through to the OpenAI branch.
- API keys MUST be set in environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). The provider module does not validate their presence.
- For Ollama, `temperature` and `num_predict` are passed directly; `max_tokens` is NOT used (mapped to `num_predict` instead).
- `AVAILABLE_MODELS` is the single source of truth for model lists shown in the frontend.
- `build_llm_from_agent` MUST be the only way agents create LLM instances at runtime.
