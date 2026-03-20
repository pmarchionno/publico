"""Add registration token fields to users

Revision ID: 20260212_01
Revises: 20260210_02
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_01"
down_revision = "20260210_02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("registration_token", sa.String(512), nullable=True))
    op.add_column(
        "users",
        sa.Column("registration_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("users", "registration_token_expires_at")
    op.drop_column("users", "registration_token")
