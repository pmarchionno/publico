"""create payments and transfer tables

Revision ID: 20260102_01
Revises: 
Create Date: 2026-01-02 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260102_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUMs safely using raw SQL with IF NOT EXISTS
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
                CREATE TYPE payment_status AS ENUM ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED');
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transfer_status') THEN
                CREATE TYPE transfer_status AS ENUM ('CREATED', 'REQUIRES_PM', 'REQUIRES_KYC', 'AUTHORIZED', 'CAPTURED', 'FAILED', 'CANCELLED');
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transfer_event_status') THEN
                CREATE TYPE transfer_event_status AS ENUM ('CREATED', 'REQUIRES_PM', 'REQUIRES_KYC', 'AUTHORIZED', 'CAPTURED', 'FAILED', 'CANCELLED');
            END IF;
        END $$;
    """)

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )

    op.create_table(
        "transfers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("origin_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="CREATED"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("concept", sa.String(length=32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("connector_id", sa.String(length=64), nullable=True),
        sa.Column("source_address", sa.String(length=64), nullable=False),
        sa.Column("source_address_type", sa.String(length=32), nullable=False),
        sa.Column("source_owner_id_type", sa.String(length=16), nullable=False),
        sa.Column("source_owner_id", sa.String(length=32), nullable=False),
        sa.Column("source_owner_name", sa.String(length=128), nullable=True),
        sa.Column("destination_address", sa.String(length=64), nullable=False),
        sa.Column("destination_address_type", sa.String(length=32), nullable=False),
        sa.Column("destination_owner_id_type", sa.String(length=16), nullable=False),
        sa.Column("destination_owner_id", sa.String(length=32), nullable=False),
        sa.Column("destination_owner_name", sa.String(length=128), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("connector_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )
    op.create_index("ix_transfers_origin_id", "transfers", ["origin_id"], unique=True)

    op.create_table(
        "transfer_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True,nullable=False),
        sa.Column("transfer_id", sa.BigInteger(), sa.ForeignKey("transfers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )
    op.create_index("ix_transfer_events_transfer_id_created", "transfer_events", ["transfer_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transfer_events_transfer_id_created", table_name="transfer_events")
    op.drop_table("transfer_events")

    op.drop_index("ix_transfers_origin_id", table_name="transfers")
    op.drop_table("transfers")

    op.drop_table("payments")

    # Drop ENUMs safely using raw SQL
    op.execute("DROP TYPE IF EXISTS transfer_event_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS transfer_status CASCADE;")
    op.execute("DROP TYPE IF EXISTS payment_status CASCADE;")
