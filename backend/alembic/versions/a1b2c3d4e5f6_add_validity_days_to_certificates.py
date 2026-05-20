"""add validity_days to certificates

Revision ID: a1b2c3d4e5f6
Revises: 430931b9ff48
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '430931b9ff48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('certificates', sa.Column('validity_days', sa.Integer(), nullable=True, server_default='365'))
    op.execute("UPDATE certificates SET validity_days = 365 WHERE validity_days IS NULL")
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column('certificates', 'validity_days', nullable=False)


def downgrade() -> None:
    op.drop_column('certificates', 'validity_days')
