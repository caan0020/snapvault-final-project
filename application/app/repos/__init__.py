"""Repository factory.

`build_repo()` returns a `Store` that bundles one repo per table. The
factory is the only place that knows whether we are on DynamoDB or the
local JSON files — everything else just calls `repo.albums` / `repo.photos`.
"""
from ..config import Config
from ..models import Album, Photo
from .dynamo import DynamoRepo
from .local import LocalRepo


class Store:
    def __init__(self, albums, photos):
        self.albums = albums
        self.photos = photos


def build_repo():
    if Config.BACKEND == "aws":
        return Store(
            albums=DynamoRepo(Config.ALBUMS_TABLE, Album),
            photos=DynamoRepo(Config.PHOTOS_TABLE, Photo),
        )
    return Store(
        albums=LocalRepo("albums.json", Album),
        photos=LocalRepo("photos.json", Photo),
    )
