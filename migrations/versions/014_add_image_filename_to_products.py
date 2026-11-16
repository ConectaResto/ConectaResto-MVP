"""add image_filename to products

Revision ID: 014_add_image_filename_to_products
Revises: 013_allow_null_abierto_por_id
Create Date: 2026-11-15 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "014_add_image_filename_to_products"
down_revision = "013_allow_null_abierto_por_id"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col["name"] for col in inspector.get_columns("products")]

    if "image_filename" not in existing_columns:
        op.add_column(
            "products",
            sa.Column("image_filename", sa.String(length=255), nullable=True),
        )


def downgrade():
    op.drop_column("products", "image_filename")
