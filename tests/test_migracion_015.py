from operator import itemgetter
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from tests.test_pedidos import contexto, pedir


def test_migracion_015_sqlite_preserva_detalles_y_rechaza_downgrade(client, contexto):
    pedido_id = pedir(client, contexto)["id"]
    db.session.remove()
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    config = Config(str(migrations / "alembic.ini"))
    config.set_main_option("script_location", str(migrations))
    revision = "015_add_cancelado_to_pedidos"
    anterior = "014_add_image_filename_to_products"
    assert ScriptDirectory.from_config(config).get_revision(revision).down_revision == anterior
    with db.engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.commit()

    # db.create_all parte del esquema actual. El primer downgrade construye
    # la restricción anterior sin depender de migraciones SQLite previas.
    command.stamp(config, revision)
    command.downgrade(config, anterior)
    cancelar = text("UPDATE pedidos SET estado='CANCELADO' WHERE id=:pedido_id")
    with db.engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        with pytest.raises(IntegrityError):
            conn.execute(cancelar, {"pedido_id": pedido_id})
        conn.rollback()
        esquema = inspect(conn)
        detalle_fk = esquema.get_foreign_keys("detalles_pedido")
        pedido_fk = esquema.get_foreign_keys("pedidos")
        otros_checks = {c["name"]: c["sqltext"] for c in esquema.get_check_constraints("pedidos")
                        if c["name"] != "ck_pedidos_estado"}
        detalles = conn.exec_driver_sql("SELECT * FROM detalles_pedido").all()

    command.upgrade(config, revision)
    with db.engine.begin() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert conn.exec_driver_sql("SELECT * FROM detalles_pedido").all() == detalles
        esquema = inspect(conn)
        assert esquema.get_foreign_keys("detalles_pedido") == detalle_fk
        por_columna = itemgetter("constrained_columns")
        assert sorted(esquema.get_foreign_keys("pedidos"), key=por_columna) == sorted(pedido_fk, key=por_columna)
        assert {c["name"]: c["sqltext"] for c in esquema.get_check_constraints("pedidos")
                if c["name"] != "ck_pedidos_estado"} == otros_checks
        conn.execute(cancelar, {"pedido_id": pedido_id})

    with pytest.raises(RuntimeError, match="mientras existan pedidos CANCELADO"):
        command.downgrade(config, anterior)
    with db.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT estado FROM pedidos").scalar_one() == "CANCELADO"
        assert conn.exec_driver_sql("SELECT * FROM detalles_pedido").all() == detalles
        assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == revision
        # La fixture global borra sus tablas al terminar; restaurar su modo habitual.
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
