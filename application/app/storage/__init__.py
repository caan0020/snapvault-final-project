"""Storage factory — picks S3 in the cloud, local filesystem in dev."""
from ..config import Config
from .local import LocalFileStorage
from .s3 import S3FileStorage


def build_storage():
    if Config.BACKEND == "aws":
        return S3FileStorage()
    return LocalFileStorage()
