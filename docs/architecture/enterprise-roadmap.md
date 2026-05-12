---
id: arch-enterprise-roadmap
title: Enterprise Roadmap — 12-Month Implementation Plan
domain: architecture
tags: [roadmap, enterprise, planning, multi-tenancy, workspace, organization, sso, saml, scim, oidc, mfa, queue, rabbitmq, jobs, observability, opentelemetry, langfuse, billing, usage-metering, soc2, helm, kubernetes, on-prem, white-label, plugins, rag, hybrid-search, reranker, i18n, e2e-tests]
related: [arch-system-overview, arch-operations, arch-deployment, arch-dependencies, guides-momo-setup]
summary: 12-month plan to evolve AgentForge from MVP to enterprise SaaS. Four phases — Phase 0 prerequisites (CI, tests); Phase 1 multi-tenancy + queue + SSO + audit; Phase 2 hybrid RAG + OTEL/Langfuse + usage-based billing + cron triggers; Phase 3 plugin system + LLM/vector breadth + i18n + E2E tests + notifications; Phase 4 Helm + Terraform + on-prem + SOC2 + white-label. Includes schema DDL, code touchpoints, acceptance criteria, effort estimates, risks, team sizing, and budget.
---

# AgentForge — Enterprise Roadmap & Implementation Plan

> **Mục đích**: Kế hoạch triển khai chi tiết để đưa AgentForge từ MVP single-user lên nền tảng bán được Enterprise.
> **Phạm vi**: 12 tháng, 4 quý, ~25 hạng mục lớn.
> **Cách dùng**: Mỗi hạng mục có scope, files cần đụng, schema thay đổi, milestone, acceptance criteria, effort estimate. Đọc theo thứ tự — các hạng mục sau phụ thuộc các hạng mục trước.
> **Liên kết**: [kien-truc-flowise-dify.md](../../../docs/kien-truc-flowise-dify.md) — bối cảnh so sánh với Flowise/Dify.
>
> **🔴 Trạng thái triển khai**: roadmap này là spec ổn định, KHÔNG chứa progress notes. Trước khi bắt đầu code, đọc [phase-1-progress](./phase-1-progress.md) để biết hiện đang đến đâu, đã quyết gì, đang đợi quyết định gì. File progress được update mỗi session, đây không.

---

## 📋 Tổng quan ưu tiên

| Phase | Thời gian | Mục tiêu chính | Kết quả bán được |
|---|---|---|---|
| **Phase 0** | Tuần 1-2 | Prerequisites: CI, test infra, branching strategy | Foundation cho mọi việc sau |
| **Phase 1 (Q1)** | Tháng 1-3 | Multi-tenancy + Queue + SSO + Audit log | B2B SMB ($500-2k/tháng) |
| **Phase 2 (Q2)** | Tháng 4-6 | RAG nâng cấp + Observability + Usage billing + Triggers | Mid-market ($5-20k/năm) |
| **Phase 3 (Q3)** | Tháng 7-9 | Plugin system + LLM/VectorDB breadth + i18n + E2E tests | Compete Dify Cloud |
| **Phase 4 (Q4)** | Tháng 10-12 | Helm + On-prem + SOC2 + White-label + Advanced workflow | Enterprise ($50-200k/năm) |

**Nguyên tắc xuyên suốt**:
- Mỗi hạng mục có **migration script reversible**.
- Test trước khi build (TDD cho schema-heavy work).
- Feature flag mọi tính năng mới (dùng env hoặc DB-driven).
- Mọi PR phải có migration test trên Postgres thật, không SQLite.

---

# Phase 0 — Prerequisites (Tuần 1-2)

> Trước khi build feature lớn, phải có nền tảng để không bị regression.

## P0.1 — CI/CD pipeline đầy đủ

**Scope**: GitHub Actions chạy trên mọi PR.

**Phải có**:
- Backend: `pytest` + `mypy --strict` + `ruff` + `alembic upgrade head` trên Postgres test container
- Frontend: `pnpm test` (vitest) + `pnpm lint` + `pnpm type-check` + `pnpm build`
- Docker build cho backend + frontend (cache layers)
- Migration check: `alembic check` + auto-generate diff
- Coverage report (Codecov hoặc tự host)

**Files mới**:
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`
- `.github/workflows/docker-build.yml`
- `apps/backend/conftest.py` (Postgres testcontainer fixture)

**Effort**: 3-4 ngày. **DoD**: PR template có status check bắt buộc pass.

## P0.2 — Test infrastructure

**Scope**: Đặt nền cho 80% coverage trong tương lai.

**Backend**:
- Pytest fixtures: `db_session`, `authenticated_user`, `workspace_factory` (cho phase 1)
- Factory pattern (`factory-boy`) thay vì insert thủ công
- Test marker: `@pytest.mark.integration`, `@pytest.mark.unit`

**Frontend**:
- Vitest + jsdom config
- React Testing Library setup
- MSW (Mock Service Worker) để mock API
- Playwright cho E2E (config sẵn, test sau)

**Files mới**:
- `apps/backend/tests/factories/`
- `apps/backend/tests/conftest.py`
- `apps/frontend/src/test-utils/`
- `apps/frontend/playwright.config.ts`

**Effort**: 5 ngày. **DoD**: 1 unit test mẫu + 1 integration test mẫu pass trên CI.

## P0.3 — Git branching + Release process

**Scope**: Setup branch strategy + semver + changelog.

- Trunk-based: `main` luôn deployable, feature branches < 3 ngày
- Conventional Commits (feat/fix/chore/docs)
- `release-please` hoặc `changesets` tự động tạo CHANGELOG
- Git tags semver cho mỗi release

**Effort**: 1 ngày.

---

# Phase 1 — Q1: Foundation cho Enterprise (Tháng 1-3)

> 3 thứ phải làm TRƯỚC khi có khách hàng B2B đầu tiên, vì sửa sau sẽ phải migrate dữ liệu khách.

## 🔴 P1.1 — Multi-tenancy (Workspace/Organization)

**Tại sao**: Mọi resource hiện gắn `user_id`. B2B = nhiều người trong 1 công ty share workspace.

### Schema thay đổi

**Tables mới**:
```sql
organizations (
  id UUID PK,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  billing_email TEXT,
  plan TEXT DEFAULT 'free',  -- free|pro|enterprise
  created_at, updated_at
)

