"""Upload configuration - add new file types here."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UploadTypeConfig:
    max_size: int              # bytes
    allowed_extensions: tuple[str, ...]
    access: str                # "public" | "private"
    path: str                  # storage subdirectory
    entity_types: tuple[str, ...]  # allowed entity_type values


UPLOAD_CONFIGS: dict[str, UploadTypeConfig] = {
    "avatar": UploadTypeConfig(
        max_size=2 * 1024 * 1024,       # 2MB
        allowed_extensions=("jpg", "jpeg", "png", "webp", "gif"),
        access="public",
        path="avatars",
        entity_types=("user", "agent"),
    ),
    "document": UploadTypeConfig(
        max_size=20 * 1024 * 1024,      # 20MB
        allowed_extensions=("pdf", "docx", "xlsx", "txt", "md", "csv", "html"),
        access="private",
        path="documents",
        entity_types=("knowledge_base",),
    ),
    "cv": UploadTypeConfig(
        max_size=10 * 1024 * 1024,      # 10MB
        allowed_extensions=("pdf",),
        access="private",
        path="cv",
        entity_types=("user",),
    ),
    "attachment": UploadTypeConfig(
        max_size=10 * 1024 * 1024,      # 10MB
        allowed_extensions=("jpg", "jpeg", "png", "webp", "gif", "pdf", "docx", "txt"),
        access="private",
        path="attachments",
        entity_types=("conversation", "message"),
    ),
}


def get_upload_config(file_type: str) -> UploadTypeConfig:
    config = UPLOAD_CONFIGS.get(file_type)
    if not config:
        valid = ", ".join(UPLOAD_CONFIGS.keys())
        raise ValueError(f"Unknown file type: {file_type}. Valid types: {valid}")
    return config
