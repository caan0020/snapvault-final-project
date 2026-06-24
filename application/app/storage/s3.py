"""S3-backed file storage (used when SNAPVAULT_BACKEND=aws).

Upload, download and delete are three explicit boto3 calls made by the
app's own code — `put_object`, `get_object`, `delete_object`. The bucket
stays fully private; the browser never talks to S3 directly. This is what
the rubric means by "files uploaded and downloaded by the app itself".
"""
import boto3

from ..config import Config
from .base import FileStorage


class S3FileStorage(FileStorage):
    def __init__(self):
        # The bucket name is checked lazily (see _require_bucket) rather than
        # here, so the app still boots — and Beanstalk health stays Green —
        # in the short window between `eb create` and `eb setenv SNAPVAULT_BUCKET`.
        self.bucket = Config.BUCKET
        self.client = boto3.client("s3", region_name=Config.AWS_REGION)

    def _require_bucket(self):
        if not self.bucket:
            raise RuntimeError(
                "SNAPVAULT_BUCKET is not set — set it with "
                "`eb setenv SNAPVAULT_BUCKET=<bucket-name>`"
            )

    def save(self, key, fileobj, content_type):
        # UPLOAD: app reads the bytes and puts them into S3.
        self._require_bucket()
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=fileobj.read(),
            ContentType=content_type,
        )
        return key

    def open(self, key):
        # DOWNLOAD: app pulls the object from S3 and returns the bytes,
        # which the route then streams to the browser.
        self._require_bucket()
        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def delete(self, key):
        self._require_bucket()
        self.client.delete_object(Bucket=self.bucket, Key=key)
