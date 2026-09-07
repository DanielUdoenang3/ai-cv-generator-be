"""add_cover_letter_and_document_kind

Adds structured cover letter storage to ai_generations and a document_kind
discriminator column to documents so resume and cover letter files can
coexist as separate records under the same submission.

ai_generations table
--------------------
- cover_letter_json  JSON nullable

documents table
---------------
- document_kind  VARCHAR NOT NULL DEFAULT 'resume'

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-09-07 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# revision identifiers
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_generations: cover letter JSON storage ──────────────────────────
    op.add_column(
        "ai_generations",
        sa.Column("cover_letter_json", sa.JSON(), nullable=True),
    )

    # ── documents: kind discriminator ─────────────────────────────────────
    op.add_column(
        "documents",
        sa.Column(
            "document_kind",
            sa.String(),
            nullable=False,
            server_default="resume",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "document_kind")
    op.drop_column("ai_generations", "cover_letter_json")
