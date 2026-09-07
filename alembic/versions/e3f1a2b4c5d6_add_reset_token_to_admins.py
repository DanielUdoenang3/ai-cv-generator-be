"""add_reset_token_to_admins

Revision ID: e3f1a2b4c5d6
Revises: cfc93f8f4591
Create Date: 2026-09-07 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f1a2b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'cfc93f8f4591'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password reset token fields to admins table."""
    op.add_column('admins', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('admins', sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_admins_reset_token', 'admins', ['reset_token'], unique=True)


def downgrade() -> None:
    """Remove password reset token fields from admins table."""
    op.drop_index('ix_admins_reset_token', table_name='admins')
    op.drop_column('admins', 'reset_token_expires_at')
    op.drop_column('admins', 'reset_token')
