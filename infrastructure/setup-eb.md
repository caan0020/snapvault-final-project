# Elastic Beanstalk deployment (console)

This document walks through how SnapVault was deployed to AWS Elastic
Beanstalk using the AWS Management Console — no command-line tools
beyond `zip` and basic shell commands. It picks up where
[setup-s3.md](setup-s3.md) and [setup-rds.md](setup-rds.md) left off:
the S3 bucket already exists, and the RDS instance is **Available**.

## Why Elastic Beanstalk

The application could have been deployed to a plain EC2 instance, but
that would mean configuring Nginx, Gunicorn, systemd, security groups,
and TLS termination by hand. Elastic Beanstalk wraps all of that in a
managed environment: it provisions the EC2 instance, runs Gunicorn
behind Nginx with sensible defaults, applies environment variables,
and gives a public CNAME to share. For a student project this is the
right fast-feedback choice; in a production system we'd reach for a
similar managed layer (ECS, App Runner, or Kubernetes) for the same
reason.

The Beanstalk Python platform's only convention we have to honor is
that the WSGI module exposes an object called `application` at the
deployment root. The file `application/application.py` does exactly
that.

## Why the console (not the eb CLI)

The standard tool for Beanstalk deployments is `awsebcli`. We tried it
first, but the AWS Academy Learner Lab terminal runs Python 3.7, which
modern `awsebcli` no longer supports — the install fails with a
`setuptools` / `typing.Protocol` import error. Pinning to
`awsebcli==3.20.10` would have worked, but for a project with only two
or three planned deploys the console is faster and easier, and every
step is naturally screenshottable for the report. So we chose the
console path deliberately.

## Step 1 — package the application as a zip

Beanstalk deploys a zip of the application root. From the Cloud9
terminal:

```bash
cd ~/sdpcba-2026-finalproject-caan0020/application
zip -r ../snapvault-v1.zip . \
  -x "*.venv*" "*__pycache__*" "*.db" "uploads/*" ".elasticbeanstalk/*"
```

The `-x` flags exclude things Beanstalk shouldn't ship: the local
virtualenv (we want Beanstalk to install from `requirements.txt` on its
own), Python bytecode caches, the SQLite dev database, the local
`uploads/` directory (we use S3 in production), and any CLI state.

The resulting `snapvault-v1.zip` should contain `application.py`,
`config.py`, `requirements.txt`, and the `snapvault/` package at the
top level — not nested inside an extra folder. Verify with:

```bash
unzip -l ../snapvault-v1.zip | head -20
```

Download `snapvault-v1.zip` to your local machine through the Cloud9
file explorer (or skip this and upload it directly from inside the
Cloud9 / AWS Console — the Beanstalk upload widget accepts a file
from anywhere your browser can read).

## Step 2 — create the Beanstalk application

In the AWS Console, search for **Elastic Beanstalk** and open it.
Click **Create application**, then fill in:

| Field | Value |
|---|---|
| Application name | `snapvault` |
| Application tags | leave blank |
| Platform | **Python** |
| Platform branch | **Python 3.11 running on 64bit Amazon Linux 2023** |
| Platform version | leave at the recommended default |
| Application code | **Upload your code** → choose `snapvault-v1.zip` |
| Version label | `v1` |
| Presets | **Single instance (Free Tier eligible)** |

Click **Next**.

## Step 3 — configure service access (the IAM trap)

This is the most important page. Beanstalk's defaults are *create new
roles*, but Learner Lab forbids new IAM role creation
(`iam:CreateRole` is denied by `Pvoclabs2`). If you accept the defaults
here, the create will fail several minutes in with a confusing IAM
error. Change both fields:

| Field | Value |
|---|---|
| Service role | **Use an existing service role** → **`LabRole`** |
| EC2 key pair | leave blank (no SSH) |
| EC2 instance profile | **`LabInstanceProfile`** |

`LabRole` is the role Elastic Beanstalk itself assumes to provision
the environment. `LabInstanceProfile` is the role attached to the
EC2 instance that actually runs the app. Both are pre-created in
Learner Lab; we can use them but not change them.

Click **Next**.

## Step 4 — set up networking

| Field | Value |
|---|---|
| VPC | **Default VPC** |
| Public IP address | **Activated** (so the grader can reach the app from the public internet) |
| Instance subnets | check **all subnets in the default VPC** |
| Database subnets | leave unchecked (we already created RDS outside this flow) |

Click **Next**.

## Step 5 — configure the instance

| Field | Value |
|---|---|
| Instance type | **`t3.micro`** |
| EC2 security groups | leave at the auto-created one (Beanstalk makes one named `awseb-…`) |
| Root volume type | General purpose SSD (gp2) |
| Root volume size | 8 GiB |
| All other fields | leave at the default |

Click **Next** through the remaining pages (Capacity, Updates,
Monitoring, etc.) — the single-instance preset has already locked in
sensible defaults. The only page we'll revisit later is **Environment
properties**, but it's cleaner to set those *after* the first deploy.

On the final **Review** page, click **Submit**. Provisioning takes
5–10 minutes. The page will live-update as Beanstalk creates the EC2
instance, security groups, and CloudWatch alarms.

