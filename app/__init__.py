import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, session
from flask_login import LoginManager

from .models import User, db

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "data"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "backups"), exist_ok=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
    relative_path = database_url.replace("sqlite:///", "", 1) if database_url.startswith("sqlite:///") else ""
    if database_url.startswith("sqlite:///") and relative_path != ":memory:" and not os.path.isabs(relative_path):
        database_path = os.path.abspath(os.path.join(app.root_path, "..", relative_path))
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        database_url = f"sqlite:///{database_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import bp as auth_bp
    from .routes import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.before_request
    def keep_admin_session_timed():
        session.permanent = True

    with app.app_context():
        db.create_all()
        User.ensure_default_admin()

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
