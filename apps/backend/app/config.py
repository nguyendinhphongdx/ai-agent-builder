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
