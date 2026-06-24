# SnapVault — Final Project Report

A cloud **photo gallery** web application written in Python with Flask,
deployed to AWS using **Elastic Beanstalk**, **DynamoDB** and **S3**, and
provisioned from **Cloud9**.

**Author:** Can Akgun (`caan0020`)
**Course:** CACBA 2026 — Services and Development Platforms for Cloud Based Applications
**Live URL:** _`http://snapvault-env.<your-id>.us-east-1.elasticbeanstalk.com`_
&nbsp;&nbsp;_(fill in after `eb open` — see [deployment](#5-deployment-to-the-cloud))_

---

## Table of contents

1. [Project description](#1-project-description)
2. [Architecture](#2-architecture)
3. [AWS services used](#3-aws-services-used-with-screenshots)
4. [How CRUD, S3 and DynamoDB are wired](#4-how-crud-s3-and-dynamodb-are-wired)
5. [Deployment to the cloud](#5-deployment-to-the-cloud)
6. [Problems encountered and how they were solved](#6-problems-encountered-and-how-they-were-solved)
7. [Repository content](#7-repository-content)
8. [Running locally](#8-running-locally)

---

## 1. Project description

**SnapVault** is a web-based photo gallery hosted entirely in AWS. You
organise pictures into albums, upload them to the cloud, then tag,
favourite, search and share them. The image files are kept in Amazon S3
and everything *about* them (titles, tags, which album, …) in Amazon
DynamoDB, so memories live safely in the cloud instead of on a phone or
laptop that can break.

### Features

- **Albums & photos** with full create/read/update/delete.
- **Upload to the cloud** — each file is written to S3 by the app itself.
- **Tags** — comma-separated, normalised, shown as chips.
- **Search** — across photo titles, descriptions and tags.
- **Favourites** — star photos; they get a pinned section.
- **Dashboard** — live counts (photos, albums, favourites, bytes stored).
- **Public share link** — each album has an unguessable token URL that
  shows a clean, read-only gallery without exposing the management UI.
- **Download original** — the app pulls the file back out of S3 and
  streams it to the browser.

### Full CRUD (rubric criterion 1)

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| **Album** | "Create album" form → `put_item` | albums list + album page (`scan` / `get_item`) | rename, reset share link → `put_item` | delete album → cascades to its photos' DynamoDB rows **and** S3 objects |
| **Photo** | upload form → **S3 `put_object`** + DynamoDB `put_item` | gallery, single-photo page, raw stream (`get_item` + **S3 `get_object`**) | edit title / description / tags, toggle favourite, move album → `put_item` | delete → DynamoDB `delete_item` + **S3 `delete_object`** |

### Pages (server-rendered, not a SPA)

1. Dashboard (`/`)
2. Albums (`/albums`)
3. Single album (`/albums/<id>`)
4. Upload photo (`/albums/<id>/upload`)
5. Single photo (`/photos/<id>`)
6. Search (`/search`)
7. Favourites (`/favorites`)
8. Public shared album (`/share/<token>`)

That is well above the "at least three pages" requirement.

---

## 2. Architecture

```
                       Public internet
                              │  HTTP
                              ▼
              ┌───────────────────────────────┐
              │     AWS Elastic Beanstalk     │
              │   single instance, t3.micro   │
              │      Nginx → Gunicorn         │
              │        Flask app (boto3)      │
              │   role: LabInstanceProfile    │
              └──────┬─────────────────┬──────┘
                     │   AWS SDK (boto3) / HTTPS
            ┌────────▼────────┐   ┌────▼─────────────┐
            │  Amazon DynamoDB │   │   Amazon S3      │
            │  SnapVault-Albums│   │  private bucket  │
            │  SnapVault-Photos│   │  photo files     │
            │  (metadata)      │   │                  │
            └──────────────────┘   └──────────────────┘
```

### Framework choices

- **Python + Flask** (app-factory pattern, server-rendered Jinja2
  templates). Flask is small and the Elastic Beanstalk Python platform
  looks for a WSGI callable named `application` — exactly what
  `application/application.py` exposes.
- **Gunicorn** as the WSGI server in production (via the `Procfile`).
- **boto3** for every AWS call, used directly in our own `repos/dynamo.py`
  and `storage/s3.py` — not hidden behind another wrapper — so the
  upload/download/read/write flow is explicit (important for the rubric).
- **No ORM, no SQL.** DynamoDB is a key–value store; the data layer is a
  thin repository over boto3.

### Provider abstraction (the key design idea)

All data access goes through a **repository** interface (`app/repos`) and
all file access through a **storage** interface (`app/storage`). A factory
picks the implementation from one environment variable,
`SNAPVAULT_BACKEND`:

| `SNAPVAULT_BACKEND` | Data | Files |
|---|---|---|
| `local` (default) | a JSON file in `.data/` | the local `.data/uploads/` folder |
| `aws` | **DynamoDB** | **S3** |

The route handlers and templates are identical in both modes, so the app
runs on a laptop with no AWS account *and* in the cloud with **zero code
changes** — moving to AWS is a configuration change. This is the 12-factor
"config in the environment" principle.

---

## 3. AWS services used (with screenshots)

### Amazon DynamoDB — metadata

Two on-demand tables, each with a single string partition key `id`:
`SnapVault-Albums` and `SnapVault-Photos`. The app reads and writes them
with boto3 (`get_item`, `scan`, `put_item`, `delete_item`). Every
attribute is stored as a string to keep marshalling simple. Created by
[`infrastructure/init_dynamodb.py`](infrastructure/init_dynamodb.py); full
notes in [`infrastructure/setup-dynamodb.md`](infrastructure/setup-dynamodb.md).

![DynamoDB tables](infrastructure/screenshots/05-dynamodb-tables.png)
![DynamoDB items](infrastructure/screenshots/06-dynamodb-items.png)

### Amazon S3 — photo files

A single **private** bucket holds the image bytes. Upload, download and
delete are three explicit boto3 calls in
[`app/storage/s3.py`](application/app/storage/s3.py) — `put_object`,
`get_object`, `delete_object`. The bucket has **all public access
blocked**: the app reads each object itself and streams it back through a
Flask route, so the browser never talks to S3 directly. Created by
[`infrastructure/init_s3.py`](infrastructure/init_s3.py); notes in
[`infrastructure/setup-s3.md`](infrastructure/setup-s3.md).

![S3 bucket](infrastructure/screenshots/07-s3-bucket.png)

### AWS Elastic Beanstalk — hosting

The Flask app runs on a single-instance Beanstalk environment
(`snapvault-env`, Python 3.11 / Amazon Linux 2023, `t3.micro`). Beanstalk
provides Nginx, Gunicorn, the EC2 instance, health monitoring and a public
URL. Static configuration lives in
[`application/.ebextensions/01_env.config`](application/.ebextensions/01_env.config);
the unique bucket name is set with `eb setenv`. Notes in
[`infrastructure/setup-eb.md`](infrastructure/setup-eb.md).

![Elastic Beanstalk environment](infrastructure/screenshots/03-eb-environment.png)
![EB environment properties](infrastructure/screenshots/04-eb-config-env.png)

### Amazon EC2 — the instance behind Beanstalk

Beanstalk manages one `t3.micro` EC2 instance running Amazon Linux 2023.
We never SSH in; Beanstalk owns its lifecycle. It carries the
`LabInstanceProfile`, which grants the app its DynamoDB + S3 permissions
at runtime — so **no AWS access keys appear anywhere** in the repo.

![EC2 instance](infrastructure/screenshots/08-ec2-instance.png)

### AWS Cloud9 — the development & deployment environment

The whole project is cloned, the resources are created
(`init_dynamodb.py`, `init_s3.py`), and the app is deployed
(`eb create` / `eb deploy`) from a Cloud9 terminal, whose credentials are
already wired into the lab account.

![Cloud9 terminal](infrastructure/screenshots/10-cloud9.png)

### AWS IAM — credentials

AWS Academy Learner Lab forbids creating new IAM roles, so SnapVault reuses
the pre-existing **`LabRole`** (Beanstalk's service role) and
**`LabInstanceProfile`** (the EC2 instance role). Because the instance
profile supplies credentials automatically, the repository contains zero
static keys.

![IAM roles](infrastructure/screenshots/09-iam-roles.png)

---

## 4. How CRUD, S3 and DynamoDB are wired

A single upload touches both AWS services and demonstrates a write to each:

```
POST /albums/<id>/upload
   │
   ├─ app reads the uploaded bytes
   ├─ storage.save(key, bytes)      → S3   put_object        (file → S3)
   └─ repo.photos.save(photo)       → DynamoDB put_item       (metadata → DynamoDB)
```

Displaying that photo demonstrates a read from each:

```
GET /photos/<id>            → DynamoDB get_item   (metadata)
GET /photos/<id>/raw        → S3 get_object        (bytes, streamed by the app)
```

- DynamoDB **read + write**: `app/repos/dynamo.py`
  (`get_item`, `scan`, `put_item`, `delete_item`).
- S3 **upload + download**: `app/storage/s3.py`
  (`put_object`, `get_object`, `delete_object`).

---

## 5. Deployment to the cloud

Deployed from **Cloud9** with the EB CLI. Full walkthrough:
[`infrastructure/CLOUD9_DEPLOY.md`](infrastructure/CLOUD9_DEPLOY.md). In short:

```bash
# 1. clone in Cloud9
git clone <repo-url> && cd sdpcba-2026-finalproject-caan0020

# 2. create the AWS resources (idempotent)
python3 infrastructure/init_dynamodb.py        # SnapVault-Albums + SnapVault-Photos
python3 infrastructure/init_s3.py              # private bucket (prints its name)

# 3. deploy the app
cd application
eb init -p python-3.11 snapvault --region us-east-1
eb create snapvault-env --single --instance-types t3.micro \
   --service-role LabRole --instance_profile LabInstanceProfile
eb setenv SNAPVAULT_BUCKET=<bucket-name-from-step-2>
eb open
```

`.ebextensions/01_env.config` sets the backend mode, table names and
region automatically; only the unique bucket name is passed with
`eb setenv`. The optional
[`application/seed.py`](application/seed.py) can fill the live gallery with
demo photos for the presentation.

![App running on Elastic Beanstalk](infrastructure/screenshots/01-app-dashboard.png)
![An album with photos](infrastructure/screenshots/02-app-album.png)

---

## 6. Problems encountered and how they were solved

### 1. RDS made the cloud setup fragile → migrated to DynamoDB

The first version of this project used **RDS PostgreSQL**. Getting it
running meant creating a VPC security-group rule from Beanstalk to RDS,
hitting an explicit-deny on `gp3` storage in the lab, and a first-deploy
crash because the initial database name was blank. None of that is
*application* logic — it's networking plumbing. Switching the data layer to
**DynamoDB** removed the VPC, the security group, the firewall rule and the
"database does not exist" class of errors entirely: DynamoDB is reached over
the AWS API with the instance-profile credentials, so there is nothing to
wire. The repository abstraction (`app/repos`) made the swap a matter of
adding one new file (`dynamo.py`) behind the same interface.

### 2. DynamoDB rejects mixed Python types

DynamoDB's document API raises on a raw Python `bool`, and numbers come
back as `Decimal`, which then breaks JSON/templating. **Fix:** store every
attribute as a **string** (`favorite` is `"0"` / `"1"`, `size` is a string
of bytes) and convert at the edges in `app/models.py`. Marshalling becomes
trivial and the local JSON file stays human-readable too.

### 3. The S3 bucket must stay private, but the browser needs the image

A public bucket would fail the "Block all public access" expectation.
**Fix:** never hand the browser an S3 URL. The app reads each object itself
with `get_object` and streams the bytes through a Flask route
(`/photos/<id>/raw`). This keeps the bucket fully private **and** satisfies
the rubric's "files downloaded by the app code" line, because the download
is an explicit boto3 call in our code rather than a presigned/public link.

### 4. `eb create` fails with an IAM denial in Learner Lab

Beanstalk's wizard defaults to *creating new IAM roles*, but Learner Lab
denies `iam:CreateRole`, so `eb create` fails several minutes in. **Fix:**
pass the pre-existing lab roles explicitly —
`--service-role LabRole --instance_profile LabInstanceProfile`. Those roles
also grant the running app its DynamoDB + S3 access, so no keys are needed.

### 5. App started but crashed in `aws` mode — bucket name missing

In `aws` mode the storage layer needs a bucket name; on the very first
deploy it wasn't set yet, so `S3FileStorage` raised at startup and health
went **Degraded**. **Fix:** `eb setenv SNAPVAULT_BUCKET=<name>` (the bucket
name is unique per deploy, so it can't live in `.ebextensions`). The
redeploy brought health to **Green**. The error message in
`app/storage/s3.py` was made explicit so the cause is obvious in the logs.

### 6. Elastic Beanstalk Python platform conventions

EB wouldn't start the app until it found a WSGI callable named
`application` and a start command. **Fix:** `application/application.py`
exposes `application = create_app()`, and the one-line `Procfile`
(`web: gunicorn application:application`) tells Beanstalk how to run it.

---

## 7. Repository content

```
sdpcba-2026-finalproject-caan0020/
├── README.md                         # this report
├── application/                      # the Flask app (Elastic Beanstalk deploy root)
│   ├── application.py                # WSGI entry — exposes `application`
│   ├── Procfile                      # web: gunicorn application:application
│   ├── requirements.txt              # Flask, boto3, gunicorn, Werkzeug
│   ├── seed.py                       # optional demo data (self-generated images)
│   ├── .ebextensions/01_env.config   # env vars + WSGIPath
│   └── app/
│       ├── __init__.py               # Flask app factory
│       ├── config.py                 # env-driven config + local/aws switch
│       ├── models.py                 # Album & Photo dataclasses
│       ├── routes.py                 # all routes — full CRUD
│       ├── repos/                    # DynamoDB / local JSON data layer
│       ├── storage/                  # S3 / local filesystem file layer
│       ├── templates/                # 9 Jinja templates + macros
│       └── static/css/style.css
└── infrastructure/
    ├── CLOUD9_DEPLOY.md              # full Cloud9 → Beanstalk walkthrough
    ├── init_dynamodb.py              # create the two DynamoDB tables
    ├── init_s3.py                    # create the private S3 bucket
    ├── setup-dynamodb.md             # DynamoDB deep dive
    ├── setup-s3.md                   # S3 deep dive
    ├── setup-eb.md                   # Elastic Beanstalk deep dive
    ├── README.md                     # infrastructure index
    └── screenshots/                  # AWS console captures referenced above
```

---

## 8. Running locally

No AWS account needed — the default backend is `local` (a JSON file + a
local folder):

```bash
cd application
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py            # optional: fill the gallery with demo photos
python application.py
# open http://127.0.0.1:5000
```

Setting `SNAPVAULT_BACKEND=aws`, `SNAPVAULT_BUCKET=…` (and the table /
region vars) flips the very same code onto DynamoDB + S3 — the same switch
Elastic Beanstalk uses at deploy time.
