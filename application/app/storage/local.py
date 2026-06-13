"""Local filesystem storage (used when SNAPVAULT_BACKEND=local).

Mirrors the S3 backend's three operations against .data/uploads/ so the
app behaves identically on a laptop with no AWS account. Object keys may
contain "/" (e.g. albums/<id>/cover.jpg); they map to subdirectories.
"""
import os

from ..config import UPLOADS_DIR
from .base import FileStorage


class LocalFileStorage(FileStorage):
    def _path(self, key):
        return UPLOADS_DIR / key

    def save(self, key, fileobj, content_type):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(fileobj.read())
        return key

    def open(self, key):
        with open(self._path(key), "rb") as f:
            return f.read()

    def delete(self, key):
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass
