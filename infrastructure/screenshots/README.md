# Screenshots

Capture these during the Cloud9 → Elastic Beanstalk deploy and drop the
PNGs in this folder. The top-level [`../../README.md`](../../README.md)
report links to them by these exact names.

| File | What to capture |
|---|---|
| `01-app-dashboard.png` | the running app's **dashboard** on the live `…elasticbeanstalk.com` URL |
| `02-app-album.png` | an **album page** with a few photos in the grid |
| `03-eb-environment.png` | Elastic Beanstalk environment, **Health: Green**, URL visible |
| `04-eb-config-env.png` | EB → Configuration → **environment properties** (`SNAPVAULT_*`) |
| `05-dynamodb-tables.png` | DynamoDB → Tables → **SnapVault-Albums** + **SnapVault-Photos** |
| `06-dynamodb-items.png` | `SnapVault-Photos` → **Explore items** (rows written by the app) |
| `07-s3-bucket.png` | the S3 bucket's objects + **"Block all public access: On"** |
| `08-ec2-instance.png` | the **EC2 instance** Elastic Beanstalk launched |
| `09-iam-roles.png` | IAM → **LabRole** / **LabInstanceProfile** |
| `10-cloud9.png` | the **Cloud9** terminal mid-deploy (e.g. `eb status` output) |

Tip: a quick way to get `06` populated is to run the seeder against the
cloud first — `SNAPVAULT_BACKEND=aws SNAPVAULT_BUCKET=<bucket> python3 seed.py`.
