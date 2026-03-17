"""Cloudflare R2 storage integration.

Uses the S3-compatible API via boto3. All operations are workspace-scoped:
object keys are prefixed with the workspace_id so isolation is enforced at
the storage layer as well as the application layer.
"""
from __future__ import annotations

import hashlib
from typing import Optional


_UPLOAD_TTL_SECONDS = 3600  # presigned upload URL valid for 1 hour
_DOWNLOAD_TTL_SECONDS = 900  # presigned download URL valid for 15 minutes


def _r2_client(account_id: str, access_key_id: str, secret_access_key: str):  # type: ignore[return]
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("boto3 is required for R2 storage. Install it with: pip install boto3") from exc

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def r2_is_configured(account_id: str, access_key_id: str, secret_access_key: str, bucket_name: str) -> bool:
    return bool(account_id and access_key_id and secret_access_key and bucket_name)


def build_storage_key(workspace_id: str, asset_id: str, filename: str) -> str:
    """Construct a deterministic, workspace-scoped object key."""
    safe_name = filename.replace("/", "_").replace("..", "_")
    return f"workspaces/{workspace_id}/assets/{asset_id}/{safe_name}"


def generate_upload_url(
    *,
    account_id: str,
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    storage_key: str,
    mime_type: str,
    expires_in: int = _UPLOAD_TTL_SECONDS,
) -> str:
    """Return a presigned PUT URL for a direct client-to-R2 upload."""
    client = _r2_client(account_id, access_key_id, secret_access_key)
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket_name, "Key": storage_key, "ContentType": mime_type},
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )


def generate_download_url(
    *,
    account_id: str,
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    storage_key: str,
    expires_in: int = _DOWNLOAD_TTL_SECONDS,
) -> str:
    """Return a presigned GET URL for a time-limited download."""
    client = _r2_client(account_id, access_key_id, secret_access_key)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": storage_key},
        ExpiresIn=expires_in,
    )


def delete_object(
    *,
    account_id: str,
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    storage_key: str,
) -> None:
    client = _r2_client(account_id, access_key_id, secret_access_key)
    client.delete_object(Bucket=bucket_name, Key=storage_key)


def public_url(base_url: str, storage_key: str) -> Optional[str]:
    """Construct a public URL if the bucket has a custom domain / public access configured."""
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/{storage_key}"
