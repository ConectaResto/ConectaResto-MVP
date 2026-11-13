from sqlalchemy import text


def test_database_connection(app):
    with app.app_context():
        from app.extensions import db
        result = db.session.execute(text("SELECT 1")).scalar()
        assert result == 1