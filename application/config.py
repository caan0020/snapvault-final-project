import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'snapvault.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
    LOCAL_UPLOAD_DIR = BASE_DIR / "uploads"

    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    PRESIGNED_URL_TTL = int(os.environ.get("PRESIGNED_URL_TTL", "3600"))

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
