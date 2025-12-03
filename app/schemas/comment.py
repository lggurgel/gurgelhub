"""
Comment Schemas for GurgelHub API

Pydantic models for request/response validation and serialization.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ============================================
# General Comments
# ============================================

class CommentBase(BaseModel):
    """Base comment fields shared across schemas."""
    content: str = Field(..., min_length=1, max_length=10000)
    author_name: Optional[str] = Field(None, min_length=1, max_length=100)


class CommentCreate(CommentBase):
    """Schema for creating a new comment."""
    parent_id: Optional[UUID] = None
    author_token: str = Field(..., min_length=32, max_length=64)


class CommentUpdate(BaseModel):
    """Schema for updating an existing comment."""
    content: str = Field(..., min_length=1, max_length=10000)
    author_token: str = Field(..., min_length=32, max_length=64)


class CommentResponse(BaseModel):
    """Schema for comment response (without nested replies)."""
    id: UUID
    article_id: UUID
    parent_id: Optional[UUID] = None
    author_name: Optional[str] = None
    content: str
    is_edited: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    reply_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CommentWithReplies(CommentResponse):
    """Schema for comment with nested replies (recursive)."""
    replies: List["CommentWithReplies"] = []

    model_config = ConfigDict(from_attributes=True)


class CommentTree(BaseModel):
    """Schema for paginated comment tree response."""
    comments: List[CommentWithReplies]
    total: int
    page: int
    per_page: int


# ============================================
# Inline Comments (Text Selection)
# ============================================

class InlineCommentBase(BaseModel):
    """Base inline comment fields."""
    content: str = Field(..., min_length=1, max_length=10000)
    author_name: Optional[str] = Field(None, min_length=1, max_length=100)


class InlineCommentCreate(InlineCommentBase):
    """Schema for creating an inline comment on selected text."""
    selector: str = Field(..., min_length=1, max_length=500)
    selected_text: str = Field(..., min_length=1, max_length=5000)
    start_offset: int = Field(..., ge=0)
    end_offset: int = Field(..., ge=0)
    content_hash: str = Field(..., min_length=32, max_length=64)
    author_token: str = Field(..., min_length=32, max_length=64)
    parent_id: Optional[UUID] = None


class InlineCommentUpdate(BaseModel):
    """Schema for updating an inline comment."""
    content: str = Field(..., min_length=1, max_length=10000)
    author_token: str = Field(..., min_length=32, max_length=64)


class InlineCommentResolve(BaseModel):
    """Schema for resolving/unresolving an inline comment thread."""
    author_token: str = Field(..., min_length=32, max_length=64)
    resolved: bool = True


class InlineCommentResponse(BaseModel):
    """Schema for inline comment response."""
    id: UUID
    article_id: UUID
    parent_id: Optional[UUID] = None
    selector: str
    selected_text: str
    start_offset: int
    end_offset: int
    content_hash: str
    author_name: Optional[str] = None
    content: str
    is_resolved: bool = False
    is_edited: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    reply_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class InlineCommentWithReplies(InlineCommentResponse):
    """Schema for inline comment with nested replies."""
    replies: List["InlineCommentWithReplies"] = []

    model_config = ConfigDict(from_attributes=True)


class InlineCommentGroup(BaseModel):
    """Group of inline comments for the same text selection."""
    selector: str
    selected_text: str
    start_offset: int
    end_offset: int
    comments: List[InlineCommentWithReplies]
    total_count: int


class InlineCommentsResponse(BaseModel):
    """Response containing all inline comments for an article, grouped by selection."""
    groups: List[InlineCommentGroup]
    total: int


# ============================================
# User Identity
# ============================================

class UserIdentity(BaseModel):
    """Schema for user identity management (localStorage persistence)."""
    author_token: str = Field(..., min_length=32, max_length=64)
    author_name: Optional[str] = Field(None, min_length=1, max_length=100)


class UserIdentityUpdate(BaseModel):
    """Schema for updating cached user identity."""
    author_name: Optional[str] = Field(None, min_length=1, max_length=100)


# Enable recursive model references
CommentWithReplies.model_rebuild()
InlineCommentWithReplies.model_rebuild()

