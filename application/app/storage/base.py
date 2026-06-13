"""File-storage interface shared by the S3 and local backends.

Three operations are enough for the whole app: store bytes, read bytes
back, and delete. The route layer uses `open()` to stream a photo back to
the browser, which is how the *app itself* performs the download (no
public bucket, no presigned URL handed to the client).
"""
from abc import ABC, abstractmethod


class FileStorage(ABC):
    @abstractmethod
    def save(self, key, fileobj, content_type):
        """Store bytes from a file-like object under `key`; returns the key."""

    @abstractmethod
    def open(self, key):
        """Read and return the raw bytes stored under `key`."""

    @abstractmethod
    def delete(self, key):
        """Delete the object at `key` (no error if missing)."""
