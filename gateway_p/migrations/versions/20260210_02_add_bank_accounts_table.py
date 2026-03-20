"""Add bank accounts table

Revision ID: 20260210_02
Revises: 20260210_01
Create Date: 2026-02-10 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260210_02'
down_revision = '20260210_01'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla de cuentas bancarias
    op.create_table(
        'bank_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cvu_cbu', sa.String(22), nullable=False,
                  comment='CVU o CBU de 22 dígitos'),
        sa.Column('account_type', sa.String(16), nullable=False,
                  comment='Tipo de cuenta: CBU, CVU'),
        sa.Column('alias', sa.String(64), nullable=True,
                  comment='Alias de la cuenta (ej: alias.ejemplo.cuenta)'),
        sa.Column('status', sa.String(16), nullable=False, server_default='active',
                  comment='Estado: active, suspended, closed'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false(),
                  comment='Indica si es la cuenta principal del usuario'),
        sa.Column('bdc_account_id', sa.String(64), nullable=True,
                  comment='ID de la cuenta en el sistema BDC'),
        sa.Column('currency', sa.String(8), nullable=False, server_default='ARS',
                  comment='Moneda de la cuenta: ARS, USD'),
        sa.Column('balance', sa.Numeric(18, 2), nullable=True,
                  comment='Saldo actual (si se sincroniza)'),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}',
                  comment='Metadatos adicionales'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('cvu_cbu', name='uq_bank_accounts_cvu_cbu')
    )

    # Crear índices
    op.create_index('idx_bank_account_user', 'bank_accounts', ['user_id'])
    op.create_index('idx_bank_account_status', 'bank_accounts', ['status'])
    op.create_index('idx_bank_account_user_primary', 'bank_accounts', ['user_id', 'is_primary'])


def downgrade():
    # Eliminar índices
    op.drop_index('idx_bank_account_user_primary', table_name='bank_accounts')
    op.drop_index('idx_bank_account_status', table_name='bank_accounts')
    op.drop_index('idx_bank_account_user', table_name='bank_accounts')
    
    # Eliminar tabla
    op.drop_table('bank_accounts')
