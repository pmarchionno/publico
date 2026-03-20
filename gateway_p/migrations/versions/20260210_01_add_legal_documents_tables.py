"""Add legal documents and user acceptances tables

Revision ID: 20260210_01
Revises: 20260209_02
Create Date: 2026-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260210_01'
down_revision = '20260209_02'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla de documentos legales
    op.create_table(
        'legal_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(32), nullable=False, 
                  comment='Tipo: terms_and_conditions, privacy_policy, etc.'),
        sa.Column('version', sa.String(16), nullable=False,
                  comment='Versión del documento (ej: 1.0, 2.1)'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False,
                  comment='Fecha desde la cual es efectivo'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Índices para legal_documents
    op.create_index('idx_legal_doc_type_active', 'legal_documents', 
                    ['document_type', 'is_active'])
    op.create_index('idx_legal_doc_type_version', 'legal_documents', 
                    ['document_type', 'version'], unique=True)
    
    # Crear tabla de aceptaciones de usuarios
    op.create_table(
        'user_legal_acceptances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False,
                  comment='Fecha y hora de aceptación'),
        sa.Column('ip_address', sa.String(45), nullable=True,
                  comment='IP desde donde se aceptó (IPv4 o IPv6)'),
        sa.Column('user_agent', sa.String(512), nullable=True,
                  comment='User agent del navegador/app'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['legal_documents.id'], ondelete='CASCADE'),
    )
    
    # Índices para user_legal_acceptances
    op.create_index('idx_user_acceptance_user', 'user_legal_acceptances', ['user_id'])
    op.create_index('idx_user_acceptance_document', 'user_legal_acceptances', ['document_id'])
    op.create_index('idx_user_acceptance_user_doc', 'user_legal_acceptances', 
                    ['user_id', 'document_id'])


def downgrade():
    # Eliminar índices de user_legal_acceptances
    op.drop_index('idx_user_acceptance_user_doc', table_name='user_legal_acceptances')
    op.drop_index('idx_user_acceptance_document', table_name='user_legal_acceptances')
    op.drop_index('idx_user_acceptance_user', table_name='user_legal_acceptances')
    
    # Eliminar tabla de aceptaciones
    op.drop_table('user_legal_acceptances')
    
    # Eliminar índices de legal_documents
    op.drop_index('idx_legal_doc_type_version', table_name='legal_documents')
    op.drop_index('idx_legal_doc_type_active', table_name='legal_documents')
    
    # Eliminar tabla de documentos legales
    op.drop_table('legal_documents')
