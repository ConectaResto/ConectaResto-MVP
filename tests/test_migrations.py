import os
import re

import pytest
from app.extensions import db
from app.models.base import BaseModel
from app.catalog.models import Category, Product
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.servicios.models import Pago, Servicio
from app.users.models import Rol, Usuario


# ---------------------------------------------------------------------------
# Pruebas de estructura de migraciones
# ---------------------------------------------------------------------------

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "migrations", "versions"
)


def _list_migration_files():
    """Return sorted list of migration revision IDs found in versions/."""
    files = []
    for fname in os.listdir(MIGRATIONS_DIR):
        if fname.endswith(".py") and fname != "__init__.py":
            m = re.match(r"^(\d+)_.*\.py$", fname)
            if m:
                files.append((int(m.group(1)), fname))
    return sorted(files, key=lambda x: x[0])


def test_migration_files_exist_and_are_sequential():
    """Cada archivo de migración tiene un número secuencial sin gaps."""
    files = _list_migration_files()
    assert len(files) > 0, "No se encontraron archivos de migración"
    for i, (num, _fname) in enumerate(files, start=1):
        assert num == i, f"Se esperaba migración {i}, se encontró {num}"


def test_migration_down_revision_chain_is_consistent():
    """El campo down_revision de cada migración apunta a la anterior."""
    files = _list_migration_files()
    previous_revision = None
    for num, fname in files:
        filepath = os.path.join(MIGRATIONS_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()
        m = re.search(r'down_revision\s*=\s*["\']([^"\']*)["\']', content)
        if num == 1:
            assert m is None or m.group(1) == "None", (
                f"La primera migración ({fname}) debe tener down_revision=None"
            )
        else:
            assert m is not None, (
                f"La migración {fname} no tiene down_revision definido"
            )
            assert m.group(1) == previous_revision, (
                f"La migración {fname} tiene down_revision={m.group(1)}, "
                f"se esperaba {previous_revision}"
            )
        # Extraer el revision id para usar como previous en la siguiente iteración
        m2 = re.search(r'revision\s*=\s*["\']([^"\']*)["\']', content)
        assert m2 is not None, f"La migración {fname} no tiene revision definido"
        previous_revision = m2.group(1)


# ---------------------------------------------------------------------------
# Pruebas de modelos y tablas
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "roles": Rol,
    "usuarios": Usuario,
    "categories": Category,
    "products": Product,
    "mesas": Mesa,
    "servicios": Servicio,
    "pedidos": Pedido,
    "detalles_pedido": DetallePedido,
    "pagos": Pago,
}


def test_all_models_inherit_from_base_model():
    """Todos los modelos heredan de BaseModel."""
    for table_name, model_class in EXPECTED_TABLES.items():
        assert issubclass(model_class, BaseModel), (
            f"{model_class.__name__} no hereda de BaseModel"
        )


def test_model_table_names_match_expected():
    """Cada modelo tiene el __tablename__ esperado."""
    for table_name, model_class in EXPECTED_TABLES.items():
        assert model_class.__tablename__ == table_name, (
            f"{model_class.__name__}.__tablename__ es {model_class.__tablename__}, "
            f"se esperaba {table_name}"
        )


def test_models_are_registered_in_alembic_metadata(app):
    """Alembic comparte los metadatos de todos los modelos de dominio."""
    metadata = app.extensions["migrate"].db.metadata
    assert set(metadata.tables) == set(EXPECTED_TABLES)
    for table_name, model_class in EXPECTED_TABLES.items():
        assert metadata.tables[table_name] is model_class.__table__


def test_all_models_have_id_created_at_updated_at(app):
    """Todos los modelos tienen id, created_at y updated_at de BaseModel."""
    with app.app_context():
        from app.extensions import db

        for table_name, model_class in EXPECTED_TABLES.items():
            # Verificar columnas en el modelo
            columns = {c.name for c in model_class.__table__.columns}
            assert "id" in columns, f"{model_class.__name__} no tiene columna id"
            assert "created_at" in columns, (
                f"{model_class.__name__} no tiene columna created_at"
            )
            assert "updated_at" in columns, (
                f"{model_class.__name__} no tiene columna updated_at"
            )



