# Elastic Beanstalk deployment

This document walks through how SnapVault was deployed to AWS Elastic
Beanstalk — the choices that were made, the commands that were run, and
the gotchas to watch for. It picks up where [setup-s3.md](setup-s3.md)
and [setup-rds.md](setup-rds.md) left off: the S3 bucket already exists,
and the RDS instance is **Available** with its endpoint saved.

## Why Elastic Beanstalk

The application could have been deployed to a plain EC2 instance, but
that would have meant configuring Nginx, Gunicorn, systemd, security
groups, and TLS termination by hand. Elastic Beanstalk wraps all of that
in a managed environment: it provisions the EC2 instance, runs Gunicorn
behind Nginx with sensible defaults, applies our environment variables,
and gives us a public CNAME to share. Deploying a new version is a
single `eb deploy`. For a student project this is the right
fast-feedback choice; in a production system we'd reach for a similar
managed layer (ECS, App Runner, or Kubernetes) for the same reason.

The Beanstalk Python platform's only convention we have to honor is
that the WSGI module exposes an object called `application` at the
deployment root. Our `application/application.py` does exactly that.

## Installing the EB CLI

The Beanstalk CLI runs inside the Cloud9 terminal, which already has
the right credentials (it inherits `LabRole` automatically). Install it
with pip:

```bash
python3 -m pip install --user --upgrade awsebcli
eb --version
```

If `eb` isn't found after install, the `~/.local/bin` directory isn't
on the PATH yet — fix that once:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
eb --version
```

## Initializing the application

Beanstalk treats each *application* as a container for one or more
*environments* (think dev/staging/prod). We initialize from inside the
`application/` folder so that becomes the deployment root:

```bash
cd ~/environment/sdpcba-2026-finalproject-caan0020/application
eb init
```

The interactive prompts and the answers we gave:

| Prompt | Answer | Reason |
|---|---|---|
| Default region | `us-east-1` | the only region Learner Lab allows |
| Application | Create new | first time setting up |
| Application name | `snapvault` | matches the project name |
| Platform | Python | Flask is a Python app |
| Platform branch | Python 3.11 on Amazon Linux 2023 | latest LTS-style Python branch Beanstalk supports |
| Continue with CodeCommit? | No | we use GitHub |
| Set up SSH? | No | `LabRole` already grants enough access; SSH key management is one less thing to worry about |

This writes `application/.elasticbeanstalk/config.yml`. That directory
is already in `.gitignore` — nothing to commit.

## Creating the environment

```bash
eb create snapvault-env \
  --instance-type t3.micro \
  --single \
  --instance-profile LabInstanceProfile
```

Three flags matter:

- `--single` creates a *single-instance environment* — one EC2 host,
  no load balancer. Production Beanstalk environments come with an
  Application Load Balancer by default, which is great for high
  availability but adds about $20 a month. For a student demo with
  one user (the grader) it's pure waste.
- `--instance-type t3.micro` is the cheapest burstable EC2 class the
  lab consistently allows.
- `--instance-profile LabInstanceProfile` reuses the lab's pre-existing
  instance profile. Learner Lab forbids creating new instance profiles
  (`iam:CreateInstanceProfile` is denied), and the lab's own profile
  already grants S3 access plus the standard Beanstalk + CloudWatch
  permissions. This is the single most important flag — without it,
  `eb create` tries to create a new profile and fails with an IAM deny
  similar to the RDS gp3 issue.

Provisioning takes 5–10 minutes. The first deploy will start the Flask
app and crash immediately, because we haven't set the env vars yet —
`DATABASE_URL` is missing, so SQLAlchemy throws on startup. That's
expected and we fix it in the next step.

## Setting env vars and triggering a redeploy

Build the `DATABASE_URL` string from your RDS endpoint and master
password, then set everything in one command:

```bash
eb setenv \
  STORAGE_BACKEND=s3 \
  S3_BUCKET=snapvault-caan0020 \
  AWS_REGION=us-east-1 \
  DATABASE_URL='postgresql://postgres:YOUR_PASSWORD@snapvault-db.cgmv1jdtqqha.us-east-1.rds.amazonaws.com:5432/snapvault' \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

