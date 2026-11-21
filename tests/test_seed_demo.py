import os

import pytest
from click.testing import CliRunner
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.catalog.models import Category, Product
from app.mesas.models import Mesa
from app.pedidos.models import Pedido
from app.servicios.models import Pago, Servicio
from app.users.models import Rol, Usuario
from app.users.cli import seed_demo_cmd
from app.users.service import seed_demo


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_seed_crea_roles_usuarios_mesas_categorias_productos(app):
    """seed-demo crea roles, usuarios, mesas, categorías y productos con precios positivos."""
    with app.app_context():
        seed_demo(password="DemoPass123!")

        # Roles
        roles = db.session.execute(db.select(Rol)).scalars().all()
        role_names = {r.name for r in roles}
        assert {"ADMIN", "WAITER", "KITCHEN", "CASHIER"} <= role_names

        # Usuarios operativos
        usuarios = db.session.execute(db.select(Usuario)).scalars().all()
        usernames = {u.username for u in usuarios}
        assert {"mesero1", "cajero1", "cocinero1", "admin1"} <= usernames

        # Mesas
        mesas = db.session.execute(db.select(Mesa)).scalars().all()
        numeros = {m.numero for m in mesas}
        assert {1, 2, 3, 4, 5} <= numeros
        for m in mesas:
            assert m.estado == "DISPONIBLE"

        # Categorías
        categorias = db.session.execute(db.select(Category)).scalars().all()
        cat_names = {c.name for c in categorias}
        assert {"Bebidas", "Comidas", "Postres"} <= cat_names

        # Productos con precios positivos
        productos = db.session.execute(db.select(Product)).scalars().all()
        assert len(productos) > 0
        for p in productos:
            assert p.price is not None
            assert p.price > 0
            assert p.is_active is True
            assert p.is_available is True


def test_seed_es_idempotente(app):
    """Ejecutar seed-demo dos veces no duplica registros."""
    with app.app_context():
        seed_demo(password="DemoPass123!")
        seed_demo(password="DemoPass123!")

        # Roles: exactamente 4
        roles = db.session.execute(db.select(Rol)).scalars().all()
        assert len(roles) == 4

        # Usuarios operativos: exactamente 4
        usuarios = db.session.execute(db.select(Usuario)).scalars().all()
        assert len(usuarios) == 4

        # Mesas: exactamente 5
        mesas = db.session.execute(db.select(Mesa)).scalars().all()
        assert len(mesas) == 5

        # Categorías: exactamente 3
        categorias = db.session.execute(db.select(Category)).scalars().all()
        assert len(categorias) == 3

        # Productos: exactamente 8
        productos = db.session.execute(db.select(Product)).scalars().all()
        assert len(productos) == 8


def test_productos_tienen_precio_positivo(app):
    """Todos los productos creados por seed tienen precio > 0."""
    with app.app_context():
        seed_demo(password="DemoPass123!")

        productos = db.session.execute(db.select(Product)).scalars().all()
        assert len(productos) > 0
        for p in productos:
            assert p.price > 0


def test_usuarios_tienen_roles_asignados(app):
    """Cada usuario operativo tiene su rol correspondiente."""
    with app.app_context():
        seed_demo(password="DemoPass123!")

        mesero = db.session.execute(
            db.select(Usuario).filter_by(username="mesero1")
        ).scalar_one_or_none()
        assert mesero is not None
        assert mesero.rol.name == "WAITER"

        cajero = db.session.execute(
            db.select(Usuario).filter_by(username="cajero1")
        ).scalar_one_or_none()
        assert cajero is not None
        assert cajero.rol.name == "CASHIER"

        cocinero = db.session.execute(
            db.select(Usuario).filter_by(username="cocinero1")
        ).scalar_one_or_none()
        assert cocinero is not None
        assert cocinero.rol.name == "KITCHEN"

        admin = db.session.execute(
            db.select(Usuario).filter_by(username="admin1")
        ).scalar_one_or_none()
        assert admin is not None
        assert admin.rol.name == "ADMIN"


def test_seed_no_duplica_usuarios_existentes(app):
    """Ejecutar seed sobre usuarios existentes no los duplica ni modifica."""
    with app.app_context():
        # Crear un usuario manualmente antes del seed
        rol_admin = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol_admin)
        db.session.commit()

        existing = Usuario(
            username="admin1",
            email="existing@test.com",
            rol_id=rol_admin.id,
        )
        existing.set_password("existing-password")
        db.session.add(existing)
        db.session.commit()

        # Ejecutar seed
        seed_demo(password="DemoPass123!")

        # Verificar que el usuario existente no se duplicó
        usuarios_admin1 = db.session.execute(
            db.select(Usuario).filter_by(username="admin1")
        ).scalars().all()
        assert len(usuarios_admin1) == 1
        assert usuarios_admin1[0].email == "existing@test.com"


def test_seed_rechaza_entorno_produccion(app, monkeypatch):
    """seed-demo rechaza ejecutarse cuando FLASK_ENV=production."""
    monkeypatch.setenv("FLASK_ENV", "production")
    runner = app.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="y\n")
    assert result.exit_code != 0
    assert "producción" in result.output
    # Verificar que no se crearon roles
    with app.app_context():
        assert db.session.execute(db.select(Rol)).scalars().all() == []


def test_seed_muestra_info_bd(app):
    """seed-demo muestra nombre de BD y motor antes de pedir confirmación."""
    runner = app.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="n\n")
    assert "Base de datos:" in result.output
    assert "Motor:" in result.output


def test_seed_no_muestra_credenciales(app, monkeypatch):
    """seed-demo no muestra la contraseña de la URI de base de datos."""
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:secret123@localhost:3306/conecta_resto")
    app_test = create_app("testing")
    runner = app_test.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="n\n")
    assert "secret123" not in result.output
    assert "root:" not in result.output


def test_seed_requiere_confirmacion(app):
    """seed-demo cancela cuando el usuario no confirma."""
    runner = app.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="n\n")
    assert result.exit_code == 0
    assert "Operación cancelada" in result.output
    # Verificar que no se crearon datos
    with app.app_context():
        assert db.session.execute(db.select(Rol)).scalars().all() == []


def test_seed_rechaza_entorno_produccion(app, monkeypatch):
    """seed-demo rechaza ejecutarse cuando FLASK_ENV=production."""
    monkeypatch.setenv("FLASK_ENV", "production")
    runner = app.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="y\n")
    assert result.exit_code != 0
    assert "producción" in result.output
    # Verificar que no se crearon roles
    with app.app_context():
        assert db.session.execute(db.select(Rol)).scalars().all() == []


def test_seed_muestra_info_bd(app):
    """seed-demo muestra nombre de BD y motor antes de pedir confirmación."""
    runner = app.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="n\n")
    assert "Base de datos:" in result.output
    assert "Motor:" in result.output


def test_seed_no_muestra_credenciales(app, monkeypatch):
    """seed-demo no muestra la contraseña de la URI de base de datos."""
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:secret123@localhost:3306/conecta_resto")
    # Recrear app con la nueva URI
    app_test = create_app("testing")
    runner = app_test.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="n\n")
    assert "secret123" not in result.output
    assert "root:" not in result.output


def test_seed_requiere_confirmacion(app):
    """seed-demo cancela cuando el usuario no confirma."""
    runner = app.test_cli_runner()
    result = runner.invoke(seed_demo_cmd, ["--password", "TestPass123!"], input="n\n")
    assert result.exit_code == 0
    assert "Operación cancelada" in result.output
    # Verificar que no se crearon datos
    with app.app_context():
        assert db.session.execute(db.select(Rol)).scalars().all() == []
