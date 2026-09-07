"""expand_client_and_submission_models

Adds all new fields required by the MANGO HR intake form redesign:

clients table
-------------
- middle_name           VARCHAR nullable
- date_of_birth         DATE nullable
- address_line          VARCHAR nullable
- city                  VARCHAR nullable
- state                 VARCHAR nullable
- country               VARCHAR nullable
- zip_code              VARCHAR nullable
- linkedin_url          VARCHAR nullable
- portfolio_url         VARCHAR nullable
- resume_file_url       VARCHAR nullable
- resume_file_name      VARCHAR nullable
- desired_job_titles    JSON nullable
- preferred_work_arrangement VARCHAR nullable
- expected_salary_range VARCHAR nullable
- available_start_date  DATE nullable
- companies_to_exclude  JSON nullable
- security_clearance    VARCHAR nullable
- citizenship_status    VARCHAR nullable
- visa_sponsorship_required VARCHAR nullable
- non_compete_obligations TEXT nullable
- professional_references JSON nullable
- gender (already existed as VARCHAR — kept, no change)
- sexual_orientation    VARCHAR nullable
- race_ethnicity        VARCHAR nullable
- veteran_status        VARCHAR nullable
- has_disability        VARCHAR nullable
- notes                 TEXT nullable

submissions table
-----------------
- saved_resume_text     TEXT nullable
- target_position altered to nullable (was NOT NULL)
- job_description altered to TEXT (was VARCHAR)
- existing_cv_url altered to TEXT (was VARCHAR)

Revision ID: f1a2b3c4d5e6
Revises: e3f1a2b4c5d6
Create Date: 2026-09-07 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# revision identifiers
# ---------------------------------------------------------------------------
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e3f1a2b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ── clients: new columns ───────────────────────────────────────────────

    # Core identity
    op.add_column("clients", sa.Column("middle_name", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("date_of_birth", sa.Date(), nullable=True))

    # Contact / address
    op.add_column("clients", sa.Column("address_line", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("city", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("state", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("country", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("zip_code", sa.String(), nullable=True))

    # Online presence
    op.add_column("clients", sa.Column("linkedin_url", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("portfolio_url", sa.String(), nullable=True))

    # Resume file
    op.add_column("clients", sa.Column("resume_file_url", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("resume_file_name", sa.String(), nullable=True))

    # Job preferences
    op.add_column("clients", sa.Column("desired_job_titles", sa.JSON(), nullable=True))
    op.add_column("clients", sa.Column("preferred_work_arrangement", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("expected_salary_range", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("available_start_date", sa.Date(), nullable=True))
    op.add_column("clients", sa.Column("companies_to_exclude", sa.JSON(), nullable=True))

    # Work authorisation
    op.add_column("clients", sa.Column("security_clearance", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("citizenship_status", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("visa_sponsorship_required", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("non_compete_obligations", sa.Text(), nullable=True))

    # Professional references
    op.add_column("clients", sa.Column("professional_references", sa.JSON(), nullable=True))

    # Demographics (EEO — voluntary)
    # NOTE: 'gender' column already exists on the clients table from the
    # original model; we only add the new demographic columns here.
    op.add_column("clients", sa.Column("sexual_orientation", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("race_ethnicity", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("veteran_status", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("has_disability", sa.String(), nullable=True))

    # Notes
    op.add_column("clients", sa.Column("notes", sa.Text(), nullable=True))

    # ── submissions: new column ────────────────────────────────────────────
    op.add_column(
        "submissions",
        sa.Column("saved_resume_text", sa.Text(), nullable=True),
    )

    # ── submissions: alter existing columns ───────────────────────────────
    # target_position — make nullable (requirement now lives on the client form)
    op.alter_column(
        "submissions",
        "target_position",
        existing_type=sa.String(),
        nullable=True,
    )

    # job_description — promote VARCHAR → TEXT for large pastes
    op.alter_column(
        "submissions",
        "job_description",
        existing_type=sa.String(),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # existing_cv_url — promote VARCHAR → TEXT (long Cloudinary URLs)
    op.alter_column(
        "submissions",
        "existing_cv_url",
        existing_type=sa.String(),
        type_=sa.Text(),
        existing_nullable=True,
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ── submissions: revert column type and nullability changes ───────────
    op.alter_column(
        "submissions",
        "existing_cv_url",
        existing_type=sa.Text(),
        type_=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "submissions",
        "job_description",
        existing_type=sa.Text(),
        type_=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "submissions",
        "target_position",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("submissions", "saved_resume_text")

    # ── clients: drop all new columns (reverse order) ─────────────────────
    op.drop_column("clients", "notes")
    op.drop_column("clients", "has_disability")
    op.drop_column("clients", "veteran_status")
    op.drop_column("clients", "race_ethnicity")
    op.drop_column("clients", "sexual_orientation")
    op.drop_column("clients", "professional_references")
    op.drop_column("clients", "non_compete_obligations")
    op.drop_column("clients", "visa_sponsorship_required")
    op.drop_column("clients", "citizenship_status")
    op.drop_column("clients", "security_clearance")
    op.drop_column("clients", "companies_to_exclude")
    op.drop_column("clients", "available_start_date")
    op.drop_column("clients", "expected_salary_range")
    op.drop_column("clients", "preferred_work_arrangement")
    op.drop_column("clients", "desired_job_titles")
    op.drop_column("clients", "resume_file_name")
    op.drop_column("clients", "resume_file_url")
    op.drop_column("clients", "portfolio_url")
    op.drop_column("clients", "linkedin_url")
    op.drop_column("clients", "zip_code")
    op.drop_column("clients", "country")
    op.drop_column("clients", "state")
    op.drop_column("clients", "city")
    op.drop_column("clients", "address_line")
    op.drop_column("clients", "date_of_birth")
    op.drop_column("clients", "middle_name")
