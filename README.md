<div align="center">

# 🔥 AgentForge

**The open-source LLM app platform.**
Build AI agents, visual workflows, RAG pipelines, and multi-agent systems — self-hosted, batteries-included.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL + pgvector](https://img.shields.io/badge/Postgres-pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

[Quick Start](#-quick-start) · [Features](#-features) · [Why AgentForge?](#why-agentforge) · [Development](DEVELOPMENT.md) · [Documentation](docs/)

</div>

---

## Why AgentForge?

AgentForge is a **production-ready, self-hosted alternative to Dify, Flowise, and LangSmith**.
It combines agent building, visual workflows, RAG, observability, and billing — all in a single
open-source monorepo you can run anywhere.

Whether you're a solo developer prototyping a chatbot or a company shipping AI products to paying
customers, AgentForge gives you the full stack: **drag-and-drop workflow design, knowledge bases
with pgvector, SSO/SCIM, Stripe billing, and Langfuse observability — out of the box.**

> **No vendor lock-in. No per-seat pricing. No credit limits. Just your infrastructure.**

---

## ✨ Features

### 🤖 Agent Builder

Create AI agents in minutes with a split-view editor — config on the left, live chat preview on
the right. Switch LLM providers (OpenAI, Anthropic, Google, Ollama) on the fly, attach tools and
knowledge bases, and ship to production with one click.

### 🔀 Visual Workflows

Drag-and-drop workflow editor powered by React Flow that compiles to LangGraph StateGraphs.
Branching, loops, human-in-the-loop, sub-workflows, and per-node execution tracking with token
usage and latency metrics.

### 📚 Knowledge Bases (RAG)

Upload PDF, DOCX, TXT, MD, CSV, or HTML. AgentForge handles the full pipeline: parse → chunk →
embed → cosine search via **pgvector**. Auto-generates a retrieval tool for any agent — no glue
code required.

### 🛠️ Tools & Integrations

4 built-in tool types (HTTP Request, Code Executor, Web Scraper, DB Query) plus dynamic JSON
Schema → Pydantic conversion for custom tools. Connect to anything with REST, GraphQL, OAuth,
or webhooks.

### 🎯 Multi-Agent Orchestration

Supervisor/worker and peer collaboration patterns. Mix LLM providers across agents (e.g., GPT-4
supervises a Claude worker and a Gemini researcher). Built on LangGraph.

### 📨 Triggers Everywhere

Trigger agents from anywhere your users already are:

- 🌐 **Webhooks** (HMAC-signed, replay protection)
- 📧 **Email** (IMAP poll)
- 💬 **Slack**, **Discord**, **Microsoft Teams**
- ⏰ **Scheduled** (cron)

### 💬 Streaming Chat

Token-by-token WebSocket streaming with tool-call indicators, markdown rendering, conversation
history, and embeddable widgets for any website.

### 🏢 Enterprise-Grade

Everything you need to ship AI products to real customers:

- **Multi-tenant workspaces** with RBAC and audit logs
- **MFA** (TOTP), **SSO** (SAML/OIDC), **SCIM** provisioning
- **Stripe** billing (Checkout, Subscriptions, Connect payouts) + **MoMo** for VND payments
- **OpenTelemetry** tracing, **Langfuse** LLM traces, cost dashboard, rate limiting
- **Admin console** with user/workspace management, hub moderation, personal access tokens

### 🏪 Template Hub

Share and install agent, workflow, and tool templates across workspaces. Author payouts via
Stripe Connect — turn your agents into revenue.

---

## ⚡ Quick Start

Get AgentForge running in under 2 minutes:

```bash
git clone <repo-url> lc-agent && cd lc-agent

cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.example apps/frontend/.env.local
# Edit apps/backend/.env → set OPENAI_API_KEY

docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.cli.seed_admin \
    --email admin@example.com --password 'ChangeMe!'
```

Then open **<http://localhost:3000>** and sign in. That's it.

> 📘 For local dev (hot-reload, manual setup, CLI reference, env vars, migrations, ops) see **[DEVELOPMENT.md](DEVELOPMENT.md)**.

---

## 🏗️ Tech Stack

| Backend                  | Frontend                         | Infrastructure              |
| ------------------------ | -------------------------------- | --------------------------- |
| Python 3.12              | Next.js 16 · React 19            | PostgreSQL 16 + pgvector    |
| FastAPI (async)          | TypeScript · Tailwind            | Redis · RabbitMQ            |
| LangChain · LangGraph    | shadcn/ui (radix-ui)             | Docker Compose              |
| SQLAlchemy 2.0           | TanStack Query · Zustand         | Self-hosted, anywhere       |

---

## 📐 Architecture

```text
lc-agent/
├── apps/
│   ├── backend/       FastAPI + LangGraph
│   └── frontend/      Next.js 16
├── services/          Postgres · Redis · RabbitMQ · Dispatcher · Mail · Socket · Code Sandbox
├── docs/              60+ spec files (architecture, conventions, backend, frontend, API)
├── mcp-docs/          MCP server for AI-assisted doc search
└── scripts/forge.sh   CLI for managing the whole stack
```

See **[DEVELOPMENT.md](DEVELOPMENT.md)** for the full layout and module breakdown.

---

## 📦 Use Cases

- 🤖 **Customer support chatbots** with knowledge-base-aware responses
- 📊 **Internal copilots** that query your databases and APIs
- 🔄 **AI-powered workflow automation** (intake forms, triage, routing)
- 🎓 **Tutoring & coaching agents** with conversation memory
- 🛒 **AI product features** for SaaS — agents-as-a-service with billing built-in
- 🏬 **Template marketplaces** where authors earn from their agents

---

## 🗺️ Roadmap

- [x] Agent builder with multi-provider LLM support
- [x] Visual workflow editor with LangGraph compilation
- [x] RAG with pgvector
- [x] Multi-agent orchestration
- [x] Inbound triggers (webhook, email, Slack, Discord, Teams, cron)
- [x] Stripe & MoMo billing
- [x] SSO/SCIM, MFA, audit logs
- [x] Template hub with author payouts
- [x] OpenTelemetry + Langfuse observability
- [ ] Voice agents (WebRTC)
- [ ] On-prem LLM gateway with model routing
- [ ] Fine-tuning pipeline

---

## 🤝 Contributing

We welcome contributions! Whether it's a bug fix, a new feature, docs improvements, or a new
template for the hub — please open an issue or PR.

Before contributing:

1. Read **[CLAUDE.md](CLAUDE.md)** for project conventions (4-layer backend modules, feature-based
   frontend, httpOnly cookie auth, snake_case plural tables)
2. See **[DEVELOPMENT.md](DEVELOPMENT.md)** for local setup
3. Browse **[docs/conventions/](docs/conventions/)** for code style rules

---

## 📜 License

[MIT](LICENSE) — free for personal and commercial use. No telemetry, no callbacks, no surprises.

---

<div align="center">

**[⬆ Back to top](#-agentforge)**

Built with FastAPI · LangGraph · Next.js · Postgres

If AgentForge is useful to you, please ⭐ the repo!

</div>
