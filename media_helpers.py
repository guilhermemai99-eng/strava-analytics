"""Proxy allowlisted Strava/CDN media so profile and activity photos load."""

from __future__ import annotations

from urllib.parse import quote, urlparse

import requests

ALLOWED_MEDIA_HOSTS = frozenset(
    {
        "dgalywyr863hv.cloudfront.net",
        "dz3we2j92f51n.cloudfront.net",
        "strava.com",
        "www.strava.com",
        "graph.facebook.com",
        "scontent.xx.fbcdn.net",
        "i.imgur.com",
        "images.unsplash.com",
        "picsum.photos",
    }
)


def is_allowed_media_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in ALLOWED_MEDIA_HOSTS:
        return True
    if host.endswith(".cloudfront.net"):
        return True
    if host.endswith(".strava.com"):
        return True
    if host.endswith(".fbcdn.net"):
        return True
    return False


def proxied_media_url(url: str | None) -> str | None:
    """Same-origin proxy URL for external media; pass through app-relative paths."""
    if not url or not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None
    if raw.startswith("/"):
        return raw
    if not is_allowed_media_url(raw):
        return raw
    return f"/api/media/proxy?url={quote(raw, safe='')}"


def fetch_remote_media(url: str, *, timeout: float = 12.0) -> tuple[bytes, str]:
    """Fetch bytes + content-type for an allowlisted remote image URL."""
    if not is_allowed_media_url(url):
        raise ValueError("URL de media não permitida.")

    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PulseMedia/1.0)",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        allow_redirects=True,
    )
    if response.status_code != 200:
        raise ValueError(f"Falha a obter media ({response.status_code}).")

    content_type = (response.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
    if not content_type.startswith("image/"):
        raise ValueError("Resposta não é uma imagem.")

    data = response.content
    if not data:
        raise ValueError("Imagem vazia.")
    if len(data) > 8_000_000:
        raise ValueError("Imagem demasiado grande.")
    return data, content_type
