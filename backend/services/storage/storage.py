"""Supabase Storage helpers: bucket resolution, path validation and object fetch.

Binary content never touches PostgreSQL. Clients upload directly to Storage and the
API records the path and metadata, so this module's job is to make sure the recorded
path is one this backend would actually serve, and to fetch objects back when the AI
layer needs to look at them.

Buckets are public in the prototype. The contract here is written so that switching
them to private later changes only ``object_url``.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from backend.core.config import settings
from backend.core.errors import APIError, STORAGE_ERROR, VALIDATION_ERROR

log = logging.getLogger(__name__)

PROBLEM = "problem"
EXPERIENCE = "experience"
KNOWLEDGE = "knowledge"
CERTIFICATE = "certificate"

# Guards an image fetch from pulling something unreasonable into memory.
MAX_IMAGE_BYTES = 8 * 1024 * 1024

# Matches a path traversal, or any URI scheme. The scheme pattern allows digits and
# +.- after the first letter, so s3://, gs:// and the like are caught too.
_UNSAFE = re.compile(r"(\.\.)|(^[a-zA-Z][a-zA-Z0-9+.\-]*://)")


def bucket_for(kind: str) -> str:
    buckets = {
        PROBLEM: settings.storage_problem_bucket,
        EXPERIENCE: settings.storage_experience_bucket,
        KNOWLEDGE: settings.storage_knowledge_bucket,
        CERTIFICATE: settings.storage_certificate_bucket,
    }
    if kind not in buckets:
        raise APIError(STORAGE_ERROR, f"Unknown storage kind '{kind}'.")
    return buckets[kind]


def normalise_path(kind: str, storage_path: str) -> str:
    """Return the object path relative to its bucket.

    Clients variously send ``<bucket>/<id>/file.jpg`` or just ``<id>/file.jpg``. Both
    are accepted and stored the same way, so the fetch side has one shape to handle.
    """
    path = (storage_path or "").strip().lstrip("/")
    if not path:
        raise APIError(VALIDATION_ERROR, "storage_path is required.")
    if _UNSAFE.search(path):
        # A traversal or absolute URL would let a caller point a record at something
        # outside the bucket it claims to be in.
        raise APIError(VALIDATION_ERROR, "storage_path must be a plain path inside the bucket.")

    bucket = bucket_for(kind)
    if path.startswith(f"{bucket}/"):
        path = path[len(bucket) + 1 :]
    if not path:
        raise APIError(VALIDATION_ERROR, "storage_path must name an object, not just a bucket.")
    return path


def object_url(kind: str, storage_path: str) -> str:
    """Public URL for an object. Becomes a signed URL if buckets are made private."""
    base = settings.supabase_url.rstrip("/")
    bucket = bucket_for(kind)
    return f"{base}/storage/v1/object/public/{bucket}/{normalise_path(kind, storage_path)}"


def validate_media(kind: str, media: dict[str, Any]) -> dict[str, Any]:
    """Normalise a media metadata row and enforce the configured upload limits."""
    row = dict(media)
    row["storage_path"] = normalise_path(kind, row.get("storage_path", ""))

    size = row.get("file_size_bytes")
    if size is not None and row.get("media_type") == "video":
        limit = settings.knowledge_video_max_bytes
        if limit and int(size) > limit:
            raise APIError(
                VALIDATION_ERROR,
                f"Video exceeds the {limit // (1024 * 1024)} MB upload limit.",
                {"file_size_bytes": size, "limit_bytes": limit},
            )
    return row


def fetch_image(kind: str, storage_path: str, mime_type: str | None = None):
    """Download one image for the AI layer. Returns None rather than raising.

    A missing or oversized image degrades the fingerprint to text-only, which is much
    better than failing the customer's request over an attachment.
    """
    try:
        url = object_url(kind, storage_path)
    except APIError:
        log.warning("Skipping media with an invalid storage path")
        return None

    try:
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        data = response.content
        if len(data) > MAX_IMAGE_BYTES:
            log.info("Skipping oversized image (%d bytes)", len(data))
            return None
        resolved = mime_type or response.headers.get("content-type") or "image/jpeg"
        return data, resolved.split(";")[0].strip()
    except Exception:
        log.warning("Could not fetch an image from storage; continuing without it")
        return None


def fetch_images(kind: str, media: list[dict[str, Any]], limit: int = 4):
    """Fetch up to ``limit`` images from a list of media metadata rows."""
    out = []
    for item in media:
        if item.get("media_type") != "image":
            continue
        fetched = fetch_image(kind, str(item.get("storage_path") or ""), item.get("mime_type"))
        if fetched is not None:
            out.append(fetched)
        if len(out) >= limit:
            break
    return out