workspaces (
  id UUID PK,
  organization_id UUID FK organizations,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  is_personal BOOLEAN DEFAULT FALSE,  -- mỗi user có 1 personal workspace
  settings JSONB,
  created_at, updated_at,
  UNIQUE(organization_id, slug)
)

workspace_members (
  workspace_id UUID FK workspaces,
  user_id UUID FK users,
  role TEXT NOT NULL,  -- owner|admin|editor|viewer
  invited_by UUID FK users,
  joined_at TIMESTAMPTZ,
  PRIMARY KEY (workspace_id, user_id)
)

workspace_invitations (
  id UUID PK,
  workspace_id UUID FK workspaces,
  email TEXT NOT NULL,
  role TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ,
  accepted_at TIMESTAMPTZ NULL,
  invited_by UUID FK users
)
```

**Sửa tables hiện có**: thêm `workspace_id UUID NOT NULL FK workspaces` + index vào:
- `agents`, `tools`, `knowledge_bases`, `documents`, `document_chunks`
- `conversations`, `workflows`, `workflow_runs`, `node_executions`
- `ai_credentials`, `personal_access_tokens`
- `agent_templates` (giữ nguyên user-level cho marketplace public, nhưng thêm `published_from_workspace_id`)

**Migration strategy**:
1. Migration 1: tạo bảng mới + cột `workspace_id` NULLABLE
2. Migration 2: tạo personal workspace cho mỗi user, populate `workspace_id` từ `user_id`
3. Migration 3: ALTER COLUMN `workspace_id` SET NOT NULL
4. Migration 4: drop `user_id` không cần thiết (giữ cho ownership/audit)

### Code thay đổi

**Backend**:
- [platform/context.py](../../apps/backend/app/platform/context.py): thêm `current_workspace_id()` ContextVar
- Middleware đọc workspace từ header `X-Workspace-Id` hoặc subdomain
- Mới: `app/modules/identity/workspaces/` module (router/service/schemas)
- Mới: `app/modules/identity/organizations/` module
- **Mọi service query** phải filter `WHERE workspace_id = current_workspace_id()` — review hết ~25 modules
- Decorator `@require_workspace_role("admin")` cho privileged ops

**Frontend**:
- Workspace switcher ở header (Combobox với search)
- `/settings/workspace/` page: members, invitations, settings, danger zone
- `/onboarding/create-workspace` cho user mới
- Zustand store: `useWorkspaceStore` với `currentWorkspace`
- TanStack Query keys phải include `workspaceId` để cache đúng

### Acceptance Criteria

- [ ] User A trong workspace X không thấy resource của user B trong workspace Y
- [ ] Invite flow: gửi email → nhận token → accept → thành member
- [ ] Role enforcement: viewer không tạo được agent, editor không invite được member
- [ ] Personal workspace tạo tự động khi register
- [ ] Migration chạy được trên DB có 10k user, 100k agent (test với fixture)
- [ ] E2E test: 2 workspace, switch qua lại, data isolated

**Effort**: 4-6 tuần (1 senior backend + 1 frontend full-time).

---

## 🔴 P1.2 — Job Queue (RabbitMQ wired đúng nghĩa)

**Tại sao**: Hiện [modules/runtime/triggers/http/router.py](../../apps/backend/app/modules/runtime/triggers/http/router.py) dùng `asyncio.create_task()`. KB ingestion chạy đồng bộ. Workflow run block API thread. Sập với traffic enterprise.

### Architecture

```
API container ──publish──> RabbitMQ ──consume──> Worker container(s)
                              │
                              └──> Result queue ──> Socket service ──> WS client
```

**Worker tiers** (deployment riêng, scale độc lập):
- `worker-ingest` (KB document processing)
- `worker-workflow` (workflow execution)
- `worker-webhook` (outbound webhook delivery + retries)
- `worker-mail` (email send)
- `worker-embed` (embedding compute, batch)

### Implementation

**Library**: `aio-pika` (async-native, đã có RabbitMQ trong compose).

**Job types** (define trong `app/modules/runtime/jobs/types.py`):
```python
class JobType(str, Enum):
    KB_INGEST_DOCUMENT = "kb.ingest.document"
    KB_REINDEX = "kb.reindex"
    WORKFLOW_RUN = "workflow.run"
    WORKFLOW_RUN_SCHEDULED = "workflow.run.scheduled"
    WEBHOOK_DELIVER = "webhook.deliver"
    EMAIL_SEND = "email.send"
    EMBED_BATCH = "embed.batch"
