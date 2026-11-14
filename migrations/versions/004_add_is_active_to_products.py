"""add is_active and rename disponible to is_available on products

Revision ID: 004_add_is_active_to_products
Revises: 003_add_unique_categories_name
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_add_is_active_to_products"
down_revision = "003_add_unique_categories_name"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.alter_column("products", "disponible", new_column_name="is_available")


def downgrade():
    op.alter_column("products", "is_available", new_column_name="disponible")
    op.drop_column("products", "is_active")
