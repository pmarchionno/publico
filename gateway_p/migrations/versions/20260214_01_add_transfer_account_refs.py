"""Add transfer account references

Revision ID: 20260214_01
Revises: 20260212_01
Create Date: 2026-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260214_01"
down_revision = "20260212_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transfers",
        sa.Column("source_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "transfers",
        sa.Column("destination_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        "ix_transfers_source_account_id",
        "transfers",
        ["source_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_transfers_destination_account_id",
        "transfers",
        ["destination_account_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_transfers_source_account_id_bank_accounts",
        "transfers",
        "bank_accounts",
        ["source_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transfers_destination_account_id_bank_accounts",
        "transfers",
        "bank_accounts",
        ["destination_account_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transfers_destination_account_id_bank_accounts",
        "transfers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_transfers_source_account_id_bank_accounts",
        "transfers",
        type_="foreignkey",
    )

    op.drop_index("ix_transfers_destination_account_id", table_name="transfers")
    op.drop_index("ix_transfers_source_account_id", table_name="transfers")

    op.drop_column("transfers", "destination_account_id")
    op.drop_column("transfers", "source_account_id")
