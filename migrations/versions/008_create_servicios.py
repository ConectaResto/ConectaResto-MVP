"""create servicios table

Revision ID: 008_create_servicios
Revises: 007_create_mesas
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008_create_servicios"
down_revision = "007_create_mesas"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "servicios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mesa_id", sa.Integer(), nullable=False),
        sa.Column("abierto_por_id", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ACTIVO'"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mesa_id"], ["mesas.id"], ),
        sa.ForeignKeyConstraint(["abierto_por_id"], ["usuarios.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "estado IN ('ACTIVO', 'CERRADO')", name="ck_servicios_estado"
        ),
    )
    # Columna generada virtual para índice único parcial (solo estados ACTIVO)
    # MySQL trata NULL como distinto en índices únicos, así que múltiples
    # servicios CERRADO por mesa se permiten, pero solo uno ACTIVO por mesa.
    op.execute(
        "ALTER TABLE servicios "
        "ADD COLUMN estado_activo TINYINT(1) "
        "GENERATED ALWAYS AS (CASE WHEN estado='ACTIVO' THEN 1 ELSE NULL END) VIRTUAL"
    )
    op.create_unique_constraint(
        "uq_servicios_una_activa_por_mesa",
        "servicios",
        ["mesa_id", "estado_activo"],
    )


def downgrade():
    op.drop_constraint(
        "uq_servicios_una_activa_por_mesa", "servicios", type_="unique"
    )
    op.drop_table("servicios")