# S3 setup

This document walks through how the photo-storage bucket for SnapVault was
created, why each choice was made, and how the application connects to it
at runtime. Everything happens in `us-east-1`, the only region the AWS
Academy Learner Lab allows.

## Why S3 at all

The application stores two kinds of data: image files (the photos
themselves) and metadata (titles, descriptions, owners, timestamps). Image
files are large and binary, so putting them in a relational database is
both expensive and slow. S3 is the natural place for them — it gives
practically unlimited storage at a few cents per gigabyte per month, and
the application can hand each upload to S3 with one `boto3` call. Only the
metadata lives in RDS, where SQL queries are cheap.

## Creating the bucket

S3 bucket names are globally unique, so we picked one tied to the GitHub
identifier so we'd know it was ours: `snapvault-caan0020`. The CLI command
that created it from the Cloud9 terminal:

```bash
aws s3api create-bucket \
  --bucket snapvault-caan0020 \
  --region us-east-1
```

If you re-run this and the name is taken, suffix it (`-1`, `-eu`, …) and
remember to update the `S3_BUCKET` environment variable on Elastic
Beanstalk in [setup-eb.md](setup-eb.md) to match.

## Locking down public access

SnapVault never serves S3 objects as public URLs. When the app needs to
show a photo, the storage helper in `application/snapvault/storage.py`
asks S3 to generate a *presigned URL* — a one-hour signed link that proves
the request is allowed without exposing credentials. That means the
bucket itself doesn't need to be world-readable. In fact, leaving it
public would be a security mistake.

The bucket's "Block all public access" setting was turned on with:

```bash
aws s3api put-public-access-block \
  --bucket snapvault-caan0020 \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

All four flags need to be `true` — they cover four different ways an
object can become public (ACLs, public ACL evaluation, bucket policies,
and policy evaluation respectively). Setting just one isn't enough.

## Verifying everything works

After creating the bucket, three CLI calls confirm the bucket exists, is
private, and that the role we're running as can actually use it:

```bash
aws s3 ls                                                       # bucket appears here
aws s3api get-public-access-block --bucket snapvault-caan0020   # four `true` flags
```

The last and most reassuring test is a real round-trip — upload a tiny
file, download it, delete it:

```bash
echo "hello snapvault" > /tmp/hello.txt
aws s3 cp /tmp/hello.txt s3://snapvault-caan0020/test/hello.txt
aws s3 cp s3://snapvault-caan0020/test/hello.txt -
aws s3 rm  s3://snapvault-caan0020/test/hello.txt
```
