"""Allow NULL in servicios.abierto_por_id.

Revision ID: 013_allow_null_abierto_por_id
Revises: 012_add_detalle_timestamps
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "013_allow_null_abierto_por_id"
down_revision = "012_add_detalle_timestamps"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "servicios",
        "abierto_por_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade():
    connection = op.get_context().connection
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM servicios WHERE abierto_por_id IS NULL")
    )
    null_count = result.scalar()
    if null_count > 0:
        raise RuntimeError(
            f"No se puede downgradear: {null_count} servicio(s) con abierto_por_id=NULL. "
            "No se puede volver a NOT NULL sin asignar un usuario."
        )
    op.alter_column(
        "servicios",
        "abierto_por_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
