# RDS setup

This document explains how the `snapvault-db` Postgres database was
created, the choices made along the way, and a real bug we hit and
solved — included in detail because the rubric rewards documented
problem-solving.

## Why PostgreSQL on RDS

SnapVault's data model is small but very relational: users own albums,
albums own photos, photos can reference each other through relations
like "next photo in the album." That shape fits a relational database
much better than a key-value store, so we chose **PostgreSQL** over
DynamoDB. RDS, in turn, is AWS's managed Postgres — it handles
patching, backups, and host operating-system upgrades so we don't have
to. For a student project this is the right trade-off: more cost than
running Postgres ourselves on EC2, but enormously less operational
work.

We chose PostgreSQL specifically (rather than MySQL or MariaDB) because
the Flask code already imports `psycopg2-binary` and connects with a
`postgresql://` URL. Switching to MySQL would mean changing the driver,
the URL scheme, and re-testing — work that earns no rubric points.

## Console walkthrough

In the AWS Console, open **RDS → Create database** and pick **Standard
create** (the wizard with all fields), then fill in:

| Section | Field | Value | Why |
|---|---|---|---|
| Engine options | Engine | **PostgreSQL** | not Aurora — Aurora is denied by Learner Lab policy |
| | Engine version | latest 16.x available | Free Tier and Sandbox templates require versions AWS has flagged as Free Tier eligible; newer majors like 18 are too recent |
| Templates | | **Sandbox** | Free Tier is hidden in Learner Lab because the underlying account is older than 12 months — Sandbox is the equivalent for non-Free-Tier-eligible accounts |
| Availability & durability | Deployment | **Single-AZ DB instance (1 instance)** | Multi-AZ is explicitly blocked by the lab policy and costs double |
| Settings | DB identifier | `snapvault-db` | |
| | Master username | `postgres` | |
| | Master password | auto-generate | the password is shown exactly once — copy it then |
| Instance configuration | Instance class | `db.t3.micro` | the only burstable class the lab consistently allows |
| Storage | Storage type | **gp2** | see the problem-encountered section below |
| | Allocated storage | 20 GiB | matches Free Tier max |
| | Storage autoscaling | **off** | autoscaling is a sneaky cost source |
| Connectivity | Public access | **No** | the DB has no public IP; only Elastic Beanstalk reaches it over the VPC |
| | VPC security group | new — `snapvault-db-sg` | starts empty; we add an inbound rule for EB later |
| Authentication | Method | **Password** | the simplest option, and matches our `DATABASE_URL` design |
| Monitoring | Performance Insights | **off** | extra cost, no rubric value |
| | Enhanced monitoring | **off** | same |
| Additional configuration | Initial database name | `snapvault` | easy to miss, but if you skip it the app will fail to connect because the database literally doesn't exist |
| | Backup retention | 1 day | minimum; keeps backup storage cheap |
| | Deletion protection | **off** | so we can clean up after grading |

Click **Create database** and wait roughly five to ten minutes for the
status to go from **Creating** → **Backing-up** → **Available**.

## Problem encountered: the gp3 explicit-deny

The first three attempts at clicking *Create database* all failed with
the same error:

> *User ... is not authorized to perform: rds:CreateDBInstance ... with
> an explicit deny in an identity-based policy:
> arn:aws:iam::742165406465:policy/Pvoclabs2*

The error message says *which* IAM policy is denying (`Pvoclabs2`) but
not *which attribute* of the request the policy disagrees with. That made
it tricky to debug because the wizard ships dozens of fields, and the
denial happens server-side after submission.

The diagnostic approach was to toggle one field at a time and resubmit.
After ruling out the instance class, the engine version, encryption
state, and Multi-AZ, the culprit turned out to be the storage type.
The wizard's default — even under the Sandbox template — is **gp3**,
and `Pvoclabs2` only allows **gp2** in this lab variant. Switching the
storage type to gp2 made the next submission succeed immediately.

This is exactly the kind of problem the rubric asks to document: a real
error message, a methodical narrowing-down process, and a one-field fix
that wasn't obvious from the documentation.

## After provisioning

Once the status is **Available**, open the instance page and copy the
**Endpoint** from the *Connectivity & security* tab. It looks like
`snapvault-db.cgmv1jdtqqha.us-east-1.rds.amazonaws.com`. From the
endpoint and the master password, the SQLAlchemy connection string for
Elastic Beanstalk becomes:

```
postgresql://postgres:PASSWORD@<endpoint>:5432/snapvault
```

This goes into the `DATABASE_URL` environment variable on Beanstalk
([setup-eb.md](setup-eb.md)). It deliberately never appears in this
repository — the only places it lives are AWS's encrypted env-var
store and a private note where the master password was saved.

## Why private (no public access)

I chose to put the database in private subnets, meaning it has no
public IP address. Only resources inside the same default VPC — the
Elastic Beanstalk EC2 instance, plus the Cloud9 environment — can reach
it. This is more secure than a publicly accessible database, because
even if the security group is misconfigured there's no internet route to
the host at all. The trade-off is mild: we can't connect with a local
pgAdmin or DBeaver directly. When we needed to inspect the database, we
ran `psql` from inside Cloud9 (which lives in the same VPC).
