"""add_origin_id_to_bank_accounts

Revision ID: c16fca9dbced
Revises: 20260217_01
Create Date: 2026-02-21 18:07:06.703923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c16fca9dbced'
down_revision: Union[str, None] = '20260217_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna origin_id como nullable primero
    op.add_column('bank_accounts', sa.Column('origin_id', sa.Integer(), autoincrement=True, nullable=True, comment='ID numérico autoincremental para integración con BDC'))
    
    # Crear secuencia para el autoincremento
    op.execute("CREATE SEQUENCE IF NOT EXISTS bank_accounts_origin_id_seq")
    
    # Asignar valores a las filas existentes usando la secuencia
    op.execute("""
        UPDATE bank_accounts 
        SET origin_id = nextval('bank_accounts_origin_id_seq')
        WHERE origin_id IS NULL
    """)
    
    # Configurar la secuencia para la columna
    op.execute("ALTER TABLE bank_accounts ALTER COLUMN origin_id SET DEFAULT nextval('bank_accounts_origin_id_seq')")
    op.execute("ALTER SEQUENCE bank_accounts_origin_id_seq OWNED BY bank_accounts.origin_id")
    
    # Ahora hacer la columna NOT NULL y agregar constraint unique
    op.alter_column('bank_accounts', 'origin_id', nullable=False)
    op.create_unique_constraint('uq_bank_accounts_origin_id', 'bank_accounts', ['origin_id'])


def downgrade() -> None:
    # Eliminar constraint unique y la columna
    op.drop_constraint('uq_bank_accounts_origin_id', 'bank_accounts', type_='unique')
    op.execute("DROP SEQUENCE IF EXISTS bank_accounts_origin_id_seq CASCADE")
    op.drop_column('bank_accounts', 'origin_id')
    # ### end Alembic commands ###
