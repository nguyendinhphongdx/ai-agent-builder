from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Cấu hình ứng dụng, đọc từ biến môi trường hoặc file .env."""

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # Thông tin ứng dụng
    APP_NAME: str = "AI Agent Builder"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Kết nối database PostgreSQL (async và sync)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lc_agent"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/lc_agent"

    # Cấu hình xác thực JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REMEMBER_ME_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # Auth token TTLs.
    # Short for the verification code (brute-forceable 6 digits); long for the
    # password-reset magic link which is cryptographically strong.
    EMAIL_VERIFICATION_TTL_MINUTES: int = 15
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # Public URLs used inside emails + OAuth callbacks
    FRONTEND_URL: str = "http://localhost:3000"

    # OAuth providers (leave empty to disable that provider)
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Fernet encryption key cho ai_credentials table
    # Generate một lần: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # Backend host (used to build full URLs for files)
    BASE_URL: str = "http://localhost:8000"

    # File storage
    UPLOAD_DIR: str = "uploads"
    STORAGE_TYPE: str = "local"  # "local" | "s3" | "gcs" | "minio"
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT_URL: str = ""  # For MinIO: http://localhost:9000
    GCS_BUCKET: str = ""
    # Service account credential — thứ tự resolution:
    #   1) GCS_SA_JSON: inline JSON (tiện cho env-only deploy như Fly/Railway)
    #   2) GCS_SA_FILE: path tới file SA JSON (đã mount vào container)
    #   3) ADC fallback — ~/.config/gcloud/... hoặc metadata server (GCE/Cloud Run/GKE)
    GCS_SA_JSON: str = ""
    GCS_SA_FILE: str = ""

    # Slack inbound trigger (Phase 2.4 Block 3). V1 uses one platform
    # Slack app distributed to orgs; signing secret is platform-level.
    # Per-app secrets land later when self-serve Slack-app install
    # ships. Empty → /api/slack/events returns 503.
    SLACK_SIGNING_SECRET: str = ""
    # Replay window. Slack defaults to 5 minutes server-side; mirror
    # that here unless an integrator explicitly relaxes.
    SLACK_REPLAY_WINDOW_SECONDS: int = 300

    # Socket service — public URL for frontend handshake, API secret for /emit auth.
    # SOCKET_API_SECRET must match the socket service's API_SECRET env. Dispatcher
    # doesn't inject this header; backend forwards it via `headers={}` param.
    SOCKET_PUBLIC_URL: str = "http://localhost:4000"
    SOCKET_API_SECRET: str = ""

    # Dispatcher — internal API gateway for all service-to-service calls
    # (mail, socket, code-sandbox, ...). Empty DISPATCHER_SECRET disables guard in dev.
    DISPATCHER_URL: str = "http://localhost:3010"  # Docker: http://dispatcher:3010
    DISPATCHER_SECRET: str = ""

    # Code sandbox — direct internal call from backend (not via dispatcher).
    # SANDBOX_SECRET must match the sandbox service's INTERNAL_TOKEN env.
    SANDBOX_URL: str = "http://code-sandbox:8000"
    SANDBOX_SECRET: str = ""

    # Redis — used for rate limiting (and future: caching, session store).
    # Empty disables rate limit (dev mode without Redis).
    REDIS_URL: str = "redis://localhost:6379/0"

    # Per-token rate limit on /api/external/* (req/min). 0 disables.
    EXTERNAL_RATE_LIMIT_PER_MIN: int = 60

    # Per-IP rate limit on /api/share/* (req/min) — embed widget channel,
    # callers are anonymous browsers so we key on client IP. 0 disables.
    SHARE_RATE_LIMIT_PER_MIN: int = 30

    # Audit log retention (days). Set to 0 to disable the purge job
    # (rows accumulate forever — useful in development). The default
    # is "free plan" — bumped per-org once billing tiers wire up.
    AUDIT_LOG_RETENTION_DAYS: int = 90

    # Cohere reranker API key. Empty = rerank pipeline falls back to
    # input order (retrieval still works, just no reranking benefit).
    # Per-KB / per-workspace keys can layer on via ai_credentials
    # later; for v1 a single platform key is enough.
    COHERE_API_KEY: str = ""

    # OpenTelemetry. Empty endpoint = tracing OFF (zero overhead, no
    # exporter, no instrumentation). Set this to your collector's gRPC
    # endpoint (Tempo / Datadog / New Relic / Honeycomb / Phoenix /
    # Grafana Cloud …) to enable.
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    # Optional bearer-style header set as ``Authorization``. Vendor-
    # specific format (e.g. Honeycomb uses ``x-honeycomb-team`` —
    # those go through OTEL_EXPORTER_OTLP_HEADERS directly).
    OTEL_EXPORTER_OTLP_HEADERS: str = ""
    OTEL_SERVICE_NAME: str = "agentforge-backend"
    # Insecure plain-text gRPC for collectors on the same network.
    # Production collectors should run TLS — leave False there.
    OTEL_EXPORTER_OTLP_INSECURE: bool = False

    # LLM-specific trace provider. Distinct from OpenTelemetry —
    # purpose-built platforms (Langfuse, LangSmith, Phoenix) ingest
    # full prompt + response payloads, not just span trees.
    #   Empty (default): auto-select Langfuse if its keys are set,
    #     else Noop (silent, zero-network).
    #   "langfuse" | "noop": explicit selection regardless of keys.
    TRACE_PROVIDER: str = ""
    # Langfuse. Set both keys to enable. ``LANGFUSE_HOST`` defaults to
    # cloud.langfuse.com — point at a self-hosted instance otherwise.
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = ""

    # ── Stripe (Hub V2 paid templates) ─────────────────────────────────
    # Empty = paid templates disabled — POST /templates/{id}/purchase
    # returns 503 instead of erroring deeper into the stack.
    # STRIPE_WEBHOOK_SECRET must match the endpoint's signing secret in
    # the Stripe Dashboard (`whsec_...`).
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    # Where Stripe redirects after Checkout. {SESSION_ID} placeholder is
    # filled by Stripe with the real session id at redirect time.
    STRIPE_SUCCESS_URL: str = ""  # e.g. https://app.example.com/hub/purchase-complete?session_id={CHECKOUT_SESSION_ID}
    STRIPE_CANCEL_URL: str = ""   # e.g. https://app.example.com/hub
    # Platform fee on paid template sales, in basis points (1/100 of a
    # percent). 1000 = 10%. Stripe also takes its own processing fee on
    # top, paid by the platform. Set to 0 for free passthrough during
    # promotion / staging tests.
    STRIPE_PLATFORM_FEE_BPS: int = 1000
    # Where Stripe sends the author after the Connect onboarding flow.
    # {ACCOUNT_ID} is replaced by Stripe at redirect time.
    STRIPE_CONNECT_RETURN_URL: str = ""  # e.g. https://app.example.com/settings/payouts?ok=1
    STRIPE_CONNECT_REFRESH_URL: str = "" # e.g. https://app.example.com/settings/payouts?refresh=1

    # ── Phase 2.3 platform subscriptions ───────────────────────────────
    # Recurring SaaS plans the PLATFORM bills its tenants on (distinct
    # from the marketplace destination-charge prices above). Each plan
    # has up to two prices:
    #   STRIPE_PRICE_<TIER>          – monthly recurring base fee
    #   STRIPE_PRICE_<TIER>_METERED  – per-1k-token overage (Stripe
    #                                  "usage" pricing). Empty = base
    #                                  fee only, no overage line item.
    # Leaving STRIPE_PRICE_<TIER> empty hides that tier from the
    # self-serve picker. Enterprise is typically empty (sales-led).
    # Where Stripe redirects after a billing Checkout finishes/cancels.
    # Distinct from STRIPE_SUCCESS_URL/CANCEL_URL which are for the
    # marketplace template purchase flow.
    STRIPE_BILLING_SUCCESS_URL: str = ""  # e.g. https://app.example.com/settings/billing?ok=1
    STRIPE_BILLING_CANCEL_URL: str = ""   # e.g. https://app.example.com/settings/billing?cancel=1
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_STARTER_METERED: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_PRO_METERED: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    STRIPE_PRICE_ENTERPRISE_METERED: str = ""

    # ── MoMo (VND payments — Vietnam) ─────────────────────────────────
    # Vietnamese e-wallet. Currency-locked to VND. Empty MOMO_PARTNER_CODE
    # disables VND checkout entirely (POST /purchase on a VND template
    # returns 503). Authors don't onboard a Connect-equivalent — V1 is
    # platform-collects with manual settlement.
    MOMO_PARTNER_CODE: str = ""
    MOMO_ACCESS_KEY: str = ""
    MOMO_SECRET_KEY: str = ""
    # Production: https://payment.momo.vn  ·  Sandbox: https://test-payment.momo.vn
    MOMO_ENDPOINT: str = "https://test-payment.momo.vn"
    # Where MoMo redirects the buyer's browser after payment. {orderId}
    # is appended by the gateway. Set to your /hub/purchase-complete page.
    MOMO_RETURN_URL: str = ""
    # Public HTTPS URL MoMo POSTs IPN events to (must match the host
    # serving /api/webhooks/momo). Leave empty in dev — IPN won't fire,
    # tests rely on the redirect query string instead.
    MOMO_NOTIFY_URL: str = ""

    # Embedding config cho Knowledge Base (platform-owned, snapshot vào KB khi create).
    # Provider module tự đọc env cho credentials (OPENAI_EMBEDDING_API_KEY, OLLAMA_BASE_URL...).
    EMBEDDING_PROVIDER: str = "ollama"     # "ollama" | "openai" | ...
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 768

    # Danh sách origin được phép truy cập API (CORS)
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Observability ──────────────────────────────────────────────────
    # "text" = human-readable (dev default). "json" = single-line JSON
    # per log record, ready for Loki/Datadog/CloudWatch ingestion.
    LOG_FORMAT: str = "text"
    # Empty SENTRY_DSN disables the SDK entirely — local dev, tests, CI
    # never touch the Sentry network.
    SENTRY_DSN: str = ""
    # Tag every event so dashboards can split prod/staging/dev.
    ENVIRONMENT: str = "development"
    # Release tag — let CI/CD inject the git SHA so source maps + issue
    # grouping line up. Empty falls back to Sentry's auto-release.
    RELEASE: str = ""
    # Sample rate for performance traces (0..1). Errors are always sent.
    # Default 0 (off) so we don't burn quota until perf monitoring is wanted.
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0


settings = Settings()
