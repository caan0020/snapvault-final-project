# Infrastructure

Artifacts used to provision and deploy SnapVault on **AWS Academy Learner
Lab — Foundational Services** (region `us-east-1`).

## Files in this folder

| File | Purpose |
|---|---|
| `setup-s3.md` | Step-by-step guide for creating the S3 bucket (`snapvault-caan0020`) and configuring access through `LabRole`, with the AWS CLI commands used. |
| `setup-rds.md` | Step-by-step guide for creating the RDS PostgreSQL instance (`snapvault-db`, `db.t3.micro`, private, single-AZ) and capturing the connection details for Elastic Beanstalk. |
| `setup-eb.md` | Step-by-step guide for deploying the Flask app to Elastic Beanstalk (single-instance Python 3.11 environment), setting env vars, and wiring the RDS security group. |