import os
from flask import Flask
from app.config import get_config
from app.extensions import db, migrate
from app.common.errors import register_error_handlers


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)

    config_class = get_config(config_name)
    app.config.from_object(config_class)
    app.config["PUBLIC_BASE_URL"] = os.environ.get("PUBLIC_BASE_URL")
    if config_class is get_config("production") and (
        not app.config["SECRET_KEY"]
        or app.config["SECRET_KEY"] == "dev-secret-key-change-in-production"
    ):
        raise ValueError("Production requires a secure SECRET_KEY")

    db.init_app(app)
    if migrate is not None:
        migrate.init_app(app, db)

    register_error_handlers(app)

    from app.health.routes import health_bp
    app.register_blueprint(health_bp)

    from app.frontend.routes import frontend_bp
    app.register_blueprint(frontend_bp)

    from app import models  # noqa: F401  Registra modelos con SQLAlchemy

    from app.auth.routes import auth_bp
    from app.auth.csrf import protect_csrf
    app.register_blueprint(auth_bp)
    app.before_request(protect_csrf)

    from app.mesas.routes import mesas_bp
    app.register_blueprint(mesas_bp)

    from app.mesas.public_routes import public_mesas_bp
    app.register_blueprint(public_mesas_bp)

    from app.users.routes import users_bp
    app.register_blueprint(users_bp)

    from app.users.cli import init_roles, create_admin, seed_demo_cmd
    app.cli.add_command(init_roles)
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_demo_cmd)

    from app.catalog.routes import categories_bp, products_bp
    app.register_blueprint(categories_bp)
    app.register_blueprint(products_bp)

    from app.servicios.routes import servicios_bp
    from app.pedidos.routes import pedidos_bp
    app.register_blueprint(servicios_bp)
    app.register_blueprint(pedidos_bp)

    return app
