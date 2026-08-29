"""Validate and accept custom profile avatars (stored in Postgres)."""

from __future__ import annotations

import io

# Upload cap: phone camera photos are often 2–8 MB.
MAX_AVATAR_BYTES = 8_000_000
# After resize/compress we keep storage Railway-friendly.
MAX_AVATAR_STORED_BYTES = 1_500_000
MAX_AVATAR_EDGE = 1600
JPEG_QUALITY = 88

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
            "Imagem demasiado grande (máx. 8 MB)."
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


def process_avatar_image(data: bytes) -> tuple[bytes, str]:
    """Resize + JPEG-compress so large phone photos stay sharp but compact."""
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - env misconfig
        raise AvatarValidationError(
            "Processamento de imagem indisponível no servidor."
        ) from exc

    try:
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGBA")
                background = Image.new("RGB", img.size, (12, 16, 14))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode == "L":
                img = img.convert("RGB")

            w, h = img.size
            longest = max(w, h)
            if longest > MAX_AVATAR_EDGE:
                scale = MAX_AVATAR_EDGE / float(longest)
                img = img.resize(
                    (max(1, int(w * scale)), max(1, int(h * scale))),
                    Image.Resampling.LANCZOS,
                )

            out = io.BytesIO()
            img.save(
                out,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )
            processed = out.getvalue()
    except AvatarValidationError:
        raise
    except Exception as exc:
        raise AvatarValidationError(
            "Não foi possível processar a imagem. Tenta outro ficheiro."
        ) from exc

    if not processed or len(processed) < 32:
        raise AvatarValidationError("Imagem processada inválida.")

    if len(processed) > MAX_AVATAR_STORED_BYTES:
        # Second pass: smaller edge / lower quality.
        try:
            with Image.open(io.BytesIO(processed)) as img:
                img = img.convert("RGB")
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                img.save(out, format="JPEG", quality=80, optimize=True)
                processed = out.getvalue()
        except Exception as exc:
            raise AvatarValidationError(
                "Imagem demasiado grande após compressão."
            ) from exc

    if len(processed) > MAX_AVATAR_STORED_BYTES:
        raise AvatarValidationError(
            "Imagem demasiado grande após compressão."
        )

    return processed, "image/jpeg"
