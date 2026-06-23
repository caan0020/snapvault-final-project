# Application

SnapVault is a cloud photo gallery written in **Python with Flask**. You
create albums, upload photos, tag and favourite them, search, and share an
album with a public link. Photo **files** live in **Amazon S3**; photo and
album **metadata** lives in **Amazon DynamoDB**. The app is deployed to
**AWS Elastic Beanstalk**.

The same code runs locally with **no AWS account** (a JSON file + a local
folder) — the backend is chosen by one environment variable.

## Folder layout

```
application/
├── application.py            # Elastic Beanstalk / Gunicorn entry — exposes `application`
├── Procfile                  # web: gunicorn application:application
├── requirements.txt          # Flask, boto3, gunicorn, Werkzeug
├── seed.py                   # optional demo data (generates its own images)
├── .ebextensions/
│   └── 01_env.config         # env vars + WSGIPath, applied at deploy time
└── app/
    ├── __init__.py           # Flask app factory
    ├── config.py             # env-driven config + the local/aws BACKEND switch
    ├── models.py             # Album & Photo dataclasses (to_dict / from_dict)
    ├── routes.py             # all routes — full CRUD for albums and photos
    ├── repos/                # data layer
    │   ├── dynamo.py         #   DynamoDB (get_item / scan / put_item / delete_item)
    │   ├── local.py          #   JSON file (local dev)
    │   └── __init__.py       #   build_repo() picks one
    ├── storage/              # file layer
    │   ├── s3.py             #   S3 (put_object / get_object / delete_object)
    │   ├── local.py          #   local filesystem (local dev)
    │   └── __init__.py       #   build_storage() picks one
    ├── templates/            # Jinja templates (dashboard, albums, album, upload, photo, search, favorites, share)
    └── static/css/style.css
```

## Running locally (no AWS needed)

```bash
cd application
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py            # optional: fill the gallery with demo photos
python application.py
# open http://127.0.0.1:5000
```

By default `SNAPVAULT_BACKEND=local`, so data goes to `.data/` (a JSON
"database" + an `uploads/` folder). Nothing leaves your machine.

## Switching to the cloud

Set these and the *same code* runs on DynamoDB + S3:

| Variable | Example | Meaning |
|---|---|---|
| `SNAPVAULT_BACKEND` | `aws` | use DynamoDB + S3 instead of local files |
| `SNAPVAULT_BUCKET` | `snapvault-ab12cd` | the S3 bucket for photo files |
| `SNAPVAULT_ALBUMS_TABLE` | `SnapVault-Albums` | DynamoDB table for albums |
| `SNAPVAULT_PHOTOS_TABLE` | `SnapVault-Photos` | DynamoDB table for photos |
| `AWS_REGION` | `us-east-1` | region for both services |
| `SNAPVAULT_SECRET` | *(random hex)* | Flask session secret |

On Elastic Beanstalk the first four are set by `.ebextensions` +
`eb setenv`. Full deploy steps:
[`../infrastructure/CLOUD9_DEPLOY.md`](../infrastructure/CLOUD9_DEPLOY.md).
