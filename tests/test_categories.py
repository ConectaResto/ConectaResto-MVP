import pytest
from unittest.mock import MagicMock
from sqlalchemy.exc import IntegrityError
from app import create_app
from app.extensions import db
from app.models.category import Category
from app.catalog.service import (
    CategoryAlreadyExists,
    CategoryNotFound,
    create_category,
    deactivate_category,
    get_category,
    list_categories,
    update_category,
    _is_duplicate_category_name_error,
)


def _requires_mysql():
    """Retorna True solo si la base de pruebas usa MySQL."""
    from app.config import get_config

    return get_config("testing").SQLALCHEMY_DATABASE_URI.startswith("mysql")


@pytest.mark.skipif(
    not _requires_mysql(),
    reason="La collation utf8mb4_0900_ai_ci es específica de MySQL 8.0; SQLite no la soporta y no puede verificar el comportamiento de acentos-insensibilidad en BD.",
)
def test_create_category_duplicate_name_accent_case_insensitive(app):
    """Duplicado con acento y mayúsculas bajo collation MySQL utf8mb4_0900_ai_ci.

    Esta prueba solo se ejecuta cuando la base de pruebas es MySQL 8.0.
    En SQLite se omite porque no replica la collation autorizada.
    """
    with app.app_context():
        create_category({"name": "Café"})
        with pytest.raises(CategoryAlreadyExists):
            create_category({"name": "CAFÉ"})


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_create_category(app):
    with app.app_context():
        category = create_category({"name": "Bebidas", "description": "Refrescos y jugos"})
        assert category.id is not None
        assert category.name == "Bebidas"
        assert category.description == "Refrescos y jugos"
        assert category.is_active is True


def test_new_categories_are_active(app):
    with app.app_context():
        category = create_category({"name": "Entradas"})
        assert category.is_active is True


def test_list_categories_returns_only_active(app):
    with app.app_context():
        create_category({"name": "Activa"})
        create_category({"name": "Inactiva"})
        # deactivate the second one
        categories = list_categories(include_inactive=False)
        inactive = Category.query.filter(Category.name == "Inactiva").first()
        deactivate_category(inactive.id)

        active_list = list_categories(include_inactive=False)
        assert len(active_list) == 1
        assert active_list[0].name == "Activa"

        all_list = list_categories(include_inactive=True)
        assert len(all_list) == 2


def test_get_category_by_id(app):
    with app.app_context():
        created = create_category({"name": "Platos fuertes"})
        fetched = get_category(created.id, include_inactive=False)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Platos fuertes"


def test_get_inactive_category_returns_none(app):
    with app.app_context():
        created = create_category({"name": "Temporal"})
        deactivate_category(created.id)
        fetched = get_category(created.id, include_inactive=False)
        assert fetched is None


def test_update_category(app):
    with app.app_context():
        created = create_category({"name": "Nombre viejo", "description": "Desc vieja"})
        updated = update_category(
            created.id,
            {"name": "Nombre nuevo", "description": "Desc nueva"},
            include_inactive=False,
        )
        assert updated.name == "Nombre nuevo"
        assert updated.description == "Desc nueva"
        assert updated.is_active is True


def test_update_category_name_case_insensitive_unique(app):
    with app.app_context():
        create_category({"name": "Cafe"})
        with pytest.raises(CategoryAlreadyExists):
            create_category({"name": "CAFE"})


def test_patch_does_not_change_is_active(app):
    with app.app_context():
        created = create_category({"name": "Test", "description": "Desc"})
        assert created.is_active is True
        updated = update_category(
            created.id,
            {"name": "Nuevo nombre", "description": "Nueva desc"},
            include_inactive=False,
        )
        assert updated.is_active is True
        assert updated.name == "Nuevo nombre"
        assert updated.description == "Nueva desc"


def test_update_category_is_active_false_rejected(app):
    with app.app_context():
        created = create_category({"name": "Test2", "description": "Desc"})
        with pytest.raises(ValueError):
            update_category(created.id, {"name": "Nombre", "is_active": False})
        assert created.is_active is True
        assert created.name == "Test2"


