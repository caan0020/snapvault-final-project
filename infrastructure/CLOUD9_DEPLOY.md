# Deploying SnapVault from Cloud9

This is the end-to-end procedure to take SnapVault from a fresh AWS
Academy Learner Lab to a running Elastic Beanstalk URL. Everything is
done from the **Cloud9** terminal — the only AWS DB is **DynamoDB** and
the only file store is **S3**, so there is no VPC, security-group, or
database-firewall wiring to do (that was the painful part of the old
RDS version).

> Region used throughout: **`us-east-1`**. Roles used: **`LabRole`** /
> **`LabInstanceProfile`** (pre-created by Learner Lab — you may not
> create new IAM roles).

---

## 0. Start the lab and open Cloud9

1. In **AWS Academy → Learner Lab**, click **Start Lab** and wait for the
   dot to go green.
2. Click **AWS** to open the console, search **Cloud9**, and open your
   environment (or create one: *Create environment → t3.micro → Amazon
   Linux 2023*).

The Cloud9 terminal already has working AWS credentials, so `aws`,
`python3` and `pip` calls just work — no `aws configure` needed.

---

## 1. Clone the project

```bash
cd ~/environment
git clone https://github.com/merito-cacba/sdpcba-2026-finalproject-caan0020.git
cd sdpcba-2026-finalproject-caan0020
```

(If the repo is private, clone with a token:
`git clone https://<TOKEN>@github.com/merito-cacba/sdpcba-2026-finalproject-caan0020.git`.)

---

## 2. Install dependencies

The deploy itself doesn't need a local virtualenv, but the
resource-creation scripts and the optional seeder do (`boto3`):

```bash
cd application
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

---

## 3. Create the AWS resources (DynamoDB + S3)

Two small, idempotent scripts do this. Run them once:

```bash
# two DynamoDB tables: SnapVault-Albums and SnapVault-Photos
python3 infrastructure/init_dynamodb.py

# one PRIVATE S3 bucket (all public access blocked); prints the name
python3 infrastructure/init_s3.py
```

`init_s3.py` prints a line like:

```
S3 is ready. Next:
    eb setenv SNAPVAULT_BUCKET=snapvault-3f9c1a2b7d4e
```

**Copy that bucket name** — you need it in step 5. (You can also pass
your own name: `python3 infrastructure/init_s3.py snapvault-caan0020`.)

Verify in the console: **DynamoDB → Tables** shows the two tables, and
**S3 → Buckets** shows your bucket with *"Block all public access: On"*.

---

## 4. Initialise Elastic Beanstalk

Make sure the EB CLI is available (install it once if needed):

```bash
pip install awsebcli --upgrade
eb --version
```

Then, **from inside `application/`** (the folder with `application.py`,
`Procfile` and `.ebextensions/`):

```bash
cd application
eb init -p python-3.11 snapvault --region us-east-1
```

`eb init` writes `.elasticbeanstalk/config.yml`. If it asks about
CodeCommit, answer **no**; if it asks about SSH, answer **no**.

---

## 5. Create the environment and point it at the bucket

```bash
eb create snapvault-env \
  --single \
  --instance-types t3.micro \
  --service-role LabRole \
  --instance_profile LabInstanceProfile
```

- `--single` → one instance, **no load balancer** (cheaper, and all the
  rubric needs).
- `--service-role LabRole` / `--instance_profile LabInstanceProfile` →
  reuse the lab roles. **This is the step that makes `eb create` succeed**
  — the default "create a new role" path is denied in Learner Lab.

`.ebextensions/01_env.config` already sets `SNAPVAULT_BACKEND=aws`, the
table names, and the region at deploy time. The only thing left is the
unique bucket name:

```bash
eb setenv SNAPVAULT_BUCKET=<the-name-init_s3.py-printed>
```

That triggers one quick redeploy. When health is **Green**, open it:

```bash
eb open      # opens the public elasticbeanstalk.com URL in a browser
eb status    # prints the CNAME if you'd rather copy the URL
```

---

## 6. (Optional) Load demo data into the cloud

To present with a full gallery instead of an empty one, seed straight
into DynamoDB + S3:

```bash
cd application
source .venv/bin/activate
SNAPVAULT_BACKEND=aws SNAPVAULT_BUCKET=<your-bucket> python3 seed.py
```

This creates 3 albums and 10 generated photos in the live cloud
resources. Refresh the app — the dashboard fills in.

---

## 7. End-to-end verification (proves all three services)

On the live URL:

1. **Albums → create an album.**
2. **Upload a photo.**
3. Open the photo, click **Download original**.

Then confirm in the AWS console:

- **S3 → your bucket →** there is an object under
  `albums/<album-id>/...` → *the app wrote to S3 (put_object) and read it
  back (get_object).*
- **DynamoDB → Tables → SnapVault-Photos → Explore items →** there is a
  matching row → *the app wrote to and read from DynamoDB.*
- The page you're looking at is served from
  `…elasticbeanstalk.com` → *the app runs on Elastic Beanstalk.*

That single flow demonstrates Elastic Beanstalk + S3 + DynamoDB together.

---

## 8. Redeploying after code changes

```bash
cd application
eb deploy
```

EB zips the folder (honouring `.ebignore`), ships it, and restarts
Gunicorn in ~1 minute. No manual zip/upload needed.

---

## 9. Capturing screenshots for the report

Take these (save into `infrastructure/screenshots/`):

| File | What to capture |
|---|---|
| `01-app-dashboard.png` | the running app's dashboard on the EB URL |
| `02-app-album.png` | an album page with photos |
| `03-eb-environment.png` | EB environment, Health **Green**, with the URL |
| `04-eb-config-env.png` | EB → Configuration → environment properties |
| `05-dynamodb-tables.png` | DynamoDB → the two SnapVault tables |
| `06-dynamodb-items.png` | SnapVault-Photos → Explore items (rows visible) |
| `07-s3-bucket.png` | S3 bucket objects + "Block all public access: On" |
| `08-ec2-instance.png` | the EC2 instance EB launched |
| `09-iam-roles.png` | IAM → LabRole / LabInstanceProfile |
| `10-cloud9.png` | the Cloud9 terminal mid-deploy (`eb status` output) |

---

## 10. Tear down when finished

```bash
eb terminate snapvault-env        # deletes the EB environment + EC2
```

DynamoDB on-demand tables and the S3 bucket cost almost nothing at rest,
but to remove them too:

```bash
aws dynamodb delete-table --table-name SnapVault-Albums
aws dynamodb delete-table --table-name SnapVault-Photos
aws s3 rb s3://<your-bucket> --force
```

---

## Troubleshooting

| Symptom | Cause & fix |
|---|---|
| `eb create` fails with an IAM `AccessDenied` after a few minutes | The default "create new role" path. Re-run with `--service-role LabRole --instance_profile LabInstanceProfile`. |
| App health **Degraded**, logs show `SNAPVAULT_BUCKET is not set` | You skipped `eb setenv SNAPVAULT_BUCKET=...`. Set it; EB redeploys. |
| `eb` logs show `AccessDeniedException` on DynamoDB/S3 | The instance profile lacks access. In Learner Lab `LabInstanceProfile` already covers both — make sure it was passed to `eb create`. |
| Photos 404 on the page | The bucket name on EB doesn't match the one the files were uploaded to. Check `eb printenv` vs the bucket in the S3 console. |
| `eb` command not found | `pip install awsebcli --upgrade`, then reopen the terminal. |

Per-service deep dives: [`setup-dynamodb.md`](setup-dynamodb.md),
[`setup-s3.md`](setup-s3.md), [`setup-eb.md`](setup-eb.md).