```

**Mỗi job có**:
- `idempotency_key` (UUID, deduplicate)
- `attempt` counter
- `max_attempts` (default 5)
- `delay_seconds` (cho retry với exponential backoff)
- `dlq_after` (move to dead letter queue)

**Files mới**:
- `app/modules/runtime/jobs/__init__.py` — Producer (publish)
- `app/modules/runtime/jobs/consumer.py` — Worker entry point
- `app/modules/runtime/jobs/handlers/` — 1 file/job type
- `app/modules/runtime/jobs/idempotency.py` — Redis-backed dedup
- `app/modules/runtime/jobs/dlq.py` — DLQ inspection API
- `services/worker/Dockerfile` — Worker image
- `services/worker/docker-compose.yml`

**Sửa code**:
- KB upload endpoint: `await producer.publish(KB_INGEST_DOCUMENT, ...)` thay vì await ingest trực tiếp
- Workflow execute: enqueue job, return `run_id` ngay lập tức, client poll hoặc nghe WS
- Webhook outbound: enqueue thay vì `httpx.post` trong request

### UI thay đổi

- Job progress component (poll `/api/jobs/{id}` hoặc subscribe WS)
- DLQ admin viewer ở `/admin/jobs` (xem failed jobs, replay, delete)
- KB document có status: `queued | processing | ready | failed` (đã có status field, giờ wire đúng)

### Acceptance Criteria

- [ ] Upload PDF 200 trang → API trả 202 Accepted ngay, không block
- [ ] Worker crash giữa chừng → job redrive, không mất data
- [ ] Idempotency: publish 2 lần cùng key → chỉ chạy 1 lần
- [ ] DLQ hoạt động: 5 lần fail → vào DLQ, có UI inspect/replay
- [ ] Load test: 1000 jobs/phút không drop
- [ ] Helm-friendly: scale `worker-ingest` từ 1→5 replica không cần restart API

**Effort**: 2-3 tuần.

---

## 🔴 P1.3 — SSO Enterprise (SAML 2.0 + OIDC + SCIM)

**Tại sao**: Doanh nghiệp VN dùng Microsoft 365 (Azure AD) hoặc Google Workspace. Fortune 500 yêu cầu Okta/Ping. Hiện chỉ có OAuth Google/GitHub social login ở [modules/identity/auth/oauth.py](../../apps/backend/app/modules/identity/auth/oauth.py).

### Implementation

**Library**:
- `python3-saml` cho SAML 2.0
- `authlib` cho OIDC (đã quen với OAuth)
- Custom SCIM v2 endpoint

### Schema

```sql
sso_configurations (
  id UUID PK,
  organization_id UUID FK organizations,
  provider TEXT NOT NULL,  -- saml|oidc
  display_name TEXT,
  -- SAML
  saml_idp_entity_id TEXT,
  saml_idp_sso_url TEXT,
  saml_idp_x509_cert TEXT,
  saml_sp_entity_id TEXT,
  -- OIDC
  oidc_issuer TEXT,
  oidc_client_id TEXT,
  oidc_client_secret_encrypted BYTEA,
  -- Common
  default_role TEXT DEFAULT 'editor',
  jit_provisioning BOOLEAN DEFAULT TRUE,
  attribute_mapping JSONB,  -- {"email": "mail", "name": "displayName"}
  is_active BOOLEAN DEFAULT FALSE,
  created_at, updated_at
)

scim_tokens (
  id UUID PK,
  organization_id UUID FK organizations,
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  last_used_at TIMESTAMPTZ
)

workspace_ip_rules (
  id UUID PK,
  workspace_id UUID FK workspaces,
  cidr CIDR NOT NULL,
  description TEXT,
  created_by UUID FK users
)
```

### Endpoints mới

- `GET/POST /api/sso/saml/{org_slug}/login` — initiate
- `POST /api/sso/saml/{org_slug}/acs` — assertion consumer
- `GET /api/sso/saml/{org_slug}/metadata` — SP metadata XML
- `GET /api/sso/oidc/{org_slug}/login`
- `GET /api/sso/oidc/{org_slug}/callback`
- `GET/POST/PUT/DELETE /api/scim/v2/Users` (SCIM v2)
- `GET/POST/PUT/DELETE /api/scim/v2/Groups`

### MFA

- TOTP (Google Authenticator) với `pyotp`
- WebAuthn passkey với `webauthn` package
- Backup codes (10 codes, 1-time-use)
- Force-MFA flag per workspace
- Recovery flow qua admin

**Files**:
- `app/modules/identity/auth/sso/saml.py`
- `app/modules/identity/auth/sso/oidc.py`
- `app/modules/identity/auth/scim/`
- `app/modules/identity/auth/mfa/`
- Frontend: `/settings/security/mfa`, `/admin/sso-config`

### Acceptance Criteria

- [ ] Test với 4 IdP: Azure AD, Google Workspace, Okta, generic SAML (Keycloak)
- [ ] JIT provisioning: user login lần đầu → tự tạo trong workspace với default_role
- [ ] SCIM: deactivate user ở Okta → user bị disable trong AgentForge trong < 1 phút
- [ ] IP allowlist: user ngoài CIDR bị block
- [ ] MFA enrollment + verify + recovery flow đầy đủ
- [ ] Audit log mọi SSO event

**Effort**: 2-3 tuần.

---

## 🔴 P1.4 — Audit Log

**Tại sao**: SOC2/ISO27001 yêu cầu. Enterprise muốn biết "ai làm gì khi nào".

### Schema

```sql
audit_logs (
  id UUID PK,
  organization_id UUID FK organizations,
  workspace_id UUID FK workspaces NULL,
  actor_user_id UUID FK users NULL,  -- NULL = system action
  actor_type TEXT,  -- user|api_token|system|sso
  action TEXT NOT NULL,  -- e.g. "workspace.member.invite"
  resource_type TEXT,
  resource_id UUID,
  ip_address INET,
  user_agent TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX (organization_id, created_at DESC),
  INDEX (resource_type, resource_id, created_at DESC)
)
```

### Implementation

- Middleware tự động log mọi mutation (POST/PUT/DELETE)
- Decorator `@audit_log("agent.create")` cho actions cụ thể
- Background flush qua queue (đừng block request)
- Retention: configurable per plan (free=30d, enterprise=7 năm)

### UI

- `/admin/audit` — filter by actor, action, date range, resource
- Export CSV/JSON
- Alert rules: "khi role 'admin' bị grant → email security@"

**Effort**: 1 tuần.

---

## 🟡 P1.5 — Workspace-scoped Resources & Permissions

**Tại sao**: Sau khi có workspace, cần fine-grained permission.

### Permission model

Thay role enum bằng permission flags:
```python
class Permission(str, Enum):
    AGENT_CREATE = "agent.create"
    AGENT_READ = "agent.read"
    AGENT_UPDATE = "agent.update"
    AGENT_DELETE = "agent.delete"
    AGENT_PUBLISH = "agent.publish"
    KB_CREATE = "kb.create"
    KB_READ = "kb.read"
    # ... ~40 permissions
    BILLING_MANAGE = "billing.manage"
    MEMBER_INVITE = "member.invite"
    MEMBER_REMOVE = "member.remove"
    SSO_CONFIGURE = "sso.configure"
