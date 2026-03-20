"""change origin_id to string

Revision ID: 20260301_01_change_origin_id_to_string
Revises: 
Create Date: 2026-03-01 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260301_01_origin_str'
down_revision: Union[str, None] = '20260224_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar el índice único existente
    op.drop_index('ix_transfers_origin_id', table_name='transfers')
    
    # Cambiar el tipo de columna de bigint a varchar(64) para poder acomodar números largos
    # Convertir los valores existentes de bigint a string
    op.execute("""
        ALTER TABLE transfers 
        ALTER COLUMN origin_id TYPE VARCHAR(64) 
        USING origin_id::text
    """)
    
    # Establecer el valor por defecto
    op.alter_column('transfers', 'origin_id',
                    server_default=sa.text("'0000000000'"),
                    nullable=False)
    
    # Recrear el índice único
    op.create_index('ix_transfers_origin_id', 'transfers', ['origin_id'], unique=True)


def downgrade() -> None:
    # Eliminar el índice
    op.drop_index('ix_transfers_origin_id', table_name='transfers')
    
    # Convertir de vuelta a bigint
    op.execute("""
        ALTER TABLE transfers 
        ALTER COLUMN origin_id TYPE BIGINT 
        USING origin_id::bigint
    """)
    
    # Remover el valor por defecto
    op.alter_column('transfers', 'origin_id',
                    server_default=None,
                    nullable=False)
    
    # Recrear el índice
    op.create_index('ix_transfers_origin_id', 'transfers', ['origin_id'], unique=True)
