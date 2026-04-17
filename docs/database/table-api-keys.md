---
id: table-api-keys
title: "Table: api_keys"
domain: database
tags: [api-keys, encryption, providers, schema]
related: [schema-overview, table-users, table-agents]
summary: Encrypted API key storage for external LLM providers, with per-user default key selection and usage tracking.
---

# Table: api_keys

Source: `apps/backend/app/models/api_key.py`

Inherits: `Base`, `UUIDMixin` (custom `created_at`, no `updated_at`)

## Columns

| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| `id` | `UUID` | no | `uuid4()` | PK | |
| `user_id` | `UUID` | no | -- | FK(`users.id`) CASCADE | Owning user. |
| `provider` | `String(50)` | no | -- | -- | LLM provider identifier (see enum below). |
| `name` | `String(255)` | no | -- | -- | User-assigned display name for this key. |
| `encrypted_key` | `Text` | no | -- | -- | Encrypted API key value (see encryption notes). |
| `is_default` | `Boolean` | no | `False` | -- | Whether this is the default key for its provider. |
| `last_used_at` | `TIMESTAMP(tz)` | yes | `NULL` | -- | Updated on each API call using this key. |
| `created_at` | `TIMESTAMP(tz)` | no | `now()` | -- | |

## Provider Enum

The `provider` column accepts string values identifying the external LLM service:

| Value | Service |
|---|---|
| `"openai"` | OpenAI API (GPT models, embeddings) |
| `"anthropic"` | Anthropic API (Claude models) |

Additional providers can be added as string values without schema changes.

## Encryption

The `encrypted_key` column stores the API key after server-side encryption. The plaintext key is never persisted in the database. Key points:

- Encryption is applied before insert and decryption occurs at read time in the service layer.
- The encryption mechanism is implemented outside the model (typically in the API key service or a utility module).
- The `Text` type is used rather than a fixed-length string to accommodate varying ciphertext lengths across encryption algorithms.

## Default Key Selection

The `is_default` flag identifies which key to use when an agent's `llm_provider` matches a provider but no specific key is referenced. The application should enforce at most one default key per `(user_id, provider)` pair at the service level.

## Relationships

| Relationship | Target | Type | Notes |
|---|---|---|---|
| `user` | `User` | N:1 | Back-populates `user.api_keys`. |

## Usage Flow

1. User creates an API key via the settings UI, providing the plaintext key and a name.
2. The service layer encrypts the key and stores the ciphertext in `encrypted_key`.
3. When an agent runs, the executor looks up the user's default key for the agent's `llm_provider`.
4. The key is decrypted in memory and passed to the LangChain LLM constructor.
5. `last_used_at` is updated after a successful API call.

## Security Considerations

- Plaintext API keys exist only in memory during encryption/decryption and LLM calls.
- Database backups contain only encrypted values.
- Cascade delete on `user_id` ensures keys are removed when a user account is deleted.
- The model does not store key prefixes or masked versions; masking is handled at the API response layer.