```

Built-in roles map → permissions:
- `viewer`: `*.read`
- `editor`: `viewer` + `agent/kb/tool/workflow.create/update`
- `admin`: `editor` + `member.*` + `billing.*`
- `owner`: tất cả

Custom roles (Pro+ plan): admin tự define permission set.

**Effort**: 1 tuần.

---

## 📊 Phase 1 — Tổng kết

| Hạng mục | Effort | Phụ thuộc |
|---|---|---|
| P0 (CI + test) | 1-2 tuần | — |
| P1.1 Multi-tenancy | 4-6 tuần | P0 |
| P1.2 Queue | 2-3 tuần | P0 |
| P1.3 SSO + MFA | 2-3 tuần | P1.1 |
| P1.4 Audit log | 1 tuần | P1.1, P1.2 |
| P1.5 RBAC fine-grained | 1 tuần | P1.1 |
| **Tổng** | **11-16 tuần** | (parallel hoá được ~3 tháng) |

**Sau Phase 1, có thể bán**: B2B SMB plan ($500-2k/tháng), 5-50 users/workspace, basic SSO.

---

# Phase 2 — Q2: Power Features (Tháng 4-6)

> Khi đã có enterprise foundation, build features khách hàng dùng nhiều.

## 🟡 P2.1 — RAG nâng cấp

### P2.1.1 Hybrid Search (BM25 + Vector)

**Schema**: Thêm `tsvector` column vào `document_chunks`:
```sql
ALTER TABLE document_chunks ADD COLUMN content_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED;
CREATE INDEX ON document_chunks USING GIN (content_tsv);
```

**Algorithm** (Reciprocal Rank Fusion):
1. Parallel: vector search top-50 + BM25 search top-50
2. Score = sum(1 / (k + rank_i)) cho mỗi chunk xuất hiện
3. Return top-N theo combined score

### P2.1.2 Reranker

**Provider abstraction**:
- Cohere `rerank-3` (managed)
- BGE `bge-reranker-v2-m3` (self-hosted, qua HF Inference Endpoint hoặc local GPU)
- Voyage `rerank-2`

**Cấu hình per-KB**: enabled/disabled + provider + top_k (giữ lại sau rerank).

### P2.1.3 Parent-Child Chunking

Lưu 2 layer:
- Small chunks (200 tokens) — embed + search
- Parent chunks (1000 tokens) — return về LLM

**Schema**:
```sql
ALTER TABLE document_chunks ADD COLUMN parent_chunk_id UUID FK document_chunks;
ALTER TABLE document_chunks ADD COLUMN chunk_level INT DEFAULT 0;  -- 0=small, 1=parent
```

### P2.1.4 Connectors (External Sync)

**Connector framework**:
```python
class KBConnector(ABC):
    name: str
    auth_type: Literal["oauth", "api_key", "basic"]
    
    async def list_resources(self, credentials) -> list[Resource]: ...
    async def fetch_content(self, resource_id) -> bytes: ...
    async def get_changes_since(self, last_sync_at) -> list[Resource]: ...
```

**Connectors cần build (theo thứ tự ưu tiên)**:
1. S3 / GCS / Azure Blob
2. Google Drive (OAuth)
3. Notion (OAuth)
4. Confluence (OAuth)
5. SharePoint (Microsoft Graph)
6. Slack messages
7. GitHub repos (READMEs, wikis)

**Sync strategy**: cron job (Phase 2.4 triggers) chạy mỗi connector theo interval, dùng `last_sync_at` cursor + delta.

### P2.1.5 Table & Image Extraction

- **Tables**: `unstructured.io` hoặc `Docling` (IBM) — extract bảng thành Markdown rồi chunk
- **Images**: OCR qua `tesseract` (local) hoặc GPT-4V cho complex diagrams
- **Charts**: same as images

**Effort tổng P2.1**: 4-5 tuần.

---

## 🟡 P2.2 — Observability & Tracing

### P2.2.1 OpenTelemetry

**Setup**:
- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-instrumentation-sqlalchemy`
- `opentelemetry-instrumentation-asyncpg`
- `opentelemetry-instrumentation-redis`
- `opentelemetry-instrumentation-aio-pika`

**Custom spans** cho:
- Workflow execution: 1 span/workflow + 1 child/node
- LLM call: 1 span/call với attributes: provider, model, prompt_tokens, completion_tokens, cost_usd
- Tool call: 1 span/call

**Exporter**: OTLP qua gRPC → user tự config endpoint (Tempo, Datadog, New Relic, etc.)

### P2.2.2 Prometheus Metrics

**`/metrics` endpoint** với:
- `http_request_duration_seconds` histogram
- `workflow_run_duration_seconds` histogram (label: workflow_id, status)
- `llm_tokens_total` counter (label: provider, model, type=prompt|completion)
- `llm_cost_usd_total` counter
- `kb_query_duration_seconds`
- `job_queue_depth` gauge (label: queue_name)
- `job_processing_duration_seconds`

### P2.2.3 Langfuse / LangSmith Integration

**Plugin pattern**: user config trong workspace settings → AgentForge SDK call wrap trace.

```python
# app/observability/tracing.py
class TraceProvider(ABC):
    async def start_trace(self, name, metadata) -> Trace: ...
    async def log_generation(self, trace_id, ...): ...

class LangfuseProvider(TraceProvider): ...
class LangSmithProvider(TraceProvider): ...
class PhoenixProvider(TraceProvider): ...
```

User config trong `/settings/observability` → enable provider → paste API key.

### P2.2.4 Cost Dashboard

**Schema**:
```sql
usage_events (
  id UUID PK,
  workspace_id UUID FK,
  agent_id UUID NULL,
  workflow_run_id UUID NULL,
  event_type TEXT,  -- llm_call|kb_query|tool_call
  provider TEXT,
  model TEXT,
  prompt_tokens INT,
  completion_tokens INT,
  cost_usd NUMERIC(10, 6),
  latency_ms INT,
  created_at TIMESTAMPTZ,
  INDEX (workspace_id, created_at DESC)
)
```

