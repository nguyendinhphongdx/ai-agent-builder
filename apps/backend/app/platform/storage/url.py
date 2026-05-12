"""Resolve storage paths to full URLs. Use in Pydantic schemas."""

from app.platform.storage import get_storage


def resolve_url(path: str | None, access: str = "public") -> str | None:
    """Convert a storage key/path to a full URL.

    - None → None
    - Already absolute (http/https) → return as-is
    - Relative path → resolve via storage backend with access level
    """
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path

    key = path.lstrip("/")
    if key.startswith("uploads/"):
        key = key[len("uploads/"):]

    storage = get_storage()
    return storage.get_url(key, access)
