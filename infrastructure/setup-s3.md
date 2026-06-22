# Amazon S3 setup

The photo **files** (the image bytes) live in a single **private** S3
bucket. The metadata about them lives in DynamoDB; S3 only ever holds
the binary objects.

## The bucket

| Property | Value |
|---|---|
| Name | `snapvault-<random>` (globally unique; printed by `init_s3.py`) |
| Region | `us-east-1` |
| Public access | **fully blocked** (all four block settings on) |
| Object keys | `albums/<album-id>/<photo-id>-<filename>` |

## Why the bucket stays private

A photo gallery's instinct is to make the bucket public so `<img>` tags
can point straight at it. We deliberately **don't**. Instead the app
reads each object itself and streams the bytes back through a Flask
route (`/photos/<id>/raw`). Benefits:

- the bucket needs no public policy and passes the "Block all public
  access" check;
- it directly satisfies the rubric line *"files uploaded **and
  downloaded** by the app code"* — both directions are explicit boto3
  calls in our own code, not a public/presigned URL handed to the
  browser.

## How the app talks to it

All file I/O goes through `app/storage/s3.py`:

| Operation | boto3 call | Used by |
|---|---|---|
| **upload** | `client.put_object(Bucket, Key, Body, ContentType)` | upload a photo |
| **download** | `client.get_object(Bucket, Key)` → `["Body"].read()` | show / download a photo |
| delete | `client.delete_object(Bucket, Key)` | delete a photo / album |

## Creating the bucket

```bash
python3 infrastructure/init_s3.py            # auto-named
python3 infrastructure/init_s3.py my-name    # or your own name
```

The script creates the bucket and then calls `put_public_access_block`
with all four flags `True`. Equivalent AWS CLI:

```bash
aws s3 mb s3://snapvault-caan0020 --region us-east-1
aws s3api put-public-access-block --bucket snapvault-caan0020 \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

After creating it, hand the name to Beanstalk:

```bash
eb setenv SNAPVAULT_BUCKET=<bucket-name>
```

A quick CLI round-trip proves the role can use the bucket:

```bash
echo "hello" > /tmp/h.txt
aws s3 cp /tmp/h.txt s3://<bucket>/test/h.txt   # upload
aws s3 cp s3://<bucket>/test/h.txt -            # download
aws s3 rm s3://<bucket>/test/h.txt              # delete
```

## Permissions

The EB instance uses **`LabInstanceProfile`** (S3 read/write is included
in Learner Lab). No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
anywhere in the repo.

## Screenshot to capture

- `07-s3-bucket.png` — the bucket's objects list with *"Block all public
  access: On"* visible.
