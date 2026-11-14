"""add unique constraint to categories.name

Revision ID: 003_add_unique_categories_name
Revises: 002_create_products
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_unique_categories_name"
down_revision = "002_create_products"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_categories_name", "categories", ["name"]
    )


def downgrade():
    op.drop_constraint("uq_categories_name", "categories", type_="unique")
