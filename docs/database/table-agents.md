---
id: table-agents
title: "Table: agents"
domain: database
tags: [agents, llm, configuration, schema]
related: [schema-overview, table-users, table-tools, table-knowledge, agent-executor]
summary: Agent configuration table with LLM settings, system prompt, and N-N junctions to tools and knowledge bases.
---

# Table: agents

Source: `apps/backend/app/models/agent.py`

Inherits: `Base`, `UUIDMixin`, `TimestampMixin`

## Columns

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE, INDEX | Owning user. |
| `name` | `String(255)` | no | -- | -- | Display name. |
| `description` | `Text` | yes | `NULL` | -- | Human-readable description. |
| `avatar_url` | `String(512)` | yes | `NULL` | -- | Agent avatar image URL. |
| `system_prompt` | `Text` | no | -- | -- | System prompt defining agent behavior. |
| `llm_provider` | `String(50)` | no | `"openai"` | -- | Provider: `"openai"`, `"anthropic"`. |
| `llm_model` | `String(100)` | no | `"gpt-4o"` | -- | Model identifier. |
| `llm_config` | `JSONB` | no | `{}` | -- | Additional LLM parameters (see below). |
| `welcome_message` | `Text` | yes | `NULL` | -- | Greeting shown at conversation start. |
| `max_turns` | `Integer` | no | `50` | -- | Maximum exchange turns per conversation. |
| `is_published` | `Boolean` | no | `False` | -- | Whether the agent is publicly visible. |
| `status` | `String(20)` | no | `"draft"` | INDEX | `"draft"` or `"active"`. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |
| `updated_at` | `TIMESTAMP(tz)` | no | `now()` | -- | From TimestampMixin. |

## llm_config JSONB Structure

```json
{
  "temperature": 0.7,
  "max_tokens": 4096,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

All fields are optional. The `build_llm_from_agent` function merges these into the LLM constructor.

## Junction Table: agent_tools

| Column | Type | Constraints | Description |
|---|---|---|---|
| `agent_id` | `UUID` | PK, FK(`agents.id`) CASCADE | |
| `tool_id` | `UUID` | PK, FK(`tools.id`) CASCADE | |
| `priority` | `Integer` | default `0` | Ordering priority for tool presentation. |
| `added_at` | `TIMESTAMP(tz)` | default `now()` | When the tool was linked. |

## Junction Table: agent_knowledge_bases

| Column | Type | Constraints | Description |
|---|---|---|---|
| `agent_id` | `UUID` | PK, FK(`agents.id`) CASCADE | |
| `knowledge_base_id` | `UUID` | PK, FK(`knowledge_bases.id`) CASCADE | |
| `added_at` | `TIMESTAMP(tz)` | default `now()` | When the KB was linked. |

## Relationships

| Relationship | Target | Type | Loading | Notes |
|---|---|---|---|---|
| `user` | `User` | N:1 | default | Back-populates `user.agents`. |
| `tools` | `Tool` | N:N | `selectin` | Via `agent_tools` junction. |
| `knowledge_bases` | `KnowledgeBase` | N:N | `selectin` | Via `agent_knowledge_bases` junction. |
| `conversations` | `Conversation` | 1:N | default | Cascade delete-orphan. |
| `workflows` | `Workflow` | 1:N | default | No cascade (workflow FK is SET NULL). |

## Indexes

- `user_id` -- filter agents by owner.
- `status` -- filter active vs. draft agents.
