"""Flask application factory.

Wires the configuration, the data repository (DynamoDB / local JSON) and
the file storage (S3 / local filesystem) into a single Flask app and
registers the routes blueprint.
"""
from flask import Flask

from .config import Config
from .repos import build_repo
from .storage import build_storage
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_UPLOAD_BYTES

    # The chosen backends (local or AWS) are built once and stored on the
    # app so the route handlers can stay backend-agnostic.
    app.config["REPO"] = build_repo()
    app.config["STORAGE"] = build_storage()
    app.config["BACKEND"] = Config.BACKEND

    app.register_blueprint(bp)
    return app
