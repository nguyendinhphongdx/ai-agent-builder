#!/usr/bin/env bash
# ==========================================
# AgentForge CLI (Linux / Mac / Git Bash)
# Usage: ./forge.sh <command> [target]
# ==========================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ── Config ──
SERVICES=(postgres redis rabbitmq socket code-sandbox mail dispatcher)
APPS=(backend frontend)

# ── Colors ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; }
info() { echo -e "${YELLOW}$1${NC}"; }
head() { echo -e "${BLUE}=== $1 ===${NC}"; }

# ── Network ──
NETWORK_NAME="agentforge"
ensure_network() {
    if ! docker network inspect "$NETWORK_NAME" > /dev/null 2>&1; then
        info "Creating network $NETWORK_NAME..."
        docker network create "$NETWORK_NAME"
    fi
}

# ── Helpers ──
svc_compose() { docker compose -f "services/$1/docker-compose.yml" "${@:2}"; }
root_compose() { docker compose -f docker-compose.yml "$@"; }

is_service() { [[ -d "services/$1" ]]; }
is_app() { [[ "$1" == "backend" || "$1" == "frontend" ]]; }

# ── Start ──
do_start() {
    ensure_network
    local target="${1:-all}"
    case "$target" in
        all)
            head "Starting all"
            root_compose up -d
            ok "All services started"
            show_urls
            ;;
        services)
            head "Starting services"
            root_compose up -d "${SERVICES[@]}"
            ok "Services started"
            ;;
        apps)
            head "Starting apps"
            root_compose up -d "${APPS[@]}"
            ok "Apps started"
            ;;
        *)
            if is_service "$target" || is_app "$target"; then
                root_compose up -d "$target"
            else
                err "Unknown target: $target"; exit 1
            fi
            ok "$target started"
            ;;
    esac
}

# ── Stop ──
do_stop() {
    local target="${1:-all}"
    case "$target" in
        all)
            head "Stopping all"
            root_compose down 2>/dev/null || true
            ok "All stopped"
            ;;
        services)
            root_compose stop "${SERVICES[@]}"
            ok "Services stopped"
            ;;
        apps)
            root_compose stop "${APPS[@]}"
            ok "Apps stopped"
            ;;
        *)
            if is_service "$target" || is_app "$target"; then
                root_compose stop "$target"
            else
                err "Unknown target: $target"; exit 1
            fi
            ok "$target stopped"
            ;;
    esac
}

# ── Restart ──
do_restart() {
    do_stop "${1:-all}"
    do_start "${1:-all}"
}

# ── Build ──
do_build() {
    local target="${1:-all}"
    case "$target" in
        all)      root_compose build ;;
        backend)  root_compose build backend ;;
        frontend) root_compose build frontend ;;
        *)        err "Can only build apps (backend|frontend)"; exit 1 ;;
    esac
    ok "$target built"
}

# ── Dev (local, hot-reload) ──
do_dev() {
    local target="${1:-}"
    case "$target" in
        backend)
            info "Starting backend dev server..."
            info "  Tip: make sure services are running (./forge.sh start services)"
            cd apps/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
            ;;
        frontend)
            info "Starting frontend dev server..."
            cd apps/frontend && pnpm dev
            ;;
        socket)
            info "Starting socket service dev..."
            cd services/socket && npm run start:dev
            ;;
        docs)
            info "Starting MCP docs server..."
            cd mcp-docs && npx tsx src/index.ts
            ;;
        mail)
            info "Starting mail service dev..."
            cd services/mail && pnpm dev
            ;;
        dispatcher)
            info "Starting dispatcher service dev..."
            cd services/dispatcher && pnpm dev
            ;;
        "")
            err "Specify target: ./forge.sh dev backend|frontend|socket|mail|dispatcher|docs"; exit 1
            ;;
        *)
            err "Unknown dev target: $target"; exit 1
            ;;
    esac
}

# ── Logs ──
do_logs() {
    local target="${1:-all}"
    case "$target" in
        all)      root_compose logs -f ;;
        services) root_compose logs -f "${SERVICES[@]}" ;;
        apps)     root_compose logs -f backend frontend ;;
        *)      root_compose logs -f "$target"
            ;;
    esac
}

# ── Status ──
do_status() {
    head "Service Status"
    echo ""
    info "Services:"
    for svc in "${SERVICES[@]}"; do
        if root_compose ps --status running 2>/dev/null | grep -q "$svc"; then
            echo -e "  ${GREEN}●${NC} $svc"
        else
            echo -e "  ${RED}○${NC} $svc"
        fi
    done
    echo ""
    info "Applications:"
    for svc in "${APPS[@]}"; do
        if root_compose ps --status running 2>/dev/null | grep -q "$svc"; then
            echo -e "  ${GREEN}●${NC} $svc"
        else
            echo -e "  ${RED}○${NC} $svc"
        fi
    done
    echo ""
}

