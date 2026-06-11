"""Local JSON-file repository (used when SNAPVAULT_BACKEND=local).

Lets the whole app run on a laptop with no AWS account. Each table is one
JSON file under .data/ keyed by item id. Writes go through a temp file +
atomic replace so a crash never leaves a half-written store.
"""
import json
import os
import tempfile

from ..config import DATA_DIR
from .base import Repo


class LocalRepo(Repo):
    def __init__(self, filename, model_cls):
        self.model = model_cls
        self.path = DATA_DIR / filename

    def _read(self):
        if not self.path.exists():
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def list(self):
        data = self._read()
        items = [self.model.from_dict(d) for d in data.values()]
        items.sort(key=lambda o: o.created_at, reverse=True)
        return items

    def get(self, id):
        row = self._read().get(id)
        return self.model.from_dict(row) if row else None

    def save(self, obj):
        data = self._read()
        data[obj.id] = obj.to_dict()
        self._write(data)
        return obj

    def delete(self, id):
        data = self._read()
        if id in data:
            del data[id]
            self._write(data)

    def find_by(self, field, value):
        return [o for o in self.list() if getattr(o, field, None) == value]
