---
id: arch-dependencies
title: Dependencies - All Packages & Version Policy
domain: architecture
tags: [dependencies, packages, pyproject, package-json, versions, langchain, nextjs]
related: [arch-system-overview, conventions-backend, conventions-frontend]
summary: All backend (pyproject.toml) and frontend (package.json) dependencies with rationale. Version policy uses minimum version constraints.
---

# Dependencies

## Backend (`apps/backend/pyproject.toml`)

### Core
| Package | Version | Why |
|---|---|---|
| fastapi[standard] | >=0.115 | Web framework, auto OpenAPI docs |
| uvicorn[standard] | >=0.30 | ASGI server, hot-reload |
| pydantic-settings | >=2.6 | Env var config with type validation |
| python-multipart | >=0.0.12 | File upload support |
| httpx | >=0.27 | Async HTTP client for tools |

### Database
| Package | Version | Why |
|---|---|---|
| sqlalchemy[asyncio] | >=2.0 | Async ORM |
| asyncpg | >=0.30 | PostgreSQL async driver |
| alembic | >=1.14 | Database migrations |
| pgvector | >=0.3 | Vector column type + similarity search |

### Auth
| Package | Version | Why |
|---|---|---|
| python-jose[cryptography] | >=3.3 | JWT encode/decode |
| passlib[bcrypt] | >=1.7 | Password hashing |

### AI/LLM
| Package | Version | Why |
|---|---|---|
| langchain | >=0.3 | Core abstractions, tools |
| langchain-openai | >=0.3 | OpenAI LLM + embeddings |
| langchain-anthropic | >=0.3 | Anthropic Claude models |
| langchain-community | >=0.3 | Document loaders |
| langchain-ollama | >=0.3 | Local models via Ollama |
| langgraph | >=0.2 | Agent orchestration, workflows |
| langchain-text-splitters | >=0.3 | Document chunking |

### Document Processing
| Package | Version | Why |
|---|---|---|
| pypdf | >=4.0 | PDF parsing |
| docx2txt | >=0.8 | DOCX parsing |

## Frontend (`apps/frontend/package.json`)

### Core
| Package | Version | Why |
|---|---|---|
| next | 16.x | React framework (App Router) |
| react / react-dom | 19.x | UI library |
| typescript | 5.x | Type safety |

### UI
| Package | Why |
|---|---|
| tailwindcss | Utility-first CSS |
| @base-ui/react | shadcn/ui component primitives (NOT @radix-ui) |
| class-variance-authority | Variant-based component styling |
| clsx + tailwind-merge | Conditional class merging |
| lucide-react | Icons |
| next-themes | Dark/light mode |
| sonner | Toast notifications |

### Data & State
| Package | Why |
|---|---|
| @tanstack/react-query | Server state (API data caching, mutations) |
| zustand | Client state (UI-only: streaming, selected node) |
| axios | HTTP client with interceptors |

### Forms
| Package | Why |
|---|---|
| react-hook-form | Form state management |
| @hookform/resolvers | Zod integration |
| zod | Schema validation |

### Specialized
| Package | Why |
|---|---|
| @xyflow/react | React Flow v12 for workflow editor |
| react-markdown + remark-gfm | Markdown rendering in chat |

## Version Policy
- Backend: minimum version constraints (`>=`), pip resolves latest compatible
- Frontend: pnpm lockfile pins exact versions
- No upper bounds unless known breaking changes
