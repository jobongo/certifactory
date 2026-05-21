"""add certificate_templates table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'certificate_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('ca_id', sa.String(36), sa.ForeignKey('certificate_authorities.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(20), nullable=True),
        sa.Column('key_algorithm', sa.String(10), nullable=True),
        sa.Column('key_size', sa.Integer(), nullable=True),
        sa.Column('validity_days', sa.Integer(), nullable=True),
        sa.Column('key_usage', sa.JSON(), nullable=True),
        sa.Column('extended_key_usage', sa.JSON(), nullable=True),
        sa.Column('custom_extensions', sa.JSON(), nullable=True),
        sa.Column('subject_defaults', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('certificate_templates')