**Dashboard** ở `/dashboard/usage`:
- Line chart: cost theo ngày/tuần/tháng
- Breakdown: theo agent, theo workflow, theo model
- Top consumers (workspace member nào dùng nhiều nhất)
- Alert rule: "khi > $X/ngày → email"

**Effort P2.2**: 3-4 tuần.

---

## 🟡 P2.3 — Usage-Based Billing

### Pricing model

**Plans**:
| Plan | Price | Limits |
|---|---|---|
| Free | $0 | 1 workspace, 3 members, 100 LLM calls/month, 10 MB KB |
| Starter | $29/mo | 5 members, 10k LLM calls, 1GB KB |
| Pro | $99/mo | 20 members, 100k LLM calls, 10GB KB, SSO |
| Enterprise | Quote | Unlimited, on-prem option, SLA |

**Plus metered**:
- $0.001/extra LLM call
- $0.10/GB extra KB
- $0.50/extra workspace

### Implementation

**Stripe Metered Billing**:
- Tạo Stripe Product/Price cho mỗi plan + metered SKU
- Mỗi `usage_event` → batch publish vào Stripe `usage_records`
- Webhook handler `invoice.upcoming` → check quota → notify

**Quota enforcement**:
- Redis counter mỗi workspace, reset đầu tháng
- Middleware check trước khi LLM call: `if usage > quota: raise QuotaExceeded`
- Soft limit: warn ở 80%, hard limit ở 100% (configurable)

### Tax handling

- **VN**: VAT 10% trên invoice nội địa
- **EU**: VATMOSS, validate VAT number qua VIES API
- **US**: Sales tax via Stripe Tax
- Stripe Tax tự handle hầu hết, chỉ cần config địa chỉ + business type

### Invoice & Reports

- Invoice generation tự động (Stripe)
- PDF download qua dashboard
- Monthly report email với usage breakdown

**Files**:
- `app/modules/commerce/payments/subscriptions/plans.py` — define plans
- `app/modules/commerce/payments/subscriptions/quota.py` — enforcement
- `app/modules/commerce/payments/subscriptions/metering.py` — Stripe usage publish
- Frontend: `/settings/billing/`, `/settings/billing/invoices/`

**Effort**: 3 tuần.

---

## 🟡 P2.4 — Trigger Ecosystem

### P2.4.1 Cron / Schedule Trigger

**Architecture**: APScheduler chạy trong dedicated `worker-scheduler` container, đọc `scheduled_triggers` table mỗi phút.

```sql
scheduled_triggers (
  id UUID PK,
  workspace_id UUID FK,
  workflow_id UUID FK,
  cron_expression TEXT,  -- e.g. "0 9 * * 1-5"
  timezone TEXT DEFAULT 'UTC',
  next_run_at TIMESTAMPTZ,
  last_run_at TIMESTAMPTZ,
  is_active BOOLEAN,
  created_by UUID FK users
)
```

**Workflow node mới**: `cron_trigger` (giống webhook_trigger nhưng schedule).

### P2.4.2 Email Trigger

**Inbound email** qua:
- Mailgun Routes (managed)
- Hoặc SES + SNS + Lambda webhook

Workflow node `email_trigger` nhận: from, to, subject, body, attachments.

### P2.4.3 Slack/Teams/Discord Trigger

**Slack**: Slack App với Events API + Slash Commands.
**Teams**: Bot Framework với Bot Service.
**Discord**: Discord Bot với gateway/webhook.

Mỗi nền tảng = 1 trigger node + 1 OAuth setup flow trong settings.

### P2.4.4 Webhook Hardening

**Phải có**:
- HMAC signature verification cho INCOMING (config secret per webhook)
- Replay protection (nonce + timestamp window)
- Retries với exponential backoff cho OUTGOING
- Webhook delivery log + replay UI

**Effort P2.4**: 3 tuần (cron + email + 1 platform; Slack/Teams/Discord rải Phase 3).

---

## 📊 Phase 2 — Tổng kết

| Hạng mục | Effort |
|---|---|
| P2.1 RAG nâng cấp | 4-5 tuần |
| P2.2 Observability | 3-4 tuần |
| P2.3 Billing | 3 tuần |
| P2.4 Triggers (core) | 3 tuần |
| **Tổng** | **13-15 tuần** (parallel ~3 tháng) |

**Sau Phase 2, có thể bán**: Mid-market plan với SLA, dashboard cost, automated workflows. Giá $5-20k/năm.

---

# Phase 3 — Q3: Breadth & Polish (Tháng 7-9)

> Đua tính năng với Dify trên những thứ enterprise đánh giá.

## 🟢 P3.1 — Plugin / Extension System

**Inspired by**: Dify Plugin Daemon. Hiện [modules/integrations/mcp/](../../apps/backend/app/modules/integrations/mcp/) chỉ expose AgentForge as MCP server, chưa **consume** plugins/MCP servers ngoài.

### Architecture

```
Backend API ──JSON-RPC──> Plugin Daemon (subprocess pool)
                              │
                              ├──> Plugin A (Python venv riêng)
                              ├──> Plugin B (Node.js)
                              └──> Plugin C (Docker container)
```

### Plugin manifest

```yaml
# plugin.yaml
id: my-jira-tool
version: 1.0.0
runtime: python  # python|nodejs|docker
entrypoint: main.py
capabilities:
  - tool
  - trigger
permissions:
  - http_outbound: ["jira.com"]
  - secrets: ["JIRA_API_KEY"]
schema:
  tools:
    - name: create_issue
      description: Create a Jira issue
      input_schema: {...}
      output_schema: {...}
```

### Implementation

- Plugin Daemon: Python service quản lý subprocess pool
- Plugin loader: clone Git repo hoặc upload zip → validate manifest → install deps trong venv → register
- Sandbox: Linux namespaces + seccomp + cgroups (đã có code-sandbox service, mở rộng)
- Plugin marketplace: tách khỏi template marketplace, có review process

**Effort**: 4-5 tuần. Đây là feature lớn — nếu effort không đủ, làm sau.