def test_rol_model_fields(app):
    """El modelo Rol tiene los campos esperados."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Rol.__table__.columns}
        assert "name" in columns
        assert "description" in columns

        rol = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol)
        db.session.commit()
        assert rol.id is not None
        assert rol.name == "ADMIN"
        assert rol.description == "Administrador"
        db.session.delete(rol)
        db.session.commit()


def test_usuario_model_fields(app):
    """El modelo Usuario tiene los campos esperados."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Usuario.__table__.columns}
        assert "username" in columns
        assert "email" in columns
        assert "password_hash" in columns
        assert "rol_id" in columns
        assert "is_active" in columns

        # Crear rol primero (FK requerida)
        rol = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="testuser",
            email="test@example.com",
            rol_id=rol.id,
        )
        usuario.set_password("ClaveSegura123")
        db.session.add(usuario)
        db.session.commit()
        assert usuario.id is not None
        assert usuario.username == "testuser"
        assert usuario.check_password("ClaveSegura123") is True
        assert usuario.check_password("Incorrecta") is False
        assert usuario.is_active is True

        db.session.delete(usuario)
        db.session.delete(rol)
        db.session.commit()


def test_category_model_fields(app):
    """El modelo Category tiene los campos esperados."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Category.__table__.columns}
        assert "name" in columns
        assert "description" in columns
        assert "is_active" in columns

        cat = Category(name="Bebidas", description="Bebidas variadas")
        db.session.add(cat)
        db.session.commit()
        assert cat.id is not None
        d = cat.to_dict()
        assert d["name"] == "Bebidas"
        assert d["is_active"] is True
        db.session.delete(cat)
        db.session.commit()


def test_product_model_fields(app):
    """El modelo Product tiene los campos esperados."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Product.__table__.columns}
        assert "name" in columns
        assert "description" in columns
        assert "price" in columns
        assert "categoria_id" in columns
        assert "is_active" in columns
        assert "is_available" in columns

        # Crear categoría primero (FK requerida)
        cat = Category(name="Bebidas", description="Bebidas")
        db.session.add(cat)
        db.session.commit()

        prod = Product(
            name="Coca Cola",
            description="Refresco de cola",
            price=25.50,
            categoria_id=cat.id,
        )
        db.session.add(prod)
        db.session.commit()
        assert prod.id is not None
        d = prod.to_dict()
        assert d["name"] == "Coca Cola"
        assert d["price"] == "25.50"
        assert d["categoria_id"] == cat.id
        db.session.delete(prod)
        db.session.delete(cat)
        db.session.commit()


def test_mesa_model_fields(app):
    """El modelo Mesa tiene los campos esperados."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Mesa.__table__.columns}
        assert "numero" in columns
        assert "estado" in columns
        assert "public_token" in columns

        mesa = Mesa(numero=1, estado="DISPONIBLE")
        db.session.add(mesa)
        db.session.commit()
        assert mesa.id is not None
        assert mesa.numero == 1
        assert mesa.estado == "DISPONIBLE"
        assert mesa.public_token is not None
        assert len(mesa.public_token) == 64  # 32 bytes -> 64 hex chars
        db.session.delete(mesa)
        db.session.commit()


# ---------------------------------------------------------------------------
# Pruebas de modelos nuevos (servicios, pedidos, detalles_pedido)
# ---------------------------------------------------------------------------

def test_servicio_model_fields(app):
    """El modelo Servicio tiene los campos esperados y relación con mesa/usuario."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Servicio.__table__.columns}
        assert "mesa_id" in columns
        assert "abierto_por_id" in columns
        assert "estado" in columns

        # Crear prerequisitos: mesa y usuario
        mesa = Mesa(numero=5, estado="DISPONIBLE")
        db.session.add(mesa)
        db.session.commit()

        rol = Rol(name="WAITER", description="Mesero")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="mesero1",
            email="mesero1@example.com",
            rol_id=rol.id,
        )
        usuario.set_password("Clave123")
        db.session.add(usuario)
        db.session.commit()

        servicio = Servicio(
            mesa_id=mesa.id,
            abierto_por_id=usuario.id,
            estado="ACTIVO",
        )
        db.session.add(servicio)
        db.session.commit()
        assert servicio.id is not None
        assert servicio.mesa_id == mesa.id
        assert servicio.abierto_por_id == usuario.id
        assert servicio.estado == "ACTIVO"
        assert servicio.mesa is not None
        assert servicio.mesa.numero == 5
        assert servicio.abierto_por is not None
        assert servicio.abierto_por.username == "mesero1"

        # Cambiar a CERRADO
        servicio.estado = "CERRADO"
        db.session.commit()
        assert servicio.estado == "CERRADO"

        db.session.delete(servicio)
        db.session.delete(usuario)
        db.session.delete(rol)
        db.session.delete(mesa)
        db.session.commit()


