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
    # Alembic creates version_num as VARCHAR(32), but this revision has
    # 34 characters. Keep its published identifier and widen the tracking
    # column before Alembic records it, including on a fresh installation.
    if conn.dialect.name in {"mysql", "mariadb"}:
        version_column = next(
            col for col in inspector.get_columns("alembic_version")
            if col["name"] == "version_num"
        )
        version_type = version_column["type"]
        if (isinstance(version_type, sa.String)
                and version_type.length is not None
                and version_type.length < len(revision)):
            op.alter_column(
                "alembic_version",
                "version_num",
                type_=sa.String(length=64, collation=version_type.collation),
                existing_type=version_type,
                existing_nullable=version_column["nullable"],
            )

    # MySQL DDL can survive a failed version update. Preserve an image
    # column (and any values) left by an earlier attempt instead of adding it twice.
    existing_columns = [col["name"] for col in inspector.get_columns("products")]

    if "image_filename" not in existing_columns:
        op.add_column(
            "products",
            sa.Column("image_filename", sa.String(length=255), nullable=True),
        )


def downgrade():
    # Keep version_num wide so this published revision remains usable on retry.
    op.drop_column("products", "image_filename")
