"""Object storage (S3 API).

Points at local MinIO in dev and DigitalOcean Spaces in prod — same code, only the
STORAGE_* config differs. Objects are served back to the browser through a gated Flask
route (see content.get_sketch), so credentials/endpoint are never exposed client-side.
"""
import uuid

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per file


class StorageError(RuntimeError):
    pass


def _client():
    cfg = current_app.config
    endpoint = cfg.get("STORAGE_ENDPOINT")
    if not endpoint:
        raise StorageError("object storage is not configured (STORAGE_ENDPOINT unset)")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=cfg.get("STORAGE_ACCESS_KEY"),
        aws_secret_access_key=cfg.get("STORAGE_SECRET_KEY"),
        region_name=cfg.get("STORAGE_REGION") or "us-east-1",
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _bucket() -> str:
    bucket = current_app.config.get("STORAGE_BUCKET")
    if not bucket:
        raise StorageError("object storage is not configured (STORAGE_BUCKET unset)")
    return bucket


def ensure_bucket() -> None:
    """Create the bucket if it doesn't exist (idempotent). Safe to call on startup."""
    client = _client()
    bucket = _bucket()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def extension_ok(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_fileobj(fileobj, filename: str, content_type: str, prefix: str = "sketches") -> str:
    """Upload a file-like object; return the storage key to persist in the DB."""
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else "bin"
    key = f"{prefix}/{uuid.uuid4().hex}.{ext}"
    client = _client()
    client.upload_fileobj(
        fileobj,
        _bucket(),
        key,
        ExtraArgs={"ContentType": content_type or "application/octet-stream"},
    )
    return key


def get_object(key: str):
    """Return (body_stream, content_type) for a stored object, or raise StorageError."""
    client = _client()
    try:
        obj = client.get_object(Bucket=_bucket(), Key=key)
    except ClientError as exc:
        raise StorageError(f"object not found: {key}") from exc
    return obj["Body"], obj.get("ContentType", "application/octet-stream")
