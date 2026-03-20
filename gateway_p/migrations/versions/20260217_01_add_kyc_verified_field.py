"""Add KYC verification field to users

Revision ID: 20260217_01
Revises: 20260214_01
Create Date: 2026-02-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260217_01"
down_revision = "20260214_01"
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add is_kyc_verified field to users table"""
    op.add_column(
        "users",
        sa.Column(
            "is_kyc_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    
    # Create index for faster queries filtering by KYC status
    op.create_index(
        "idx_user_is_kyc_verified",
        "users",
        ["is_kyc_verified"],
        unique=False,
    )


def downgrade() -> None:
    """Remove is_kyc_verified field from users table"""
    op.drop_index("idx_user_is_kyc_verified", table_name="users")
    op.drop_column("users", "is_kyc_verified")
