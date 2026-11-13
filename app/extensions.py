try:
    from flask_sqlalchemy import SQLAlchemy
    from flask_migrate import Migrate

    db = SQLAlchemy()
    migrate = Migrate()
except ImportError:
    from flask_sqlalchemy import SQLAlchemy

    db = SQLAlchemy()
    migrate = None