---

## 🟢 P3.2 — LLM & Vector DB Breadth

### Thêm LLM providers

Tạo abstraction `LLMProvider` rồi implement:
- Mistral (Codestral, Mixtral)
- Groq (LLaMA 3 fast inference)
- Google Gemini (Pro + Flash)
- AWS Bedrock (Claude/Llama via AWS)
- Azure OpenAI (Enterprise yêu cầu)
- vLLM / Together AI (self-hosted)
- Cohere Command
- DeepSeek
- Qwen (cho thị trường Châu Á)

**Files**: `app/modules/integrations/llm/providers/{name}.py` mỗi provider.

### Thêm Vector DB backends

`VectorStore` abstraction:
- Pinecone (managed, enterprise quen)
- Weaviate (self-hosted phổ biến)
- Qdrant
- Milvus
- Chroma
- Elasticsearch (cho khách đã có ES)

**Cấu hình per-KB**: chọn backend, paste credentials, AgentForge tự sync embeddings.

**Effort**: 3-4 tuần (1 tuần/3 provider).

---

## 🟢 P3.3 — i18n (Đa ngôn ngữ)

**Stack**: `next-intl` (App Router native).

### Setup

- Locale routing: `/en/`, `/vi/`, `/ja/`, `/ko/`
- Middleware detect locale từ Accept-Language hoặc cookie
- Translation files: `messages/{locale}.json`
- Tách hardcoded strings → translation keys (~2000 strings)

### Localization

- Số, tiền: `Intl.NumberFormat`
- Ngày giờ: `Intl.DateTimeFormat` + timezone
- Pluralization: ICU MessageFormat
- RTL support (tailwindcss-rtl) cho Arabic/Hebrew

**Initial languages**: English, Vietnamese, Japanese, Korean (SEA market focus). Spanish, French, Chinese sau.

**Effort**: 2-3 tuần (extract strings là phần tốn thời gian).

---

## 🟢 P3.4 — E2E Test Suite

**Framework**: Playwright.

### Critical paths phải có (Tier 1):
1. Signup → email verify → onboarding → first agent
2. Create agent + attach tool + chat with streaming
3. Upload KB → wait processing → query KB
4. Build workflow with 5 nodes → execute → check output
5. Publish template → another user purchases (Stripe test mode) → fork

### Tier 2 paths:
6. Invite member → member accepts → role enforcement
7. SSO login (mock SAML IdP via SimpleSAMLphp)
8. MFA enrollment + recovery
9. Hub browse + filter + search
10. Admin: ban user + restore + audit log appears

### Setup

- Playwright config: 3 browsers (Chromium, Firefox, WebKit)
- Visual regression: snapshot pixel diff
- Run on CI: nightly + on main merge
- Coverage target: 80% backend, 60% frontend

**Effort**: 3 tuần.

---

## 🟢 P3.5 — Notifications Center

**Tại sao**: Hiện không có inbox UI, user miss execution failures.

### Schema

```sql
notifications (
  id UUID PK,
  user_id UUID FK users,
  workspace_id UUID FK NULL,
  type TEXT,  -- workflow.failed, member.invited, payment.succeeded, ...
  title TEXT,
  body TEXT,
  link_url TEXT,
  metadata JSONB,
  read_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

notification_preferences (
  user_id UUID FK users,
  notification_type TEXT,
  in_app BOOLEAN DEFAULT TRUE,
  email BOOLEAN DEFAULT TRUE,
  push BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (user_id, notification_type)
)
```

### UI

- Bell icon header + dropdown gần đây 10 notification
- `/notifications` page full inbox
- Mark read/unread, filter by type, archive
- Settings: per-type opt-in (email/push/in-app)
- Real-time push qua WebSocket (Socket service đã có)

### Channels

- In-app (WS push + DB persist)
- Email (qua mail service)
- Push (web push API + FCM cho mobile sau)
- Slack DM (cho workspace có Slack integration)

**Effort**: 1-2 tuần.

---

## 🟢 P3.6 — Workflow Advanced Features

### P3.6.1 Sub-workflows
Node `sub_workflow` cho phép gọi workflow khác. Recursion check (max depth 10). Parameter mapping in/out.

### P3.6.2 Loop node thật
Hiện file rỗng. Implement: foreach over array, while condition, break/continue.

### P3.6.3 Step-through Debugger
- Breakpoint UI: click vào node → set breakpoint
- Run with debug mode → pause ở breakpoint → inspect state → continue/step
- Backend: workflow runner check breakpoint set, persist state ở Redis, đợi resume signal

### P3.6.4 Workflow Versioning + Rollback
- `workflow_versions` table snapshot mỗi save
- UI: version history, diff view, "restore this version"
- Run history link tới version đã chạy

### P3.6.5 A/B Test Prompts
- Variant config: 2 prompt versions, 50/50 split
- Track conversion metric (user-defined)
- Statistical significance calculator

**Effort**: 3-4 tuần (chia nhỏ, làm song song).

---

## 🟢 P3.7 — Annotation & Feedback Loop

**Tại sao**: Enterprise muốn measure quality + retrain.

### Implementation

- Thumbs up/down ở mỗi message AI trả lời
- "Why?" textbox khi thumbs down
- Annotation table:
  ```sql
  message_annotations (
    id UUID PK,
    message_id UUID FK,
    user_id UUID FK,
    rating INT CHECK (rating IN (-1, 1)),
    feedback TEXT,
    expected_response TEXT,
    tags TEXT[],
    created_at
  )
  ```
- Export annotation dataset cho fine-tuning (JSONL format)
- Dashboard: rating trend, top failing patterns

**Effort**: 1 tuần.

---

## 📊 Phase 3 — Tổng kết

| Hạng mục | Effort |
|---|---|
| P3.1 Plugin system | 4-5 tuần |
| P3.2 LLM/VectorDB breadth | 3-4 tuần |
| P3.3 i18n | 2-3 tuần |
| P3.4 E2E tests | 3 tuần |
| P3.5 Notifications | 1-2 tuần |
| P3.6 Workflow advanced | 3-4 tuần |
| P3.7 Annotation | 1 tuần |
| **Tổng** | **17-22 tuần** (parallel ~4 tháng) |