A few notes:

- `eb setenv` triggers an automatic redeploy with the new vars baked
  in. No separate `eb deploy` is needed.
- `STORAGE_BACKEND=s3` is what flips the app from the local `uploads/`
  folder to real S3 — the storage layer in
  `application/snapvault/storage.py` reads this env var at request time.
- The `SECRET_KEY` is generated inline so the dev default never makes
  it into production. Every deploy gets a fresh, random 64-char value.
- The literal `DATABASE_URL` with password never appears in this
  repository. It lives only in Beanstalk's encrypted environment
  variable store, which is visible only to the EC2 instances the
  environment launches and to authorized AWS console users.

## Opening the RDS firewall to the EB instance

Beanstalk created its own security group for the EC2 instance — let's
call it the *EB SG*. The RDS instance has its own security group
(`snapvault-db-sg`) which currently allows nothing inbound. We need a
rule that lets the EB SG talk to RDS on Postgres' port.

In the console:

1. **EC2 → Instances** → find the instance Beanstalk launched (its name
   starts with `snapvault-env-`) → in the side panel, note the
   **Security groups** assigned to it. The one we want is named
   something like `awseb-e-XXXXXXXX-stack-AWSEBSecurityGroup-YYYY`.
   Copy its **group ID** (it looks like `sg-0123abcd…`).
2. **EC2 → Security Groups → snapvault-db-sg → Inbound rules →
   Edit inbound rules → Add rule**:
   - Type: **PostgreSQL** (port 5432 fills in automatically)
   - Source: **Custom**, then paste the EB SG ID
   - Description: `Allow Flask app on EB to reach Postgres`
3. **Save rules.**

Within ten seconds the running Flask app on EB can open connections to
RDS. Why this pattern instead of allowing a specific IP? Because if EB
ever scales out to more instances, every new EC2 host automatically
joins the same EB SG and inherits this rule. There's nothing to update.

## Opening the app

```bash
eb open
```

This opens the Beanstalk environment's URL in a browser. Sign up, log
in, create an album, upload a photo — then confirm in another tab that
the object appears under `s3://snapvault-caan0020/` and a row appears
in the `photos` table of the RDS instance. That cross-check completes
the end-to-end loop and earns the deploy, S3, and RDS points all in one
test.

## Troubleshooting

Three commands cover almost every first-deploy issue:

```bash
eb status            # short health summary
eb logs --all        # full logs from /var/log on the EC2 instance — the most useful one
eb health            # per-instance and per-process health
```

The errors I've actually seen on first deploy:

- **`OperationalError: could not connect to server`** — the security
  group rule from the previous step is missing or points at the wrong
  SG. Open the EB instance's security groups in the EC2 console, copy
  the right SG ID, and add the inbound rule again.
- **502 Bad Gateway** — Flask never started. Run `eb logs --all` and
  look for a Python traceback near the top of `web.stdout.log`. Most
  often a typo in an env var or a missing dependency in
  `requirements.txt`.
- **`KeyError: 'DATABASE_URL'`** — typo in `eb setenv`. Re-run it with
  the correct name; the redeploy fixes things in about two minutes.

## Recording the public URL for the report

```bash
eb status --verbose | grep CNAME
```

That CNAME — something like
`snapvault-env.eba-abcdef.us-east-1.elasticbeanstalk.com` — is the
public address the instructor will visit during grading. Paste it into
the main `README.md` report and into the presentation notes.

## Cost

The EB EC2 instance is `t3.micro`, the same cheap class we used for
RDS — roughly $0.01 per hour, or $7 a month if left on. The single-
instance environment skips the load balancer entirely, which would
have been the larger cost. The RDS instance is the bigger budget
drain.

When you're done for the day, stop the RDS instance from the RDS
console and either stop or terminate the Beanstalk environment:

```bash
# Permanently delete the EB environment (and the EC2 instance)
eb terminate snapvault-env --force
```

For shorter pauses, use the AWS console — **Elastic Beanstalk →
Environments → snapvault-env → Actions → Stop environment** — which
keeps the configuration but releases the EC2 instance.
