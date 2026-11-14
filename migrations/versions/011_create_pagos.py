"""create pagos table

Revision ID: 011_create_pagos
Revises: 010_create_detalles_pedido
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011_create_pagos"
down_revision = "010_create_detalles_pedido"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pagos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("servicio_id", sa.Integer(), nullable=False),
        sa.Column("registrado_por_id", sa.Integer(), nullable=False),
        sa.Column("importe", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"], ),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usuarios.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id", name="uq_pagos_servicio_id"),
        sa.CheckConstraint("importe > 0", name="ck_pagos_importe_positivo"),
    )


def downgrade():
    op.drop_table("pagos")