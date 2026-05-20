"""add deleted_ca to auditaction enum

Revision ID: 430931b9ff48
Revises: 9cee7cc9f982
Create Date: 2026-05-17 23:19:37.030143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '430931b9ff48'
down_revision: Union[str, None] = '9cee7cc9f982'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'deleted_ca'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'imported_ca'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'imported_cert'")


def downgrade() -> None:
    pass
