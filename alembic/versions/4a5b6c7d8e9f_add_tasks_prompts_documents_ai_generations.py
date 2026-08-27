"""add tasks prompts documents ai_generations tables

Revision ID: 4a5b6c7d8e9f
Revises: 0ef7222ab49c
Create Date: 2026-08-26 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a5b6c7d8e9f'
down_revision: Union[str, Sequence[str], None] = '0ef7222ab49c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### create tasks table ###
    op.create_table('tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('assigned_to_id', sa.String(), nullable=True),
        sa.Column('priority', sa.String(), nullable=False, server_default='normal'),
        sa.Column('status', sa.String(), nullable=False, server_default='todo'),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)

    # ### create prompts table ###
    op.create_table('prompts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompts_id'), 'prompts', ['id'], unique=False)

    # ### create documents table ###
    op.create_table('documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('file_url', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False, server_default='pdf'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)

    # ### create ai_generations table ###
    op.create_table('ai_generations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(), nullable=False, server_default='success'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_generations_id'), 'ai_generations', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_generations_id'), table_name='ai_generations')
    op.drop_table('ai_generations')

    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_index(op.f('ix_prompts_id'), table_name='prompts')
    op.drop_table('prompts')

    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')
    op.drop_table('tasks')
