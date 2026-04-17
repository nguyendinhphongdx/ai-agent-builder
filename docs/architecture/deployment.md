---
id: arch-deployment
title: Deployment - Docker Compose & Environment
domain: architecture
tags: [docker, docker-compose, deployment, environment, ports, volumes, healthcheck]
related: [arch-system-overview, arch-project-structure]
summary: Docker Compose orchestration. Services extend from services/ dir. Backend port 8000, frontend 3000, postgres 5432, redis 6379, rabbitmq 5672/15672.
---

# Deployment

## Ports

| Service | Port | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000/api |
| Backend Docs | 8000 | http://localhost:8000/api/docs |
| PostgreSQL | 5432 | postgresql://localhost:5432/lc_agent |
| Redis | 6379 | redis://localhost:6379/0 |
| RabbitMQ | 5672 | amqp://localhost:5672/ |
| RabbitMQ UI | 15672 | http://localhost:15672 |

## Running

```bash
# All services + apps
docker compose up

# Only infrastructure
docker compose up postgres redis rabbitmq

# Single service standalone
cd services/postgres && docker compose up

# Development (without Docker)
cd apps/backend && pip install -e . && uvicorn app.main:app --reload
cd apps/frontend && pnpm install && pnpm dev
```

## Environment Variables

### Backend (`apps/backend/.env`)
| Variable | Default | Description |
|---|---|---|
| DATABASE_URL | postgresql+asyncpg://postgres:postgres@localhost:5432/lc_agent | Async DB connection |
| DATABASE_URL_SYNC | postgresql://postgres:postgres@localhost:5432/lc_agent | Sync DB (Alembic) |
| SECRET_KEY | dev-secret-key... | JWT signing key |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Access token TTL |
| REFRESH_TOKEN_EXPIRE_DAYS | 7 | Refresh token TTL |
| OPENAI_API_KEY | (empty) | OpenAI API key |
| ANTHROPIC_API_KEY | (empty) | Anthropic API key |
| CORS_ORIGINS | ["http://localhost:3000"] | Allowed CORS origins |
| UPLOAD_DIR | uploads | File upload directory |
| DEBUG | false | Enable debug mode |
| REDIS_URL | redis://localhost:6379/0 | Redis connection |
| RABBITMQ_URL | amqp://guest:guest@localhost:5672/ | RabbitMQ connection |

### Frontend (`apps/frontend/.env.local`)
| Variable | Default | Description |
|---|---|---|
| NEXT_PUBLIC_API_URL | http://localhost:8000/api | Backend API base URL |
| NEXT_PUBLIC_WS_URL | ws://localhost:8000/api | WebSocket base URL |

## Database Migrations

```bash
cd apps/backend
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```
