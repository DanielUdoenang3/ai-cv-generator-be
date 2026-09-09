"""add_missing_gender_column

The gender column was assumed to already exist in migration f1a2b3c4d5e6
but was never actually present in the clients table. This migration adds it.

Revision ID: g2h3i4j5k6l7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("gender", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "gender")
