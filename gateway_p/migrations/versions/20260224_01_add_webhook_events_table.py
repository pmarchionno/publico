"""Add webhook events table for idempotency

Revision ID: 20260224_01
Revises: c16fca9dbced
Create Date: 2026-02-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260224_01"
down_revision = "c16fca9dbced"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="didit"),
        sa.Column("webhook_type", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("vendor_data", sa.String(length=255), nullable=True),
        sa.Column("event_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_webhook_events_event_id"),
    )
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"], unique=True)
    op.create_index("ix_webhook_events_session_id", "webhook_events", ["session_id"], unique=False)
    op.create_index("ix_webhook_events_webhook_type", "webhook_events", ["webhook_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_events_webhook_type", table_name="webhook_events")
    op.drop_index("ix_webhook_events_session_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_event_id", table_name="webhook_events")
    op.drop_table("webhook_events")
