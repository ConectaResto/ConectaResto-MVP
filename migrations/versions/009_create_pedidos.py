"""create pedidos table

Revision ID: 009_create_pedidos
Revises: 008_create_servicios
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "009_create_pedidos"
down_revision = "008_create_servicios"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pedidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("servicio_id", sa.Integer(), nullable=False),
        sa.Column("origen", sa.String(length=20), nullable=False),
        sa.Column("creado_por_id", sa.Integer(), nullable=True),
        sa.Column("autorizado_por_id", sa.Integer(), nullable=True),
        sa.Column("autorizado_at", sa.DateTime(), nullable=True),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column(
            "estado_preparacion",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'NO_ENVIADO'"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicios.id"], ),
        sa.ForeignKeyConstraint(["creado_por_id"], ["usuarios.id"], ),
        sa.ForeignKeyConstraint(["autorizado_por_id"], ["usuarios.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'EN_PREPARACION', 'LISTO', 'ENTREGADO')",
            name="ck_pedidos_estado",
        ),
        sa.CheckConstraint(
            "origen IN ('MESERO', 'PUBLICO')",
            name="ck_pedidos_origen",
        ),
        sa.CheckConstraint(
            "estado_preparacion IN ('NO_ENVIADO', 'RECIBIDO', 'EN_COCINA', 'LISTO_PARA_SERVIR')",
            name="ck_pedidos_estado_preparacion",
        ),
    )


def downgrade():
    op.drop_table("pedidos")