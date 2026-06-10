"""Domain models.

Plain dataclasses with `to_dict` / `from_dict` so they round-trip cleanly
through either backend. Every attribute is stored as a **string** — that
keeps DynamoDB marshalling trivial (no Decimal juggling) and the local
JSON file readable.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _now():
    return datetime.now(timezone.utc).isoformat()


def normalize_tags(raw):
    """Turn free 'Nature, beach , nature' text into a clean 'nature,beach'.

    Lower-cases, trims, drops blanks and de-duplicates while keeping order.
    """
    seen = []
    for part in (raw or "").replace(";", ",").split(","):
        tag = part.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return ",".join(seen)


@dataclass
class Album:
    id: str
    name: str
    created_at: str
    share_token: str  # unguessable token used for the public /share/<token> view

    @classmethod
    def new(cls, name):
        return cls(
            id="alb_" + uuid4().hex[:12],
            name=name,
            created_at=_now(),
            share_token="shr_" + uuid4().hex[:16],
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "share_token": self.share_token,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            created_at=d.get("created_at", ""),
            share_token=d.get("share_token", ""),
        )


@dataclass
class Photo:
    id: str
    album_id: str
    title: str
    description: str
    tags: str            # comma-separated, normalized
    favorite: str        # "0" or "1"
    file_key: str        # object key in S3 / local storage
    file_name: str       # original upload filename
    content_type: str
    size: str            # bytes, as a string
    created_at: str

    @classmethod
    def new(cls, album_id, title, description="", tags="",
            file_key="", file_name="", content_type="", size="0"):
        return cls(
            id="pho_" + uuid4().hex[:12],
            album_id=album_id,
            title=title,
            description=description,
            tags=normalize_tags(tags),
            favorite="0",
            file_key=file_key,
            file_name=file_name,
            content_type=content_type,
            size=str(size),
            created_at=_now(),
        )

    @property
    def is_favorite(self):
        return self.favorite == "1"

    def tag_list(self):
        return [t for t in self.tags.split(",") if t]

    def to_dict(self):
        return {
            "id": self.id,
            "album_id": self.album_id,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "favorite": self.favorite,
            "file_key": self.file_key,
            "file_name": self.file_name,
            "content_type": self.content_type,
            "size": self.size,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d.get("id", ""),
            album_id=d.get("album_id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            tags=d.get("tags", ""),
            favorite=d.get("favorite", "0"),
            file_key=d.get("file_key", ""),
            file_name=d.get("file_name", ""),
            content_type=d.get("content_type", ""),
            size=d.get("size", "0"),
            created_at=d.get("created_at", ""),
        )
