# Infrastructure

Everything needed to provision and deploy SnapVault on **AWS Academy
Learner Lab** (region `us-east-1`), driven from **Cloud9**.

## Start here

➡️ **[`CLOUD9_DEPLOY.md`](CLOUD9_DEPLOY.md)** — the full, top-to-bottom
deploy: create the resources, then ship the app to Elastic Beanstalk.

## Resource-creation scripts (idempotent)

| Script | Creates |
|---|---|
| [`init_dynamodb.py`](init_dynamodb.py) | the two DynamoDB tables `SnapVault-Albums` and `SnapVault-Photos` |
| [`init_s3.py`](init_s3.py) | one **private** S3 bucket (all public access blocked) |

```bash
python3 infrastructure/init_dynamodb.py
python3 infrastructure/init_s3.py
```

## Per-service deep dives

| File | Service |
|---|---|
| [`setup-dynamodb.md`](setup-dynamodb.md) | DynamoDB — tables, keys, the four boto3 calls, permissions |
| [`setup-s3.md`](setup-s3.md) | S3 — private bucket, app-side upload/download, permissions |
| [`setup-eb.md`](setup-eb.md) | Elastic Beanstalk — platform conventions, `eb` CLI, LabRole |

## Screenshots

`screenshots/` holds the AWS console captures referenced by the top-level
[`../README.md`](../README.md) report. The list of shots to take is at the
end of [`CLOUD9_DEPLOY.md`](CLOUD9_DEPLOY.md#9-capturing-screenshots-for-the-report).
