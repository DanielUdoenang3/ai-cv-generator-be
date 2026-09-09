"""add_admin_invitations_table

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h3i4j5k6l7m8"
down_revision: Union[str, Sequence[str], None] = "g2h3i4j5k6l7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_invitations",
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("invited_by_id", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_invitations_id"), "admin_invitations", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_admin_invitations_email"), "admin_invitations", ["email"], unique=False
    )
    op.create_index(
        op.f("ix_admin_invitations_token"), "admin_invitations", ["token"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_invitations_token"), table_name="admin_invitations")
    op.drop_index(op.f("ix_admin_invitations_email"), table_name="admin_invitations")
    op.drop_index(op.f("ix_admin_invitations_id"), table_name="admin_invitations")
    op.drop_table("admin_invitations")
