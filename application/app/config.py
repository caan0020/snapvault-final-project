"""Application configuration.

Everything is driven by environment variables so the *same* code runs
locally (a JSON file + a local uploads folder) and in the cloud
(DynamoDB + S3) — moving to AWS is a config change, not a code change.

`SNAPVAULT_BACKEND` is the single switch:
  - "local" (default) -> JSON file repo + local filesystem storage
  - "aws"             -> DynamoDB repo + S3 storage
"""
import os
from pathlib import Path


# Local-dev data lives next to the package, never committed (see .gitignore).
DATA_DIR = Path(__file__).resolve().parent.parent / ".data"
UPLOADS_DIR = DATA_DIR / "uploads"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env():
    """Tiny .env reader so local dev picks up settings without extra libs.

    Values already in the real environment win (e.g. set via `eb setenv`
    in production), so this never overrides cloud configuration.
    """
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


class Config:
    # backend switch: "local" or "aws"
    BACKEND = os.environ.get("SNAPVAULT_BACKEND", "local")

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

    # DynamoDB tables (created by infrastructure/init_dynamodb.py)
    ALBUMS_TABLE = os.environ.get("SNAPVAULT_ALBUMS_TABLE", "SnapVault-Albums")
    PHOTOS_TABLE = os.environ.get("SNAPVAULT_PHOTOS_TABLE", "SnapVault-Photos")

    # S3 bucket (created by infrastructure/init_s3.py, set via `eb setenv`)
    BUCKET = os.environ.get("SNAPVAULT_BUCKET", "")

    SECRET_KEY = os.environ.get("SNAPVAULT_SECRET", "dev-secret-change-me")

    MAX_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MB per file
    ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


# Make sure the local data folders exist when running in local mode.
if Config.BACKEND == "local":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
