"""Allow terminal CANCELADO orders."""

from alembic import op
import sqlalchemy as sa


revision = "015_add_cancelado_to_pedidos"
down_revision = "014_add_image_filename_to_products"
branch_labels = None
depends_on = None

CONSTRAINT = "ck_pedidos_estado"
ESTADOS_ANTERIORES = "estado IN ('PENDIENTE', 'EN_PREPARACION', 'LISTO', 'ENTREGADO')"
ESTADOS_NUEVOS = "estado IN ('PENDIENTE', 'EN_PREPARACION', 'LISTO', 'ENTREGADO', 'CANCELADO')"


def _reemplazar_constraint(condicion):
    conn = op.get_bind()
    dialecto = conn.dialect.name
    if dialecto in {"mysql", "mariadb"}:
        drop = "DROP CHECK" if dialecto == "mysql" else "DROP CONSTRAINT"
        op.execute(
            f"ALTER TABLE pedidos {drop} {CONSTRAINT}, "
            f"ADD CONSTRAINT {CONSTRAINT} CHECK ({condicion})"
        )
        return

    if dialecto != "sqlite":
        op.drop_constraint(CONSTRAINT, "pedidos", type_="check")
        op.create_check_constraint(CONSTRAINT, "pedidos", condicion)
        return

    # SQLite reconstruye pedidos. Desactivar las FKs fuera de la transacción
    # permite reemplazar la tabla padre sin modificar detalles_pedido.
    with op.get_context().autocommit_block():
        foreign_keys = conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                with op.batch_alter_table("pedidos", recreate="always") as batch:
                    batch.drop_constraint(CONSTRAINT, type_="check")
                    batch.create_check_constraint(CONSTRAINT, condicion)
                if foreign_keys and conn.exec_driver_sql(
                    "PRAGMA foreign_key_check('detalles_pedido')"
                ).first() is not None:
                    raise RuntimeError("La reconstrucción de pedidos dejaría detalles sin referencia")
                conn.exec_driver_sql("COMMIT")
            except Exception:
                conn.exec_driver_sql("ROLLBACK")
                raise
        finally:
            if foreign_keys:
                conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def upgrade():
    _reemplazar_constraint(ESTADOS_NUEVOS)


def downgrade():
    cancelado = op.get_bind().execute(sa.text(
        "SELECT 1 FROM pedidos WHERE estado = 'CANCELADO' LIMIT 1"
    )).first()
    if cancelado is not None:
        raise RuntimeError("No se puede revertir 015 mientras existan pedidos CANCELADO")
    _reemplazar_constraint(ESTADOS_ANTERIORES)
