"""Validate and accept custom profile avatars (stored in Postgres)."""

from __future__ import annotations

# Max size kept small so BYTEA storage stays Railway-friendly without object storage.
MAX_AVATAR_BYTES = 1_000_000

ALLOWED_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),  # further checked below
}


class AvatarValidationError(ValueError):
    pass


def detect_content_type(data: bytes) -> str:
    if len(data) < 12:
        raise AvatarValidationError("Ficheiro de imagem demasiado pequeno.")

    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"

    raise AvatarValidationError(
        "Formato inválido. Usa JPEG, PNG ou WebP."
    )


def validate_avatar_upload(data: bytes, declared_type: str | None = None) -> str:
    if not data:
        raise AvatarValidationError("Ficheiro vazio.")

    if len(data) > MAX_AVATAR_BYTES:
        raise AvatarValidationError(
            "Imagem demasiado grande (máx. 1 MB)."
        )

    detected = detect_content_type(data)

    if declared_type:
        normalized = declared_type.split(";")[0].strip().lower()
        if normalized in {"image/jpg", "image/pjpeg"}:
            normalized = "image/jpeg"
        if normalized and normalized != detected:
            # Trust magic bytes; reject only if declared is an unsupported family.
            if normalized not in ALLOWED_TYPES and normalized != detected:
                raise AvatarValidationError(
                    "Tipo de ficheiro não suportado."
                )

    return detected
