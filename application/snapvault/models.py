from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    albums = db.relationship(
        "Album",
        back_populates="owner",
        cascade="all, delete-orphan",
        order_by="Album.created_at.desc()",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Album(db.Model):
    __tablename__ = "albums"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    owner = db.relationship("User", back_populates="albums")
    photos = db.relationship(
        "Photo",
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="Photo.created_at.desc()",
    )


class Photo(db.Model):
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    storage_key = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(64), default="application/octet-stream", nullable=False)
    album_id = db.Column(
        db.Integer,
        db.ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    album = db.relationship("Album", back_populates="photos")
