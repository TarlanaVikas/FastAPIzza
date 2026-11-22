"""Safe handling of user-uploaded images (avatars and pizza photos)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from .config import get_settings

settings = get_settings()

# Detected from the file's leading bytes, never from the client-supplied name or MIME type.
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]


def _detect_extension(head: bytes) -> str | None:
    for signature, ext in _SIGNATURES:
        if head.startswith(signature):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def ensure_upload_dir() -> Path:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings.upload_dir


def public_url(stored: str | None) -> str | None:
    """Turn a stored value into a URL the browser can load."""
    if not stored:
        return None
    if stored.startswith(("/", "http://", "https://")):
        return stored
    return f"/upload/{stored}"


def save_image(upload: UploadFile) -> str:
    """Validate and store an uploaded image, returning the generated file name."""
    data = upload.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Image must be {limit_mb} MB or smaller.")
    extension = _detect_extension(data[:16])
    if extension is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a PNG, JPEG, WebP or GIF image.")
    name = f"{uuid.uuid4().hex}{extension}"
    (ensure_upload_dir() / name).write_bytes(data)
    return name


def delete_image(stored: str | None) -> None:
    """Remove a previously stored upload. Built-in artwork (paths) is never touched."""
    if not stored or stored.startswith(("/", "http://", "https://")):
        return
    target = ensure_upload_dir() / Path(stored).name
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass


def has_file(upload: UploadFile | None) -> bool:
    return upload is not None and bool(upload.filename)
