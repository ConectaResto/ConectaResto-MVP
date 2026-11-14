"""create detalles_pedido table

Revision ID: 010_create_detalles_pedido
Revises: 009_create_pedidos
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "010_create_detalles_pedido"
down_revision = "009_create_pedidos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "detalles_pedido",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("precio_unitario", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ),
        sa.ForeignKeyConstraint(["producto_id"], ["products.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("detalles_pedido")