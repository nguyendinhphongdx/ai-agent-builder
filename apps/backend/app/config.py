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

    # API key cho các nhà cung cấp LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

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

    # Socket (frontend connection URL; backend emits go through dispatcher)
    SOCKET_PUBLIC_URL: str = "http://localhost:4000"

    # Dispatcher — internal API gateway for all service-to-service calls
    # (mail, socket, code-sandbox, ...). Empty DISPATCHER_SECRET disables guard in dev.
    DISPATCHER_URL: str = "http://localhost:3010"  # Docker: http://dispatcher:3010
    DISPATCHER_SECRET: str = ""

    # Embedding mặc định cho Knowledge Base
    EMBEDDING_PROVIDER: str = "ollama"  # "openai" | "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 768
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Danh sách origin được phép truy cập API (CORS)
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
