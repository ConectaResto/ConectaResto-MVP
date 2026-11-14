"""create mesas table

Revision ID: 007_create_mesas
Revises: 006_create_usuarios
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_create_mesas"
down_revision = "006_create_usuarios"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mesas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default=sa.text("'DISPONIBLE'")),
        sa.Column("public_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero", name="uq_mesas_numero"),
        sa.UniqueConstraint("public_token", name="uq_mesas_public_token"),
        sa.CheckConstraint("numero > 0", name="ck_mesas_numero_positivo"),
        sa.CheckConstraint(
            "estado IN ('DISPONIBLE', 'OCUPADA', 'CERRADA')",
            name="ck_mesas_estado",
        ),
    )


def downgrade():
    op.drop_table("mesas")