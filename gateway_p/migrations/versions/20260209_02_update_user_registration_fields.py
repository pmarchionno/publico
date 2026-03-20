"""Add email verification and profile fields

Revision ID: 20260209_02
Revises: 20260209_01
Create Date: 2026-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260209_02"
down_revision = "20260209_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("first_name", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("dni", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(16), nullable=True))
    op.add_column("users", sa.Column("cuit_cuil", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("nationality", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("occupation", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("marital_status", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("location", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.alter_column("users", "full_name", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "password", existing_type=sa.String(255), nullable=True)


def downgrade():
    op.alter_column("users", "password", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "full_name", existing_type=sa.String(255), nullable=False)

    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "location")
    op.drop_column("users", "marital_status")
    op.drop_column("users", "occupation")
    op.drop_column("users", "nationality")
    op.drop_column("users", "phone")
    op.drop_column("users", "cuit_cuil")
    op.drop_column("users", "gender")
    op.drop_column("users", "dni")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