# ── Health ──
do_health() {
    head "Health Check"
    curl -sf http://localhost:8000/api/health > /dev/null 2>&1 && ok "Backend API" || err "Backend API"
    curl -sf http://localhost:3000 > /dev/null 2>&1 && ok "Frontend" || err "Frontend"
    curl -sf http://localhost:3011/health > /dev/null 2>&1 && ok "Mail" || err "Mail"
    curl -sf http://localhost:3010/health > /dev/null 2>&1 && ok "Dispatcher" || err "Dispatcher"
    curl -sf http://localhost:4000/health > /dev/null 2>&1 && ok "Socket" || err "Socket"
    docker exec "$(svc_compose postgres ps -q postgres 2>/dev/null)" pg_isready > /dev/null 2>&1 && ok "PostgreSQL" || err "PostgreSQL"
    docker exec "$(svc_compose redis ps -q redis 2>/dev/null)" redis-cli ping > /dev/null 2>&1 && ok "Redis" || err "Redis"
}

# ── Install ──
do_install() {
    local target="${1:-}"
    case "$target" in
        backend)  cd apps/backend && pip install -e ".[dev]" ;;
        frontend) cd apps/frontend && pnpm install ;;
        docs)     cd mcp-docs && npm install ;;
        all)      do_install backend; do_install frontend; do_install docs ;;
        "")       err "Specify target: ./forge.sh install backend|frontend|docs|all"; exit 1 ;;
    esac
}

# ── Test ──
do_test() {
    local target="${1:-}"
    case "$target" in
        backend)  cd apps/backend && pytest ;;
        frontend) cd apps/frontend && pnpm test ;;
        "")       err "Specify target: ./forge.sh test backend|frontend"; exit 1 ;;
    esac
}

# ── Migrate ──
do_migrate() {
    info "Running database migrations..."
    cd apps/backend && alembic upgrade head
    ok "Migrations applied"
}

# ── Clean ──
do_clean() {
    local target="${1:-all}"
    case "$target" in
        all)
            head "Cleaning all containers + volumes"
            root_compose down -v 2>/dev/null || true
            ok "Cleaned"
            ;;
        *)
            err "Use: ./forge.sh clean all"; exit 1
            ;;
    esac
}

# ── URLs ──
show_urls() {
    echo ""
    info "Services running at:"
    echo "  Frontend:     http://localhost:3000"
    echo "  Backend API:  http://localhost:8000/api"
    echo "  API Docs:     http://localhost:8000/api/docs"
    echo "  Socket:       http://localhost:4000 (health: /health)"
    echo "  Mail:         http://localhost:3011 (health: /health)"
    echo "  Dispatcher:   http://localhost:3010 (health: /health)"
    echo "  PostgreSQL:   localhost:5432"
    echo "  Redis:        localhost:6379"
    echo "  RabbitMQ:     localhost:5672 (UI: http://localhost:15672)"
    echo ""
}

# ── Help ──
show_help() {
    echo ""
    echo -e "  ${BLUE}AgentForge${NC} CLI"
    echo ""
    echo "  Usage: ./forge.sh <command> [target]"
    echo ""
    echo -e "  ${GREEN}Lifecycle:${NC}"
    echo "    start [target]     Start services (docker)"
    echo "    stop [target]      Stop services"
    echo "    restart [target]   Restart services"
    echo "    build [target]     Build docker images"
    echo "    dev <target>       Start local dev (hot-reload)"
    echo "    clean [target]     Remove containers + volumes"
    echo ""
    echo -e "  ${GREEN}Monitoring:${NC}"
    echo "    logs [target]      Tail logs"
    echo "    status             Show running services"
    echo "    health             Health check"
    echo ""
    echo -e "  ${GREEN}Development:${NC}"
    echo "    install <target>   Install dependencies"
    echo "    test <target>      Run tests"
    echo "    migrate            Run DB migrations"
    echo ""
    echo -e "  ${GREEN}Targets:${NC}"
    echo "    all                Everything"
    echo "    services           postgres + redis + rabbitmq + socket + code-sandbox + mail + dispatcher"
    echo "    apps               backend + frontend"
    echo "    <name>             postgres | redis | rabbitmq | socket | code-sandbox | mail | dispatcher | backend | frontend"
    echo ""
    echo -e "  ${GREEN}Examples:${NC}"
    echo "    ./forge.sh start services"
    echo "    ./forge.sh dev backend"
    echo "    ./forge.sh logs socket"
    echo "    ./forge.sh stop all"
    echo ""
}

# ── Main ──
case "${1:-help}" in
    start)   do_start "${2:-}" ;;
    stop)    do_stop "${2:-}" ;;
    restart) do_restart "${2:-}" ;;
    build)   do_build "${2:-}" ;;
    dev)     do_dev "${2:-}" ;;
    logs)    do_logs "${2:-}" ;;
    status)  do_status ;;
    health)  do_health ;;
    install) do_install "${2:-}" ;;
    test)    do_test "${2:-}" ;;
    migrate) do_migrate ;;
    clean)   do_clean "${2:-}" ;;
    help|--help|-h) show_help ;;
    *) err "Unknown command: $1"; show_help; exit 1 ;;
esac
