"""add MCP columns to certificate_authorities

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('certificate_authorities', sa.Column('mcp_enabled', sa.Boolean(), server_default='1', nullable=True))
    op.add_column('certificate_authorities', sa.Column('mcp_allowed_operations', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('certificate_authorities', 'mcp_allowed_operations')
    op.drop_column('certificate_authorities', 'mcp_enabled')
