"""Add timestamps to detalles_pedido.

Revision ID: 012_add_detalle_timestamps
Revises: 011_create_pagos
"""

from alembic import op
import sqlalchemy as sa


revision = "012_add_detalle_timestamps"
down_revision = "011_create_pagos"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("detalles_pedido", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("detalles_pedido", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # Las líneas se crean junto con el pedido. El esquema anterior no tiene
    # un historial de actualización propio para sus líneas.
    op.execute(
        """
        UPDATE detalles_pedido AS detalle
        JOIN pedidos AS pedido ON pedido.id = detalle.pedido_id
        SET detalle.created_at = pedido.created_at,
            detalle.updated_at = pedido.created_at
        """
    )

    op.alter_column("detalles_pedido", "created_at", existing_type=sa.DateTime(), nullable=False)
    op.alter_column("detalles_pedido", "updated_at", existing_type=sa.DateTime(), nullable=False)


def downgrade():
    op.drop_column("detalles_pedido", "updated_at")
    op.drop_column("detalles_pedido", "created_at")