def test_create_category_duplicate_name_case_insensitive(app):
    with app.app_context():
        create_category({"name": "Bebidas"})
        with pytest.raises(CategoryAlreadyExists):
            create_category({"name": "bebidas"})


def test_create_category_without_name_raises(app):
    with app.app_context():
        with pytest.raises(CategoryAlreadyExists):
            create_category({"name": ""})


def test_deactivate_category_sets_is_active_false(app):
    with app.app_context():
        created = create_category({"name": "Para desactivar"})
        assert created.is_active is True
        result = deactivate_category(created.id)
        assert result is not None
        assert result.is_active is False


def test_deactivate_already_inactive_returns_none(app):
    with app.app_context():
        created = create_category({"name": "Ya inactiva"})
        deactivate_category(created.id)
        result = deactivate_category(created.id)
        assert result is None


def test_deactivate_nonexistent_category_raises(app):
    with app.app_context():
        with pytest.raises(CategoryNotFound):
            deactivate_category(99999)


# ---------------------------------------------------------------------------
# Pruebas de detección de violación de UNIQUE en categories.name
# ---------------------------------------------------------------------------


def _make_mysql_duplicate_error():
    """Crea un IntegrityError simulando MySQL código 1062 (ER_DUP_ENTRY)."""
    orig = MagicMock()
    orig.args = (1062, "Duplicate entry 'Bebidas' for key 'categories.name'")
    return IntegrityError("statement", {}, orig)


def _make_sqlite_duplicate_error():
    """Crea un IntegrityError simulando SQLite UNIQUE constraint failed."""
    orig = MagicMock()
    orig.args = ("UNIQUE constraint failed: categories.name",)
    return IntegrityError("statement", {}, orig)


def _make_non_duplicate_error():
    """Crea un IntegrityError que NO es duplicado de nombre (ej. FK violation)."""
    orig = MagicMock()
    orig.args = (1452, "Cannot add or update a child row: a foreign key constraint fails")
    return IntegrityError("statement", {}, orig)


def test_is_duplicate_category_name_error_mysql_duplicate():
    """MySQL código 1062 se detecta como duplicado de nombre."""
    exc = _make_mysql_duplicate_error()
    assert _is_duplicate_category_name_error(exc) is True


def test_is_duplicate_category_name_error_sqlite_duplicate():
    """SQLite UNIQUE constraint failed en categories.name se detecta como duplicado."""
    exc = _make_sqlite_duplicate_error()
    assert _is_duplicate_category_name_error(exc) is True


def test_is_duplicate_category_name_error_non_duplicate():
    """Un error de integridad distinto (FK violation) no se confunde con duplicado."""
    exc = _make_non_duplicate_error()
    assert _is_duplicate_category_name_error(exc) is False


def test_create_category_db_duplicate_name_raises_category_already_exists(app, monkeypatch):
    """Si el commit falla con UNIQUE en categories.name, se lanza CategoryAlreadyExists."""
    with app.app_context():
        monkeypatch.setattr(db.session, "commit", MagicMock(side_effect=_make_mysql_duplicate_error()))
        with pytest.raises(CategoryAlreadyExists):
            create_category({"name": "Bebidas", "description": "Test"})


def test_create_category_db_non_duplicate_integrity_error_re_raised(app, monkeypatch):
    """Un IntegrityError que no es duplicado de nombre se propaga sin disfrazar."""
    with app.app_context():
        monkeypatch.setattr(db.session, "commit", MagicMock(side_effect=_make_non_duplicate_error()))
        with pytest.raises(IntegrityError):
            create_category({"name": "Bebidas", "description": "Test"})


def test_update_category_db_duplicate_name_raises_category_already_exists(app, monkeypatch):
    """Si el commit de actualización falla con UNIQUE en categories.name, se lanza CategoryAlreadyExists."""
    with app.app_context():
        created = create_category({"name": "Nombre viejo", "description": "Desc vieja"})
        monkeypatch.setattr(db.session, "commit", MagicMock(side_effect=_make_mysql_duplicate_error()))
        with pytest.raises(CategoryAlreadyExists):
            update_category(
                created.id,
                {"name": "Nombre nuevo", "description": "Desc nueva"},
                include_inactive=False,
            )
