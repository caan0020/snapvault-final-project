# Infrastructure

Artifacts used to provision and deploy SnapVault on **AWS Academy Learner
Lab — Foundational Services** (region `us-east-1`).

## Files in this folder

| File | Purpose |
|---|---|
| `s3-bucket-policy.json` | Least-privilege IAM policy granting `PutObject`, `GetObject`, `DeleteObject` on the SnapVault S3 bucket. Kept as a reference even though `LabRole`'s built-in permissions covered S3 in our lab variant. |
| `setup-s3.md` | Step-by-step guide for creating the S3 bucket (`snapvault-caan0020`) and configuring access through `LabRole`, with the AWS CLI commands used. |
| `setup-rds.md` | Step-by-step guide for creating the RDS PostgreSQL instance (`snapvault-db`, `db.t3.micro`, private, single-AZ) and capturing the connection details for Elastic Beanstalk. |

Future additions planned:

- `eb-deployment.md` — Elastic Beanstalk environment creation, env var setup,
  and `eb deploy` workflow.
- `screenshots/` — AWS console screenshots referenced from the final report.
