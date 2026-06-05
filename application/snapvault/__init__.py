from flask import Flask
from flask_login import LoginManager

from config import Config
from .models import db, User


login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        config_class.LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    return app


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))
