"""add ACME tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'acme_accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('jwk', sa.JSON(), nullable=False),
        sa.Column('jwk_thumbprint', sa.String(64), nullable=False, unique=True),
        sa.Column('contact', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'acme_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('acme_accounts.id'), nullable=False),
        sa.Column('ca_id', sa.String(36), sa.ForeignKey('certificate_authorities.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('identifiers', sa.JSON(), nullable=False),
        sa.Column('not_before', sa.DateTime(), nullable=True),
        sa.Column('not_after', sa.DateTime(), nullable=True),
        sa.Column('certificate_id', sa.String(36), sa.ForeignKey('certificates.id'), nullable=True),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'acme_authorizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', sa.String(36), sa.ForeignKey('acme_orders.id'), nullable=False),
        sa.Column('identifier_type', sa.String(20), nullable=True),
        sa.Column('identifier_value', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('challenges', sa.JSON(), nullable=False),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('acme_authorizations')
    op.drop_table('acme_orders')
    op.drop_table('acme_accounts')
