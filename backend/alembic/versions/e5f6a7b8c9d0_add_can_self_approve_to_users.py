"""add can_self_approve to users

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('can_self_approve', sa.Boolean(), server_default='0', nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE users SET can_self_approve = 1 WHERE role = 'admin'"))


def downgrade() -> None:
    op.drop_column('users', 'can_self_approve')
