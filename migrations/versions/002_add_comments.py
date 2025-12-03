"""Add comments tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create comments table (general article comments with threading)
    op.create_table(
        'comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('author_name', sa.String(length=100), nullable=True),
        sa.Column('author_token', sa.String(length=64), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_edited', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for comments
    op.create_index('ix_comments_article_id', 'comments', ['article_id'])
    op.create_index('ix_comments_parent_id', 'comments', ['parent_id'])
    op.create_index('ix_comments_author_token', 'comments', ['author_token'])
    op.create_index('idx_comments_article_parent', 'comments', ['article_id', 'parent_id'])
    op.create_index('idx_comments_article_created', 'comments', ['article_id', 'created_at'])

    # Create inline_comments table (text selection comments)
    op.create_table(
        'inline_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('selector', sa.String(length=500), nullable=False),
        sa.Column('selected_text', sa.Text(), nullable=False),
        sa.Column('start_offset', sa.Integer(), nullable=False),
        sa.Column('end_offset', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('author_name', sa.String(length=100), nullable=True),
        sa.Column('author_token', sa.String(length=64), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_edited', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['inline_comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for inline_comments
    op.create_index('ix_inline_comments_article_id', 'inline_comments', ['article_id'])
    op.create_index('ix_inline_comments_parent_id', 'inline_comments', ['parent_id'])
    op.create_index('ix_inline_comments_author_token', 'inline_comments', ['author_token'])
    op.create_index('idx_inline_comments_article', 'inline_comments', ['article_id'])
    op.create_index('idx_inline_comments_selector', 'inline_comments', ['article_id', 'selector'])
    op.create_index('idx_inline_comments_article_created', 'inline_comments', ['article_id', 'created_at'])


def downgrade() -> None:
    # Drop inline_comments indexes and table
    op.drop_index('idx_inline_comments_article_created', table_name='inline_comments')
    op.drop_index('idx_inline_comments_selector', table_name='inline_comments')
    op.drop_index('idx_inline_comments_article', table_name='inline_comments')
    op.drop_index('ix_inline_comments_author_token', table_name='inline_comments')
    op.drop_index('ix_inline_comments_parent_id', table_name='inline_comments')
    op.drop_index('ix_inline_comments_article_id', table_name='inline_comments')
    op.drop_table('inline_comments')

    # Drop comments indexes and table
    op.drop_index('idx_comments_article_created', table_name='comments')
    op.drop_index('idx_comments_article_parent', table_name='comments')
    op.drop_index('ix_comments_author_token', table_name='comments')
    op.drop_index('ix_comments_parent_id', table_name='comments')
    op.drop_index('ix_comments_article_id', table_name='comments')
    op.drop_table('comments')

