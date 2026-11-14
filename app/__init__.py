import os
from flask import Flask
from app.config import get_config
from app.extensions import db, migrate
from app.common.errors import register_error_handlers


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    db.init_app(app)
    if migrate is not None:
        migrate.init_app(app, db)

    register_error_handlers(app)

    from app.health.routes import health_bp
    app.register_blueprint(health_bp)

    from app.frontend.routes import frontend_bp
    app.register_blueprint(frontend_bp)

    from app import models  # noqa: F401  Registra modelos con SQLAlchemy

    return app