# CACBA - Final Project

Repository to keep all files related to Final Project.

## Author

Can Akgun

## Project title

**SnapVault**

## Project description

SnapVault is a web-based photo gallery application that lets users sign up,
upload their pictures to the cloud, organize them into albums and browse them
from any device. The goal is to provide a simple, personal place to keep
memories safe in AWS instead of relying on a single phone or laptop.

### Planned functions

- **User accounts** — sign up, log in and log out. Each user only sees their own albums and photos.
- **Photo upload** — upload one or many pictures at a time. Files are stored in **Amazon S3**; the photo metadata (owner, album, title, description, upload date) is stored in **Amazon RDS (PostgreSQL)**.
- **Albums** — create, rename and delete albums to group related pictures.
- **Gallery view** — browse a responsive grid of thumbnails for each album, with a single-photo view for the full-size image.
- **Search & filter** — find pictures by title, description or upload date.
- **Delete photos** — remove a picture both from the database and from S3.

### Pages (server-rendered, more than three)

1. Home / landing page
2. Login & registration pages
3. Albums list (dashboard)
4. Single album / gallery view
5. Photo upload page
6. Single photo detail page

### Tech stack

- **Language / framework:** Python with **Flask** (Jinja2 templates, Flask-Login, Flask-SQLAlchemy, boto3).
- **Database:** **Amazon RDS — PostgreSQL** (relational).
- **File storage:** **Amazon S3** for all uploaded images.
- **Hosting:** **AWS Elastic Beanstalk** (Python platform) — Beanstalk manages the EC2 instances, load balancer and deployments, which keeps the operational work minimal for a student project.

## Repository content

1. **application** — application source code (Flask app, templates, static files, requirements.txt).
2. **infrastructure** — scripts and configuration used to build / deploy the app (Elastic Beanstalk config, Dockerfiles, shell scripts, Terraform files, etc.).