**Sau Phase 3, đã sẵn sàng**: bán enterprise serious — competitive với Dify Cloud trên hầu hết feature axis.

---

# Phase 4 — Q4: Enterprise Deployment & Compliance (Tháng 10-12)

> Bán Fortune 500: trên cloud không đủ, phải có on-prem + compliance.

## 🟢 P4.1 — Helm Chart + Kubernetes

### Deliverables

- Helm chart trong `deploy/helm/agentforge/`
- Sub-charts cho: api, worker (mỗi tier 1 deployment), socket, frontend, postgres, redis, rabbitmq
- Values.yaml cho: replica count, resources, ingress, TLS, secrets management
- HPA (Horizontal Pod Autoscaler) cho worker tier
- PDB (Pod Disruption Budget) cho high availability
- NetworkPolicy: isolated namespaces
- Secrets: External Secrets Operator support (Vault/AWS Secrets Manager)

### Documentation

- `deploy/helm/README.md` với install command 1 dòng
- Reference architecture diagrams (3-node HA, single-node dev)
- Sizing guide: theo số user/workspace → tài nguyên cần

**Effort**: 2-3 tuần.

---

## 🟢 P4.2 — Terraform Modules

### Modules

- `terraform-aws-agentforge` (AWS)
  - VPC + subnets + NAT
  - RDS Postgres (Multi-AZ)
  - ElastiCache Redis
  - Amazon MQ for RabbitMQ
  - EKS cluster + node groups
  - ALB + ACM cert
  - S3 cho file storage
  - CloudWatch logs + alarms
- `terraform-gcp-agentforge` (GCP, sau)
- `terraform-azure-agentforge` (Azure, sau)

**Effort**: 2-3 tuần (AWS first).

---

## 🟢 P4.3 — On-prem / Air-gapped Install

### Scope

- Docker images export làm tar.gz (cho khách không có Internet)
- Helm chart hoạt động offline (helm pull + push to private registry)
- License server (offline): khách paste license key → AgentForge verify offline với public key
- Update mechanism: download package → upload qua admin UI → migrate

### License system

- License = JWT signed bởi AgentForge private key
- Claims: `org_name`, `max_users`, `expires_at`, `features` (array)
- Frontend hiển thị license status + expiry warning
- Soft enforcement: hết hạn vẫn chạy, banner đỏ; > 30 ngày = read-only

**Effort**: 3 tuần.

---

## 🟢 P4.4 — SOC2 Type 1 Preparation

### Checklist (~6 tháng prep + 3 tháng audit)

**Org-level**:
- [ ] Security policies docs (acceptable use, incident response, change management, etc.)
- [ ] Background checks process
- [ ] Security awareness training annually
- [ ] Vendor management (DPA với mọi 3rd party: Stripe, OpenAI, etc.)

**Technical**:
- [ ] Encryption at rest (Postgres TDE, S3 SSE)
- [ ] Encryption in transit (TLS 1.3 everywhere)
- [ ] Secrets management (Vault hoặc AWS Secrets Manager)
- [ ] MFA bắt buộc cho mọi employee
- [ ] Access review hàng quý
- [ ] Backup + disaster recovery (RTO < 4h, RPO < 1h)
- [ ] Vulnerability scanning (Snyk hoặc similar) — weekly
- [ ] Penetration test annually
- [ ] Audit log retention 7 năm
- [ ] Code review enforcement (đã có)
- [ ] Production access restricted (break-glass procedure)

**Auditor**: Drata/Vanta automate compliance evidence collection.

**Effort**: ~$30-50k auditor + 1 dedicated compliance person 6 tháng.

---

## 🟢 P4.5 — White-label / Custom Branding

**Tại sao**: Reseller hoặc enterprise muốn slap logo của họ.

### Customization layers

**Per-organization**:
- Logo (light/dark mode)
- Primary/accent color (HSL picker)
- Custom domain (CNAME → `app.customerdomain.com`)
- Custom email sender domain (DKIM/SPF setup guide)
- Login page background image
- Hide "AgentForge" branding (only Enterprise plan)
- Custom CSS injection (advanced)

**Per-workspace**:
- Logo
- Color scheme (override org default)

### Implementation

- `branding` JSONB column trong `organizations`
- Frontend: `useBranding()` hook đọc từ API → CSS variables override
- Custom domain: Cloudflare for SaaS hoặc Caddy + auto-SSL

**Effort**: 2 tuần.

---

## 🟢 P4.6 — Advanced Workflow Features

### P4.6.1 Workflow Marketplace mở rộng
- Templates công khai (đã có)
- Templates riêng workspace (mới)
- Templates riêng organization
- Approval workflow: editor publish → admin approve → live

### P4.6.2 Workflow as API
- Mỗi workflow auto-expose `POST /api/v1/workflows/{id}/run` với API key auth
- OpenAPI spec tự generate từ workflow input/output schema
- Rate limit per API key

### P4.6.3 Dataset Evaluation
- Upload dataset (CSV/JSONL): inputs + expected outputs
- Run workflow trên dataset → compare với expected
- Metrics: exact match, semantic similarity, BLEU, custom evaluator (LLM-as-judge)
- Track improvement across workflow versions

### P4.6.4 Model Load Balancing
- Multiple models per agent với fallback chain
- Round-robin, least-cost, fastest, custom routing
- Auto-failover khi primary 5xx

**Effort**: 3-4 tuần.

---

## 🟢 P4.7 — AWS Marketplace Listing

### Steps

1. AWS Partner Network sign-up
2. AWS Marketplace Seller Account
3. Container product (EKS-based) hoặc AMI product
4. Pricing: hourly hoặc annual contract
5. Customer onboarding flow (CloudFormation template)
6. Tax registration (multi-state US)

**Effort**: 4-6 tuần (chủ yếu legal + paperwork).

---

## 📊 Phase 4 — Tổng kết

