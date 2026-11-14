"""create usuarios table

Revision ID: 006_create_usuarios
Revises: 005_create_roles
Create Date: 2026-11-14 ...

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_create_usuarios"
down_revision = "005_create_roles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_usuarios_username"),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )


def downgrade():
    op.drop_table("usuarios")