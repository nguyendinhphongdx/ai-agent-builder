---
id: frontend-feature-settings
title: Settings View
domain: frontend
tags: [settings, api-keys, providers, configuration]
related: [frontend-layout, frontend-api-client]
summary: Documents the SettingsView component covering API key management for LLM providers and general configuration options.
---

# Settings Feature

## File: `src/features/settings/views/SettingsView.tsx`

## Sections

### API Keys

Manages API keys for LLM providers. Keys are described as "encrypted at rest."

#### Supported Providers

| Provider  | Label     | Description              |
|-----------|-----------|--------------------------|
| `openai`  | OpenAI    | GPT-4o, Embeddings       |
| `anthropic`| Anthropic| Claude Sonnet, Haiku     |
| `cohere`  | Cohere    | Reranking, Embeddings    |

#### Per-Provider Card

Each provider shows:
- Key icon, provider name, and description
- "Add Key" button (if not currently adding)
- List of existing keys with: name, masked key (first 8 + ... + last 4 chars), "Default" badge (if first key for provider), delete button
- "No keys configured" placeholder when empty

#### Add Key Form

When "Add Key" is clicked:
- Key name input (optional, defaults to `"${provider} key"`)
- Key value input (password field with show/hide toggle)
- Cancel and Save buttons
- Save creates a local `ApiKeyEntry` with masked key display

**Note:** Current implementation is local state only (no API persistence). The structure is ready for backend integration.

### General Settings

#### Default LLM Provider

Select dropdown: OpenAI, Anthropic. Description: "Used when creating new agents."

#### Default Model

Select dropdown: GPT-4o, GPT-4o Mini, Claude Sonnet 4. Description: "Pre-selected model for new agents."

## State Management

All state is managed locally via `useState`:
- `keys: ApiKeyEntry[]` -- list of added API keys
- `addingProvider: string | null` -- which provider's add form is open
- `newKeyValue`, `newKeyName` -- form inputs
- `showKey: boolean` -- password visibility toggle

## Layout

- Full height flex column
- Header with "Settings" title
- Scrollable content area, max-width `2xl` (672px)
- Provider cards use `rounded-xl border border-white/6 bg-white/2` styling
- Consistent with dashboard dark theme
