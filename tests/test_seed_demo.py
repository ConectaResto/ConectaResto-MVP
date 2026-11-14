import pytest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.mesa import Mesa
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.product import Product
from app.models.rol import Rol
from app.models.servicio import Servicio
from app.models.usuario import Usuario
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
