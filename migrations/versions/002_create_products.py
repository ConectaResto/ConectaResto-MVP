"""create products table

Revision ID: 002_create_products
Revises: 001_create_categories
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002_create_products"
down_revision = "001_create_categories"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["categoria_id"], ["categories.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("products")