| Hạng mục | Effort |
|---|---|
| P4.1 Helm chart | 2-3 tuần |
| P4.2 Terraform | 2-3 tuần |
| P4.3 On-prem + license | 3 tuần |
| P4.4 SOC2 prep | 3-6 tháng (parallel) |
| P4.5 White-label | 2 tuần |
| P4.6 Workflow advanced | 3-4 tuần |
| P4.7 AWS Marketplace | 4-6 tuần |
| **Tổng** | **15-21 tuần dev + SOC2 parallel** |

**Sau Phase 4**: bán Fortune 500, enterprise contracts $50-200k/năm, on-prem deployments.

---

# 🎯 Cross-cutting concerns (làm xuyên suốt)

## C.1 — Security

- Quarterly pentest
- Bug bounty program (HackerOne)
- Dependency scanning (Snyk, Dependabot)
- SAST (Semgrep)
- DAST (OWASP ZAP) trong CI
- CSP headers chặt
- Rate limiting per endpoint (chống brute force)
- DDoS protection (Cloudflare)

## C.2 — Documentation

- API docs auto-generated (OpenAPI)
- User docs site (Docusaurus): `/docs/`
- Tutorial videos (5-min mỗi feature lớn)
- Runbooks cho ops team
- Architecture Decision Records (ADRs) trong `docs/adrs/`

## C.3 — Customer Success

- Onboarding email sequence (Day 0/1/3/7/14/30)
- In-app tour (qua Intro.js hoặc tự build)
- Live chat support (Intercom/Crisp)
- Slack community
- Office hours hàng tuần

## C.4 — Performance

- Database query optimization (pg_stat_statements review hàng tháng)
- N+1 query check trong CI (django-debug-toolbar equivalent)
- CDN cho static assets (Cloudflare/CloudFront)
- Frontend bundle size budget (< 200KB initial)
- Lighthouse score > 90 trên landing + dashboard

## C.5 — Analytics

- Product analytics: PostHog (self-host hoặc cloud)
- Revenue analytics: ChartMogul hoặc tự build
- Funnel: signup → first agent → first chat → first published template → paid
- Cohort retention

---

# 📐 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Multi-tenancy migration broke existing data | Medium | High | Migration trên DB clone trước, rollback script, staging environment |
| Queue migration làm workflow chậm hơn | Low | Medium | Benchmark trước/sau, tune prefetch count, monitor p99 latency |
| SAML implementation buggy với 1 IdP | High | Medium | Test với 4 IdP khác nhau (Azure/Okta/Google/Keycloak), beta với 2 khách |
| SOC2 audit fail | Medium | High | Pre-audit với Drata/Vanta tools, hire fractional CISO, mock audit |
| Cost runaway (LLM calls) | High | High | Quota enforcement Phase 2.3 ngay từ đầu, alert thresholds |
| Plugin sandbox escape | Low | Critical | gVisor hoặc Firecracker microVM, security review mọi plugin |
| Helm chart drift giữa cloud vs on-prem | Medium | Medium | Single source helm chart, conditional values, test cả 2 mỗi release |

---

# 👥 Team sizing đề xuất

| Phase | Backend | Frontend | DevOps/SRE | QA | Designer | Total |
|---|---|---|---|---|---|---|
| Phase 0-1 | 2 | 1 | 1 (part) | — | — | 3-4 |
| Phase 2 | 2 | 2 | 1 | 1 | 1 (part) | 6-7 |
| Phase 3 | 3 | 2 | 1 | 1 | 1 | 8 |
| Phase 4 | 2 | 1 | 2 | 1 | — | + 1 compliance | 7-8 |

**Tổng năm 1**: ~6-8 người engineering full-time + 1 PM + 1 fractional CISO cho SOC2.

---

# 💰 Budget estimate (12 tháng)

| Khoản | USD |
|---|---|
| Engineering (6-8 people * $5-10k/mo VN rate hoặc $10-15k US) | $360k-1.4M |
| Infra (AWS dev/staging/prod) | $30-80k |
| Tools (CI, monitoring, security scanners) | $20-40k |
| SOC2 audit + tooling (Drata) | $40-60k |
| Pen test annual | $15-25k |
| Legal (contracts, privacy policy, etc.) | $20-40k |
| Marketing (landing, content, ads) | $50-150k |
| **Tổng** | **$535k - $1.8M** |

**Revenue target năm 1 để break-even**: $500k-1M ARR (tương đương 50-100 SMB customers, hoặc 5-10 mid-market, hoặc 2-3 enterprise).

---

# 🚦 Quick-Start Checklist (tuần đầu tiên)

Nếu bắt đầu hôm nay, đây là việc tuần 1:

- [ ] Setup GitHub Actions CI (P0.1)
- [ ] Add Postgres testcontainer fixture (P0.2)
- [ ] Tạo issue/milestone cho 4 phase
- [ ] Document hiện trạng: feature inventory + gap list (đã có ở review trước)
- [ ] Branch `feat/multi-tenancy` (P1.1) — bắt đầu với schema migration
- [ ] Hire/contract DevOps senior cho P0 + P4
- [ ] Pick observability vendor (Datadog vs self-host Tempo)

---

# 📚 References

- [Dify architecture](../../../dify/) — multi-tenancy + plugin daemon reference
- [Flowise enterprise](../../../Flowise/packages/server/src/enterprise/) — RBAC + SSO reference
- [Langflow](../../../langflow/) — Langchain integration reference
- [kien-truc-flowise-dify.md](../../../docs/kien-truc-flowise-dify.md) — comparison architecture
- [arch-system-overview](./system-overview.md) — current system architecture
- [arch-operations](./operations.md) — current ops runbook (will be expanded by P2.2 + P4.4)
- SOC2 Trust Services Criteria: <https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2>
- SAML 2.0 spec: <https://docs.oasis-open.org/security/saml/v2.0/>
- SCIM 2.0 spec: <https://datatracker.ietf.org/doc/html/rfc7644>

---

**Last updated**: 2026-05-10
**Owner**: TBD
**Status**: Draft v1
