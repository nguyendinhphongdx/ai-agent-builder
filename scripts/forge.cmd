@echo off
setlocal enabledelayedexpansion
:: ==========================================
:: AgentForge CLI (Windows CMD / PowerShell)
:: Usage: forge <command> [target]
:: ==========================================

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "CMD=%~1"
set "TARGET=%~2"

if "%CMD%"=="" goto :help
if "%CMD%"=="help" goto :help
if "%CMD%"=="--help" goto :help
if "%CMD%"=="-h" goto :help

goto :%CMD% 2>nul || (
    echo [31m Unknown command: %CMD%[0m
    goto :help
)

:: ==========================================
:: NETWORK
:: ==========================================
:ensure_network
docker network inspect agentforge >nul 2>nul || (
    echo [33mCreating network agentforge...[0m
    docker network create agentforge
)
goto :eof

:: ==========================================
:: START
:: ==========================================
:start
call :ensure_network
if "%TARGET%"=="" set "TARGET=all"

if "%TARGET%"=="all" (
    echo [32mStarting all services...[0m
    docker compose -f docker-compose.yml up -d
    echo [32m+ All services started[0m
    goto :urls
)

if "%TARGET%"=="services" (
    echo [32mStarting services...[0m
    docker compose -f docker-compose.yml up -d postgres redis rabbitmq socket code-sandbox mail dispatcher
    echo [32m+ Services started[0m
    goto :eof
)

if "%TARGET%"=="apps" (
    docker compose -f docker-compose.yml up -d backend frontend
    echo [32m+ Apps started[0m
    goto :eof
)

:: Single target — always use root compose
docker compose -f docker-compose.yml up -d %TARGET% 2>nul && (
    echo [32m+ %TARGET% started[0m
    goto :eof
)
echo [31mUnknown target: %TARGET%[0m
goto :eof

:: ==========================================
:: STOP
:: ==========================================
:stop
if "%TARGET%"=="" set "TARGET=all"

if "%TARGET%"=="all" (
    echo [33mStopping all...[0m
    docker compose -f docker-compose.yml down 2>nul
    for %%s in (postgres redis rabbitmq) do (
        docker compose -f services\%%s\docker-compose.yml down 2>nul
    )
    echo [32m+ All stopped[0m
    goto :eof
)

if "%TARGET%"=="services" (
    docker compose -f docker-compose.yml stop postgres redis rabbitmq socket code-sandbox mail dispatcher
    echo [32m+ Services stopped[0m
    goto :eof
)

if "%TARGET%"=="apps" (
    docker compose -f docker-compose.yml stop backend frontend
    echo [32m+ Apps stopped[0m
    goto :eof
)

docker compose -f docker-compose.yml stop %TARGET% 2>nul && (
    echo [32m+ %TARGET% stopped[0m
    goto :eof
)
echo [31mUnknown target: %TARGET%[0m
goto :eof

:: ==========================================
:: RESTART
:: ==========================================
:restart
call :stop
call :start
goto :eof

:: ==========================================
:: BUILD
:: ==========================================
:build
if "%TARGET%"=="" set "TARGET=all"
if "%TARGET%"=="all" (
    docker compose -f docker-compose.yml build
) else if "%TARGET%"=="backend" (
    docker compose -f docker-compose.yml build backend
) else if "%TARGET%"=="frontend" (
    docker compose -f docker-compose.yml build frontend
) else (
    echo [31mCan only build apps ^(backend^|frontend^)[0m
)
goto :eof

:: ==========================================
:: DEV
:: ==========================================
:dev
if "%TARGET%"=="backend" (
    echo [32mStarting backend dev server...[0m
    echo [33m  Tip: make sure infra is running ^(forge start infra^)[0m
    cd apps\backend
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    goto :eof
)
if "%TARGET%"=="frontend" (
    echo [32mStarting frontend dev server...[0m
    cd apps\frontend
    pnpm dev
    goto :eof
)
if "%TARGET%"=="socket" (
    echo [32mStarting socket service dev...[0m
    cd services\socket
    npm run start:dev
    goto :eof
)
if "%TARGET%"=="docs" (
    echo [32mStarting MCP docs server...[0m
    cd mcp-docs
    npx tsx src/index.ts
    goto :eof
)
if "%TARGET%"=="mail" (
    echo [32mStarting mail service dev...[0m
    cd services\mail
    pnpm dev
    goto :eof
)
if "%TARGET%"=="dispatcher" (
    echo [32mStarting dispatcher service dev...[0m
    cd services\dispatcher
    pnpm dev
    goto :eof
)
echo [31mSpecify target: forge dev backend^|frontend^|socket^|mail^|dispatcher^|docs[0m
goto :eof

:: ==========================================
:: LOGS
:: ==========================================
:logs
if "%TARGET%"=="" set "TARGET=all"
if "%TARGET%"=="all" (
    docker compose -f docker-compose.yml logs -f
    goto :eof
)
if exist "services\%TARGET%" (
    docker compose -f services\%TARGET%\docker-compose.yml logs -f
    goto :eof
)
if "%TARGET%"=="backend" (
    docker compose -f docker-compose.yml logs -f backend
    goto :eof
)
if "%TARGET%"=="frontend" (
    docker compose -f docker-compose.yml logs -f frontend
    goto :eof
)
echo [31mUnknown target: %TARGET%[0m
goto :eof

:: ==========================================
:: STATUS
:: ==========================================
:status
echo [34m=== Service Status ===[0m
echo.
echo Services:
for %%s in (postgres redis rabbitmq socket code-sandbox mail dispatcher) do (
    docker compose -f docker-compose.yml ps --status running 2>nul | findstr /i "%%s" >nul 2>nul && (
        echo   [32m+[0m %%s
    ) || (
        echo   [31mo[0m %%s
    )
)
echo.
echo Applications:
for %%s in (backend frontend) do (
    docker compose -f docker-compose.yml ps --status running 2>nul | findstr /i "%%s" >nul 2>nul && (
        echo   [32m+[0m %%s
    ) || (
        echo   [31mo[0m %%s
    )
)
echo.
goto :eof

:: ==========================================
:: INSTALL
:: ==========================================
:install
if "%TARGET%"=="backend" (
    cd apps\backend && pip install -e ".[dev]"
    goto :eof
)
if "%TARGET%"=="frontend" (
    cd apps\frontend && pnpm install
    goto :eof
)
if "%TARGET%"=="docs" (
    cd mcp-docs && npm install
    goto :eof
)
if "%TARGET%"=="all" (
    cd apps\backend && pip install -e ".[dev]" && cd ..\..
    cd apps\frontend && pnpm install && cd ..\..
    cd mcp-docs && npm install && cd ..
    goto :eof
)
echo [31mSpecify target: forge install backend^|frontend^|docs^|all[0m
goto :eof

:: ==========================================
:: TEST
:: ==========================================
:test
if "%TARGET%"=="backend" (
    cd apps\backend && pytest
    goto :eof
)
if "%TARGET%"=="frontend" (
    cd apps\frontend && pnpm test
    goto :eof
)
echo [31mSpecify target: forge test backend^|frontend[0m
goto :eof

:: ==========================================
:: MIGRATE
:: ==========================================
:migrate
echo [32mRunning database migrations...[0m
cd apps\backend && alembic upgrade head
echo [32m+ Migrations applied[0m
goto :eof

:: ==========================================
:: CLEAN
:: ==========================================
:clean
if "%TARGET%"=="" set "TARGET=all"
if "%TARGET%"=="all" (
    echo [31mRemoving all containers + volumes...[0m
    docker compose -f docker-compose.yml down -v 2>nul
    for %%s in (postgres redis rabbitmq) do (
        docker compose -f services\%%s\docker-compose.yml down -v 2>nul
    )
    echo [32m+ Cleaned[0m
    goto :eof
)
if exist "services\%TARGET%" (
    docker compose -f services\%TARGET%\docker-compose.yml down -v
    echo [32m+ %TARGET% cleaned[0m
    goto :eof
)
echo [31mCan only clean services[0m
goto :eof

:: ==========================================
:: HEALTH
:: ==========================================
:health
echo [34m=== Health Check ===[0m
curl -sf http://localhost:8000/api/health >nul 2>nul && (echo   [32m+[0m Backend API) || (echo   [31mx[0m Backend API)
curl -sf http://localhost:3000 >nul 2>nul && (echo   [32m+[0m Frontend) || (echo   [31mx[0m Frontend)
curl -sf http://localhost:3011/health >nul 2>nul && (echo   [32m+[0m Mail) || (echo   [31mx[0m Mail)
curl -sf http://localhost:3010/health >nul 2>nul && (echo   [32m+[0m Dispatcher) || (echo   [31mx[0m Dispatcher)
curl -sf http://localhost:4000/health >nul 2>nul && (echo   [32m+[0m Socket) || (echo   [31mx[0m Socket)
goto :eof

:: ==========================================
:: URLS
:: ==========================================
:urls
echo.
echo [33mServices running at:[0m
echo   Frontend:     http://localhost:3000
echo   Backend API:  http://localhost:8000/api
echo   API Docs:     http://localhost:8000/api/docs
echo   Socket:       http://localhost:4000 (health: /health)
echo   Mail:         http://localhost:3011 (health: /health)
echo   Dispatcher:   http://localhost:3010 (health: /health)
echo   PostgreSQL:   localhost:5432
echo   Redis:        localhost:6379
echo   RabbitMQ:     localhost:5672 (UI: http://localhost:15672)
echo.
goto :eof

:: ==========================================
:: HELP
:: ==========================================
:help
echo.
echo   [34mAgentForge[0m CLI
echo.
echo   Usage: forge ^<command^> [target]
echo.
echo   [32mLifecycle:[0m
echo     start [target]     Start services (docker)
echo     stop [target]      Stop services
echo     restart [target]   Restart services
echo     build [target]     Build docker images
echo     dev ^<target^>       Start local dev (hot-reload)
echo     clean [target]     Remove containers + volumes
echo.
echo   [32mMonitoring:[0m
echo     logs [target]      Tail logs
echo     status             Show running services
echo     health             Health check
echo.
echo   [32mDevelopment:[0m
echo     install ^<target^>   Install dependencies
echo     test ^<target^>      Run tests
echo     migrate            Run DB migrations
echo.
echo   [32mTargets:[0m
echo     all                Everything
echo     services           postgres + redis + rabbitmq + socket + code-sandbox + mail + dispatcher
echo     apps               backend + frontend
echo     ^<name^>             postgres ^| redis ^| rabbitmq ^| socket ^| code-sandbox ^| mail ^| dispatcher ^| backend ^| frontend
echo.
echo   [32mExamples:[0m
echo     forge start services
echo     forge dev backend
echo     forge logs socket
echo     forge stop all
echo.
goto :eof