def test_servicios_migracion_tiene_constraint_unica_activa_por_mesa():
    """La migración 008 crea índice único parcial (mesa_id, estado_activo)."""
    import os
    import re

    migrations_dir = os.path.join(
        os.path.dirname(__file__), "..", "migrations", "versions"
    )
    filepath = os.path.join(migrations_dir, "008_create_servicios.py")
    assert os.path.exists(filepath), "No existe la migración 008_create_servicios"

    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Verificar que la migración crea la tabla servicios
    assert "op.create_table(" in content
    assert '"servicios"' in content
    # Verificar que crea columna generada para índice único parcial
    assert "GENERATED ALWAYS AS" in content
    assert "estado_activo" in content
    # Verificar unique constraint
    assert "uq_servicios_una_activa_por_mesa" in content
    assert "estado_activo" in content
    # Verificar CheckConstraint de estados
    assert "ACTIVO" in content
    assert "CERRADO" in content


def test_pedido_model_fields(app):
    """El modelo Pedido tiene los campos esperados y relaciones."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in Pedido.__table__.columns}
        assert "servicio_id" in columns
        assert "origen" in columns
        assert "creado_por_id" in columns
        assert "autorizado_por_id" in columns
        assert "autorizado_at" in columns
        assert "estado" in columns
        assert "estado_preparacion" in columns

        # Crear prerequisitos
        mesa = Mesa(numero=7, estado="DISPONIBLE")
        db.session.add(mesa)
        db.session.commit()

        rol = Rol(name="WAITER", description="Mesero")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="mesero3",
            email="mesero3@example.com",
            rol_id=rol.id,
        )
        usuario.set_password("Clave123")
        db.session.add(usuario)
        db.session.commit()

        servicio = Servicio(
            mesa_id=mesa.id, abierto_por_id=usuario.id, estado="ACTIVO"
        )
        db.session.add(servicio)
        db.session.commit()

        pedido = Pedido(
            servicio_id=servicio.id,
            origen="MESERO",
            creado_por_id=usuario.id,
            estado="PENDIENTE",
            estado_preparacion="NO_ENVIADO",
        )
        db.session.add(pedido)
        db.session.commit()
        assert pedido.id is not None
        assert pedido.servicio_id == servicio.id
        assert pedido.origen == "MESERO"
        assert pedido.creado_por_id == usuario.id
        assert pedido.autorizado_por_id is None
        assert pedido.autorizado_at is None
        assert pedido.estado == "PENDIENTE"
        assert pedido.estado_preparacion == "NO_ENVIADO"
        assert pedido.servicio is not None
        assert pedido.servicio.mesa_id == mesa.id

        # Autorizar el pedido
        pedido.autorizado_por_id = usuario.id
        from datetime import datetime, timezone
        pedido.autorizado_at = datetime.now(timezone.utc)
        pedido.estado = "EN_PREPARACION"
        pedido.estado_preparacion = "RECIBIDO"
        db.session.commit()
        assert pedido.estado == "EN_PREPARACION"
        assert pedido.estado_preparacion == "RECIBIDO"
        assert pedido.autorizado_por_id is not None
        assert pedido.autorizado_at is not None

        db.session.delete(pedido)
        db.session.delete(servicio)
        db.session.delete(usuario)
        db.session.delete(rol)
        db.session.delete(mesa)
        db.session.commit()


def test_pedido_origen_publico(app):
    """Un pedido puede tener origen PUBLICO sin creado_por."""
    with app.app_context():
        from app.extensions import db

        mesa = Mesa(numero=8, estado="DISPONIBLE")
        db.session.add(mesa)
        db.session.commit()

        rol = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="admin1",
            email="admin1@example.com",
            rol_id=rol.id,
        )
        usuario.set_password("Clave123")
        db.session.add(usuario)
        db.session.commit()

        servicio = Servicio(
            mesa_id=mesa.id, abierto_por_id=usuario.id, estado="ACTIVO"
        )
        db.session.add(servicio)
        db.session.commit()

        pedido = Pedido(
            servicio_id=servicio.id,
            origen="PUBLICO",
            creado_por_id=None,
            estado="PENDIENTE",
            estado_preparacion="NO_ENVIADO",
        )
        db.session.add(pedido)
        db.session.commit()
        assert pedido.origen == "PUBLICO"
        assert pedido.creado_por_id is None

        db.session.delete(pedido)
        db.session.delete(servicio)
        db.session.delete(usuario)
        db.session.delete(rol)
        db.session.delete(mesa)
        db.session.commit()


def test_detalle_pedido_model_fields(app):
    """El modelo DetallePedido tiene los campos esperados y relaciones."""
    with app.app_context():
        from app.extensions import db

        columns = {c.name for c in DetallePedido.__table__.columns}
        assert "pedido_id" in columns
        assert "producto_id" in columns
        assert "cantidad" in columns
        assert "precio_unitario" in columns

        # Crear prerequisitos: categoria, producto, mesa, usuario, servicio, pedido
        cat = Category(name="Bebidas", description="Bebidas")
        db.session.add(cat)
        db.session.commit()

        producto = Product(
            name="Agua",
            description="Agua mineral",
            price=15.00,
            categoria_id=cat.id,
        )
        db.session.add(producto)
        db.session.commit()

        mesa = Mesa(numero=3, estado="DISPONIBLE")
        db.session.add(mesa)
        db.session.commit()

        rol = Rol(name="WAITER", description="Mesero")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="mesero4",
            email="mesero4@example.com",
            rol_id=rol.id,
        )
        usuario.set_password("Clave123")
        db.session.add(usuario)
        db.session.commit()

        servicio = Servicio(
            mesa_id=mesa.id, abierto_por_id=usuario.id, estado="ACTIVO"
        )
        db.session.add(servicio)
        db.session.commit()

        pedido = Pedido(
            servicio_id=servicio.id,
            origen="MESERO",
            creado_por_id=usuario.id,
            estado="PENDIENTE",
            estado_preparacion="NO_ENVIADO",
        )
        db.session.add(pedido)
        db.session.commit()

        detalle = DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto.id,
            cantidad=2,
            precio_unitario=15.00,
        )
        db.session.add(detalle)
        db.session.commit()
        assert detalle.id is not None
        assert detalle.pedido_id == pedido.id
        assert detalle.producto_id == producto.id
        assert detalle.cantidad == 2
        assert detalle.precio_unitario == 15.00
        assert detalle.pedido is not None
        assert detalle.pedido.id == pedido.id
        assert detalle.producto is not None
        assert detalle.producto.name == "Agua"

        db.session.delete(detalle)
        db.session.delete(pedido)
        db.session.delete(servicio)
        db.session.delete(usuario)
        db.session.delete(rol)
        db.session.delete(mesa)
        db.session.delete(producto)
        db.session.delete(cat)
        db.session.commit()

# Regression: revision 014 exceeds Alembic's default VARCHAR(32).
@pytest.mark.parametrize("dialect", ["mysql", "mariadb"])
@pytest.mark.parametrize("version_length", [32, 64, 128])
def test_image_migration_widens_version_before_mysql_version_update(
    dialect, version_length, monkeypatch,
):
    import importlib.util
    import io
    import sqlalchemy as sa
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory

    path = os.path.join(MIGRATIONS_DIR, "014_add_image_filename_to_products.py")
    spec = importlib.util.spec_from_file_location("image_revision_sql", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.revision) == 34

    class Inspector:
        def get_columns(self, table):
            if table == "alembic_version":
                return [{"name": "version_num", "type": sa.String(version_length, collation="utf8mb4_unicode_ci"),
                         "nullable": False}]
            assert table == "products"
            return [{"name": "id"}]

    monkeypatch.setattr(module.sa, "inspect", lambda connection: Inspector())
    output = io.StringIO()
    config = Config()
    config.set_main_option("script_location", os.path.dirname(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)
    migration = MigrationContext.configure(
        dialect_name=dialect,
        opts={"as_sql": True, "output_buffer": output,
              "starting_rev": module.down_revision,
              "fn": lambda heads, context: script._upgrade_revs("head", heads)},
    )
    # ScriptDirectory loads the actual revision module separately; run the
    # same approved upgrade through its revision step with inspection mocked.
    step = script.get_revision("head")
    monkeypatch.setattr(step.module, "upgrade", module.upgrade)
    with Operations.context(migration), migration.begin_transaction():
        migration.run_migrations()
    sql = output.getvalue()
    assert "UPDATE alembic_version" in sql
    assert module.revision in sql
    assert "ADD COLUMN image_filename VARCHAR(255)" in sql
    if version_length == 32:
        assert "MODIFY version_num VARCHAR(64) COLLATE utf8mb4_unicode_ci NOT NULL" in sql
        assert sql.index("MODIFY version_num") < sql.index("UPDATE alembic_version")
    else:
        assert "MODIFY version_num" not in sql


@pytest.mark.parametrize("partial_upgrade", [False, True])
def test_image_migration_retry_preserves_products_and_revision_chain(partial_upgrade):
    import sqlalchemy as sa
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory

    config = Config()
    config.set_main_option("script_location", os.path.dirname(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)
    revision = script.get_revision("head")
    assert revision.revision == "014_add_image_filename_to_products"
    assert revision.down_revision == "013_allow_null_abierto_por_id"
    metadata = sa.MetaData()
    columns = [sa.Column("id", sa.Integer, primary_key=True),
               sa.Column("name", sa.String(100), nullable=False)]
    if partial_upgrade:
        columns.append(sa.Column("image_filename", sa.String(255), nullable=True))
    products = sa.Table("products", metadata, *columns)
    versions = sa.Table("alembic_version", metadata,
                        sa.Column("version_num", sa.String(32), primary_key=True))
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            metadata.create_all(connection)
            values = {"id": 1, "name": "Producto previo"}
            if partial_upgrade:
                values["image_filename"] = "existing.png"
            connection.execute(products.insert(), values)
            connection.execute(versions.insert(), {"version_num": revision.down_revision})
            context = MigrationContext.configure(
                connection,
                opts={"fn": lambda heads, context: script._upgrade_revs("head", heads)},
            )
            with Operations.context(context):
                context.run_migrations()
            assert context.get_current_revision() == revision.revision
            assert connection.execute(sa.text(
                "SELECT name, image_filename FROM products WHERE id=1"
            )).one() == ("Producto previo", "existing.png" if partial_upgrade else None)
            # Repeating upgrade at head must not repeat DDL or lose existing data.
            with Operations.context(context):
                context.run_migrations()
            assert len(sa.inspect(connection).get_columns("products")) == 3
            context = MigrationContext.configure(
                connection,
                opts={"fn": lambda heads, context: script._downgrade_revs(
                    revision.down_revision, heads)},
            )
            with Operations.context(context):
                context.run_migrations()
            assert context.get_current_revision() == revision.down_revision
            assert connection.execute(sa.text("SELECT name FROM products")).scalar_one() == "Producto previo"
            assert "image_filename" not in {
                col["name"] for col in sa.inspect(connection).get_columns("products")
            }
    finally:
        engine.dispose()
