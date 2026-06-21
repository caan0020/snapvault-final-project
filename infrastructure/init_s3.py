"""Create the private S3 bucket SnapVault stores photo files in.

Run from the Cloud9 terminal:

    python3 infrastructure/init_s3.py                  # auto-generated name
    python3 infrastructure/init_s3.py my-bucket-name   # pick your own name

The bucket gets *all* public access blocked: the photos are only ever
read back by the app itself (S3 get_object) and streamed to the browser,
so the bucket never needs to be public. The script prints the final
bucket name — give it to Beanstalk with:

    eb setenv SNAPVAULT_BUCKET=<that-name>
"""
import os
import secrets
import sys

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "snapvault-" + secrets.token_hex(6)
    s3 = boto3.client("s3", region_name=REGION)

    # 1. create the bucket (us-east-1 must NOT send a LocationConstraint)
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=name)
        else:
            s3.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        print("- created bucket: %s" % name)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print("- bucket already exists: %s" % name)
        else:
            raise

    # 2. block every form of public access
    s3.put_public_access_block(
        Bucket=name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    print("- public access fully blocked")

    print("\nS3 is ready. Next:\n    eb setenv SNAPVAULT_BUCKET=%s" % name)


if __name__ == "__main__":
    main()
