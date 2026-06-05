"""Thin storage layer.

Two backends share the same three operations so the rest of the app
does not care where bytes live: `save`, `get_url`, `delete`.

- LocalStorage  -> ./uploads, served by Flask's static handler. Used in dev.
- S3Storage     -> boto3, used in production on Elastic Beanstalk.

The rubric requires file uploads to be performed directly by app code
(not a higher-level library), so S3Storage uses raw boto3 calls
(`put_object`, `generate_presigned_url`, `delete_object`).
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

import boto3
from flask import current_app, url_for


def _new_key(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{suffix}"


class LocalStorage:
    """Saves files on disk under config.LOCAL_UPLOAD_DIR."""

    def save(self, stream: BinaryIO, original_filename: str, content_type: str) -> str:
        key = _new_key(original_filename)
        target = current_app.config["LOCAL_UPLOAD_DIR"] / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(stream.read())
        return key

    def get_url(self, key: str) -> str:
        return url_for("main.serve_upload", key=key)

    def delete(self, key: str) -> None:
        target = current_app.config["LOCAL_UPLOAD_DIR"] / key
        target.unlink(missing_ok=True)


class S3Storage:
    """Uploads/downloads via raw boto3 calls."""

    def __init__(self) -> None:
        self._client = boto3.client("s3", region_name=current_app.config["AWS_REGION"])
        self._bucket = current_app.config["S3_BUCKET"]
        if not self._bucket:
            raise RuntimeError("S3_BUCKET env var is required for S3Storage")

    def save(self, stream: BinaryIO, original_filename: str, content_type: str) -> str:
        key = _new_key(original_filename)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=stream,
            ContentType=content_type,
        )
        return key

    def get_url(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=current_app.config["PRESIGNED_URL_TTL"],
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


def get_storage():
    """Return the storage backend configured for the current app."""
    backend = current_app.config["STORAGE_BACKEND"].lower()
    if backend == "s3":
        return S3Storage()
    return LocalStorage()
