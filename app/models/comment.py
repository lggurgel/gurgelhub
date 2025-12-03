"""
Comment Models for GurgelHub

Supports two types of comments:
1. General Comments - Traditional comments at the end of articles with threading support
2. Inline Comments - Confluence-style comments attached to specific text selections
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Text, Boolean, DateTime, Integer, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Comment(Base):
    """
    General comment model with recursive threading support.

    Supports nested replies through self-referential foreign key.
    Anonymous users can optionally provide their name.
    """
    __tablename__ = "comments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Self-referential for threading
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Anonymous user identity (optional)
    author_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True
    )  # Anonymous session token for edit/delete permissions

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # Soft delete for threaded comments
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        back_populates="replies",
        remote_side=[id]
    )

    __table_args__ = (
        Index('idx_comments_article_parent', 'article_id', 'parent_id'),
        Index('idx_comments_article_created', 'article_id', 'created_at'),
    )


class InlineComment(Base):
    """
    Inline comment model for Confluence-style text selection comments.

    Stores the selected text range using character offsets within a
    specific content block (identified by a unique selector/path).
    Multiple comments can reference the same text selection.
    """
    __tablename__ = "inline_comments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Thread support - inline comments can also have replies
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("inline_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Text selection info
    # selector: CSS selector or unique path to the content block
    selector: Mapped[str] = mapped_column(String(500), nullable=False)
    # The actual selected text (for validation and display)
    selected_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Character offsets within the block
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    # Content hash for detecting if the article changed
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Anonymous user identity
    author_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    replies: Mapped[list["InlineComment"]] = relationship(
        "InlineComment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    parent: Mapped[Optional["InlineComment"]] = relationship(
        "InlineComment",
        back_populates="replies",
        remote_side=[id]
    )

    __table_args__ = (
        Index('idx_inline_comments_article', 'article_id'),
        Index('idx_inline_comments_selector', 'article_id', 'selector'),
        Index('idx_inline_comments_article_created', 'article_id', 'created_at'),
    )

