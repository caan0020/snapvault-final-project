# AWS Elastic Beanstalk setup

SnapVault runs on a **single-instance** Elastic Beanstalk environment on
the **Python 3.11 / Amazon Linux 2023** platform. Beanstalk provisions
the EC2 instance, runs **Gunicorn behind Nginx**, injects the environment
variables, and gives a public URL — all without writing any
infrastructure code by hand.

## What the platform expects

The Beanstalk Python platform looks for a WSGI callable named
`application`. Three files in `application/` satisfy the platform:

| File | Role |
|---|---|
| `application.py` | exposes `application = create_app()` (the WSGI object) |
| `Procfile` | `web: gunicorn application:application` — how to start the app |
| `.ebextensions/01_env.config` | sets env vars + `WSGIPath` at deploy time |

`.ebextensions/01_env.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    SNAPVAULT_BACKEND: aws
    SNAPVAULT_ALBUMS_TABLE: SnapVault-Albums
    SNAPVAULT_PHOTOS_TABLE: SnapVault-Photos
    AWS_REGION: us-east-1
    FLASK_DEBUG: "0"
  aws:elasticbeanstalk:container:python:
    WSGIPath: application:application
```

The one value **not** in here is `SNAPVAULT_BUCKET`, because the bucket
name is unique per deploy — it's set separately with `eb setenv`.

## Deploy with the EB CLI (from Cloud9)

```bash
cd application
eb init -p python-3.11 snapvault --region us-east-1

eb create snapvault-env \
  --single \
  --instance-types t3.micro \
  --service-role LabRole \
  --instance_profile LabInstanceProfile

eb setenv SNAPVAULT_BUCKET=<bucket-from-init_s3>
eb open
```

### The two flags that matter most

- **`--single`** — a single-instance environment with **no Application
  Load Balancer**. The ALB is the most expensive part of a default
  Beanstalk environment and the rubric doesn't need it.
- **`--service-role LabRole --instance_profile LabInstanceProfile`** —
  reuse the lab's existing roles. Learner Lab denies `iam:CreateRole`,
  so the wizard's default "create a new role" path fails a few minutes
  into `eb create`. Passing the existing roles is what makes it succeed.
  `LabInstanceProfile` is also what gives the running app permission to
  reach DynamoDB and S3, so **no access keys** are needed anywhere.

## Why Elastic Beanstalk (not plain EC2)

A bare EC2 instance would mean installing and configuring Nginx,
Gunicorn, systemd and the security group by hand. Beanstalk wraps all of
that in a managed environment and adds health monitoring, log access and
one-command redeploys (`eb deploy`). For a student project it's the right
fast-feedback choice; the same instinct in production points at managed
compute like ECS or App Runner.

## Everyday commands

```bash
eb status      # health + the public CNAME
eb printenv    # the environment variables currently set
eb logs        # tail the platform + app logs (web.stdout.log has tracebacks)
eb deploy      # ship the current code (honours .ebignore)
eb terminate snapvault-env   # delete the environment when finished
```

## Screenshots to capture

- `03-eb-environment.png` — the environment dashboard, Health **Green**,
  with the URL.
- `04-eb-config-env.png` — Configuration → environment properties.
- `08-ec2-instance.png` — the EC2 instance Beanstalk launched.
