"""Storage path validation and media metadata rules."""
from __future__ import annotations

import pytest

from backend.core.config import settings
from backend.core.errors import APIError
from backend.services.storage import storage
from backend.tests.conftest import auth

API = "/api/v1"


def test_a_bare_object_path_is_accepted():
    assert storage.normalise_path(storage.PROBLEM, "abc-123/photo.jpg") == "abc-123/photo.jpg"


def test_a_bucket_prefixed_path_is_normalised_to_the_object_path():
    prefixed = f"{settings.storage_problem_bucket}/abc-123/photo.jpg"
    assert storage.normalise_path(storage.PROBLEM, prefixed) == "abc-123/photo.jpg"


@pytest.mark.parametrize("path", [
    "../secrets/key.txt",
    "abc/../../other-bucket/file.jpg",
    "https://evil.example.com/x.jpg",
    "s3://bucket/x.jpg",
    "",
    "   ",
])
def test_paths_that_escape_the_bucket_are_refused(path):
    """A traversal or absolute URL would point a record outside the bucket it claims."""
    with pytest.raises(APIError):
        storage.normalise_path(storage.PROBLEM, path)


def test_a_leading_slash_is_stripped_rather_than_refused():
    """Clients send leading slashes; the result is still confined to the bucket."""
    assert storage.normalise_path(storage.PROBLEM, "/p1/photo.jpg") == "p1/photo.jpg"


def test_each_kind_resolves_to_its_configured_bucket():
    assert storage.bucket_for(storage.PROBLEM) == settings.storage_problem_bucket
    assert storage.bucket_for(storage.EXPERIENCE) == settings.storage_experience_bucket
    assert storage.bucket_for(storage.KNOWLEDGE) == settings.storage_knowledge_bucket
    assert storage.bucket_for(storage.CERTIFICATE) == settings.storage_certificate_bucket


def test_an_unknown_kind_is_refused():
    with pytest.raises(APIError):
        storage.bucket_for("nope")


def test_object_url_points_at_the_right_bucket(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://project.supabase.co")
    url = storage.object_url(storage.EXPERIENCE, "exp-1/after.jpg")
    assert url == (
        "https://project.supabase.co/storage/v1/object/public/"
        f"{settings.storage_experience_bucket}/exp-1/after.jpg"
    )


def test_oversized_video_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "knowledge_video_max_bytes", 1_000_000)
    with pytest.raises(APIError) as caught:
        storage.validate_media(storage.KNOWLEDGE, {
            "storage_path": "case-1/clip.mp4",
            "media_type": "video",
            "file_size_bytes": 5_000_000,
        })
    assert "limit" in caught.value.message.lower()


def test_a_video_within_the_limit_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "knowledge_video_max_bytes", 10_000_000)
    row = storage.validate_media(storage.KNOWLEDGE, {
        "storage_path": "case-1/clip.mp4",
        "media_type": "video",
        "file_size_bytes": 5_000_000,
    })
    assert row["storage_path"] == "case-1/clip.mp4"


def test_the_size_limit_does_not_apply_to_images(monkeypatch):
    monkeypatch.setattr(settings, "knowledge_video_max_bytes", 1_000)
    row = storage.validate_media(storage.PROBLEM, {
        "storage_path": "p-1/photo.jpg",
        "media_type": "image",
        "file_size_bytes": 500_000,
    })
    assert row["media_type"] == "image"


def test_a_failed_image_fetch_returns_none_rather_than_raising(monkeypatch):
    """A missing attachment must degrade the fingerprint, not fail the request."""
    def explode(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(storage.httpx, "get", explode)
    assert storage.fetch_image(storage.PROBLEM, "p-1/photo.jpg") is None


def test_fetch_images_skips_non_images(monkeypatch):
    monkeypatch.setattr(storage, "fetch_image", lambda kind, path, mime=None: (b"x", "image/jpeg"))
    media = [
        {"media_type": "document", "storage_path": "a.pdf"},
        {"media_type": "image", "storage_path": "b.jpg"},
    ]
    assert len(storage.fetch_images(storage.PROBLEM, media)) == 1


# ------------------------------------------------------------ through the API


def test_problem_media_with_a_traversal_path_is_rejected(client, world):
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "t", "description": "d"},
    ).json()["id"]

    response = client.post(
        f"{API}/problems/{problem_id}/media", headers=auth(world.customer),
        json={"storage_path": "../../other/file.jpg", "media_type": "image"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_problem_media_path_is_stored_without_the_bucket_prefix(client, world, store):
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "t", "description": "d"},
    ).json()["id"]

    response = client.post(
        f"{API}/problems/{problem_id}/media", headers=auth(world.customer),
        json={"storage_path": f"{settings.storage_problem_bucket}/p1/photo.jpg"},
    )
    assert response.status_code == 201
    assert response.json()["storage_path"] == "p1/photo.jpg"
