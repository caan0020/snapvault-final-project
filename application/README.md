# Application

SnapVault is a small photo-gallery web application written in **Python with
Flask**. Users can register, log in, create albums, upload pictures and
browse their gallery. Files are stored in **Amazon S3** and all metadata
in **Amazon RDS (PostgreSQL)**.

## Folder layout

```
application/
├── application.py          # Elastic Beanstalk entry point (exposes `application`)
├── config.py               # env-driven config (DATABASE_URL, S3_BUCKET, STORAGE_BACKEND, ...)
├── requirements.txt        # Python dependencies (Flask, SQLAlchemy, boto3, psycopg2-binary, ...)
├── .gitignore              # excludes .venv/, *.db, uploads/, .elasticbeanstalk/
└── snapvault/
    ├── __init__.py         # Flask app factory + LoginManager
    ├── models.py           # SQLAlchemy models: User, Album, Photo
    ├── storage.py          # Pluggable storage layer (LocalStorage for dev, S3Storage via boto3 for prod)
    ├── auth.py             # /register, /login, /logout routes (Flask-Login)
    ├── main.py             # Full CRUD routes for albums and photos
    ├── templates/          # 8 Jinja templates (base + index + login + register + albums + album + upload + photo)
    └── static/style.css
```

## Running locally

```bash
cd application
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python application.py
# open http://127.0.0.1:5050
```

By default the app uses **SQLite** (`snapvault.db` in this folder) and saves
uploaded photos to a local `uploads/` directory. Setting the env vars
`STORAGE_BACKEND=s3`, `S3_BUCKET=...`, and `DATABASE_URL=postgresql://...`
switches it to use RDS + S3 with zero code changes — that's how it runs
on Elastic Beanstalk in the cloud.