The first deploy will probably show health **Severe** or **Degraded**
once it finishes — that's expected because we haven't set the
environment variables yet. The app starts, can't find `DATABASE_URL`,
and crashes. Fix in the next step.

## Step 6 — set the environment variables

In the Beanstalk console:

1. Click into the `snapvault-env` environment.
2. **Configuration → Updates, monitoring, and logging → Edit**.
3. Scroll to **Environment properties**.
4. Add each variable below as a separate row:

   | Name | Value |
   |---|---|
   | `STORAGE_BACKEND` | `s3` |
   | `S3_BUCKET` | `snapvault-caan0020` |
   | `AWS_REGION` | `us-east-1` |
   | `DATABASE_URL` | `postgresql://postgres:YOUR_PASSWORD@snapvault-db.cgmv1jdtqqha.us-east-1.rds.amazonaws.com:5432/snapvault` |
   | `SECRET_KEY` | any random hex string at least 32 characters long |

   Replace `YOUR_PASSWORD` and the host with your own values.

5. Click **Apply**. Beanstalk redeploys the app with the new vars
   baked in. Wait 1–2 minutes.

Generate a `SECRET_KEY` locally with:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

The point of generating it fresh per environment is so the dev default
in `config.py` never makes it to production. The variable lives only
in Beanstalk's encrypted property store; the literal value does not
appear in this repository.

## Step 7 — open the RDS firewall to Beanstalk

Beanstalk launched its own security group for the EC2 instance — let's
call it the *EB SG*. The RDS instance has its own security group
(`snapvault-db-sg`) which currently allows nothing inbound. We need a
rule that lets the EB SG talk to RDS on Postgres' port.

In the console:

1. **EC2 → Instances** → find the instance Beanstalk launched (its
   name starts with `snapvault-env-`). In the side panel, note the
   **Security groups** assigned to it. The relevant one is named
   something like `awseb-e-XXXXXXXX-stack-AWSEBSecurityGroup-YYYY`.
   Copy its **group ID** (it looks like `sg-0123abcd…`).
2. **EC2 → Security Groups → `snapvault-db-sg` → Inbound rules →
   Edit inbound rules → Add rule**:
   - Type: **PostgreSQL** (port 5432 fills in automatically)
   - Source: **Custom**, then paste the EB SG ID
   - Description: `Allow Flask app on EB to reach Postgres`
3. **Save rules**.

Within ten seconds the running Flask app on EB can open connections
to RDS. The reason we point at the EB security group ID rather than a
specific IP is that if Beanstalk ever scales out to more instances,
every new EC2 host automatically joins the same EB SG and inherits
this rule. There's nothing to update.

## Step 8 — open the app and verify

In the Beanstalk console, the environment page shows a URL at the top:
something like `snapvault-env.eba-abcdef.us-east-1.elasticbeanstalk.com`.
Click it. The SnapVault home page should load.

Smoke test the full stack:

1. Click **Register**, create an account.
2. Click **Albums → Create album**.
3. Upload a photo.
4. Confirm in another tab that:
   - The image file appears under `s3://snapvault-caan0020/` (in the S3
     console).
   - A row appears in the `photos` table of the RDS instance (we can
     check this via the RDS console's *Query editor* or with `psql`
     from inside Cloud9 — since Cloud9 is in the default VPC it can
     reach the private RDS endpoint).

That single end-to-end test simultaneously proves the app is running
on Elastic Beanstalk, talking to RDS, and writing to S3 — the three
rubric points worth eight total.

## Troubleshooting

Beanstalk has its own log viewer: **Environment → Logs → Request logs
→ Last 100 lines**. The most useful log file is `web.stdout.log`,
which contains the Python tracebacks.

Common first-deploy errors:

- **`OperationalError: could not connect to server`** — the security
  group rule from Step 7 is missing or points at the wrong SG. Open
  the EB instance's security groups in the EC2 console, copy the right
  SG ID, and add the inbound rule again.
- **502 Bad Gateway** — Flask never started. Pull the logs and look
  for a Python traceback near the top of `web.stdout.log`. Most often
  a typo in an env var or a missing dependency in `requirements.txt`.
- **`KeyError: 'DATABASE_URL'`** — typo in the env var name in
  Step 6. Fix it and re-apply; the redeploy takes about two minutes.

## Deploying a new code version later

When the application code changes:

1. Re-create the zip in Cloud9 (same `zip` command as Step 1, bump the
   version: `snapvault-v2.zip`).
2. In Beanstalk: **Environments → snapvault-env → Upload and deploy**
   → choose the new zip → enter a version label (`v2`) → **Deploy**.
3. Beanstalk shifts traffic to the new version with no downtime in
   ~1 minute.

This is the manual equivalent of `eb deploy`. For a project with two
or three deploys total, it's fine.

## Cost

The Beanstalk-launched `t3.micro` EC2 instance is about $0.01 per
hour. The single-instance preset skips the load balancer entirely,
which would have been the bigger cost. The RDS instance remains the
biggest budget drain.

When you're done for the day:

- **RDS → Actions → Stop temporarily** (RDS allows up to 7 days
  stopped before it auto-starts).
- **Elastic Beanstalk → Environments → snapvault-env → Actions →
  Terminate environment** (this fully deletes the environment; the
  application object is kept and a fresh environment can be created
  from the same zip later).
