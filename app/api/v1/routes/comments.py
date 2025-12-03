"""
Comment API Routes for GurgelHub

RESTful endpoints for managing comments on articles:
- General comments with threading support
- Inline comments for text selection (Confluence-style)
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.article import ArticleService
from app.services.comment import CommentService
from app.schemas.comment import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentWithReplies,
    CommentTree,
    InlineCommentCreate,
    InlineCommentUpdate,
    InlineCommentResolve,
    InlineCommentResponse,
    InlineCommentWithReplies,
    InlineCommentsResponse,
)

router = APIRouter()


# ============================================
# General Comments
# ============================================

@router.get("/articles/{article_id}/comments", response_model=CommentTree)
async def get_article_comments(
    article_id: UUID,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get all comments for an article with nested replies.

    Returns paginated top-level comments with their reply threads.
    """
    # Verify article exists
    article_service = ArticleService(db)
    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comment_service = CommentService(db)
    comments, total = await comment_service.get_comments_for_article(
        article_id=article_id,
        page=page,
        per_page=per_page
    )

    # Build response with nested structure
    comment_list = []
    for comment in comments:
        comment_list.append(_build_comment_tree(comment))

    return CommentTree(
        comments=comment_list,
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/articles/{article_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    article_id: UUID,
    comment_in: CommentCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new comment on an article.

    Set parent_id to reply to an existing comment.
    """
    # Verify article exists and is published
    article_service = ArticleService(db)
    article = await article_service.get_article(article_id)
    if not article or not article.is_published:
        raise HTTPException(status_code=404, detail="Article not found")

    # If replying, verify parent exists
    comment_service = CommentService(db)
    if comment_in.parent_id:
        parent = await comment_service.get_comment(comment_in.parent_id)
        if not parent or parent.article_id != article_id:
            raise HTTPException(status_code=400, detail="Invalid parent comment")

    comment = await comment_service.create_comment(article_id, comment_in)
    reply_count = await comment_service.get_reply_count(comment.id)

    return CommentResponse(
        id=comment.id,
        article_id=comment.article_id,
        parent_id=comment.parent_id,
        author_name=comment.author_name,
        content=comment.content,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        reply_count=reply_count
    )


@router.get("/comments/{comment_id}", response_model=CommentWithReplies)
async def get_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a single comment with its replies."""
    comment_service = CommentService(db)
    comment_with_replies = await comment_service.get_comment_with_replies(comment_id)

    if not comment_with_replies:
        raise HTTPException(status_code=404, detail="Comment not found")

    return comment_with_replies


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    comment_in: CommentUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update a comment.

    Requires the original author_token for authorization.
    """
    comment_service = CommentService(db)
    comment = await comment_service.update_comment(comment_id, comment_in)

    if not comment:
        raise HTTPException(
            status_code=403,
            detail="Comment not found or you don't have permission to edit it"
        )

    reply_count = await comment_service.get_reply_count(comment.id)

    return CommentResponse(
        id=comment.id,
        article_id=comment.article_id,
        parent_id=comment.parent_id,
        author_name=comment.author_name,
        content=comment.content,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        reply_count=reply_count
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    author_token: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a comment.

    If the comment has replies, it will be soft-deleted (content replaced with [deleted]).
    Requires the original author_token for authorization.
    """
    comment_service = CommentService(db)
    success = await comment_service.delete_comment(comment_id, author_token)

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Comment not found or you don't have permission to delete it"
        )


# ============================================
# Inline Comments (Text Selection)
# ============================================

@router.get("/articles/{article_id}/inline-comments", response_model=InlineCommentsResponse)
async def get_article_inline_comments(
    article_id: UUID,
    include_resolved: bool = True,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get all inline comments for an article, grouped by text selection.

    Returns groups of comments organized by their text selection location.
    """
    # Verify article exists
    article_service = ArticleService(db)
    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comment_service = CommentService(db)
    groups, total = await comment_service.get_inline_comments_for_article(
        article_id=article_id,
        include_resolved=include_resolved
    )

    return InlineCommentsResponse(
        groups=groups,
        total=total
    )


@router.post("/articles/{article_id}/inline-comments", response_model=InlineCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_inline_comment(
    article_id: UUID,
    comment_in: InlineCommentCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new inline comment on selected text.

    Requires:
    - selector: CSS selector or path to the content block
    - selected_text: The actual selected text
    - start_offset/end_offset: Character positions within the block
    - content_hash: Hash of the article content for change detection
    """
    # Verify article exists and is published
    article_service = ArticleService(db)
    article = await article_service.get_article(article_id)
    if not article or not article.is_published:
        raise HTTPException(status_code=404, detail="Article not found")

    # Validate offsets
    if comment_in.start_offset >= comment_in.end_offset:
        raise HTTPException(status_code=400, detail="Invalid text selection range")

    comment_service = CommentService(db)

    # If replying, verify parent exists
    if comment_in.parent_id:
        parent = await comment_service.get_inline_comment(comment_in.parent_id)
        if not parent or parent.article_id != article_id:
            raise HTTPException(status_code=400, detail="Invalid parent comment")

    comment = await comment_service.create_inline_comment(article_id, comment_in)

    return InlineCommentResponse(
        id=comment.id,
        article_id=comment.article_id,
        parent_id=comment.parent_id,
        selector=comment.selector,
        selected_text=comment.selected_text,
        start_offset=comment.start_offset,
        end_offset=comment.end_offset,
        content_hash=comment.content_hash,
        author_name=comment.author_name,
        content=comment.content,
        is_resolved=comment.is_resolved,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        resolved_at=comment.resolved_at,
        reply_count=0
    )


@router.get("/inline-comments/{comment_id}", response_model=InlineCommentWithReplies)
async def get_inline_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a single inline comment with its replies."""
    comment_service = CommentService(db)
    comment_with_replies = await comment_service.get_inline_comment_with_replies(comment_id)

    if not comment_with_replies:
        raise HTTPException(status_code=404, detail="Inline comment not found")

    return comment_with_replies


@router.put("/inline-comments/{comment_id}", response_model=InlineCommentResponse)
async def update_inline_comment(
    comment_id: UUID,
    comment_in: InlineCommentUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update an inline comment.

    Requires the original author_token for authorization.
    """
    comment_service = CommentService(db)
    comment = await comment_service.update_inline_comment(comment_id, comment_in)

    if not comment:
        raise HTTPException(
            status_code=403,
            detail="Comment not found or you don't have permission to edit it"
        )

    return InlineCommentResponse(
        id=comment.id,
        article_id=comment.article_id,
        parent_id=comment.parent_id,
        selector=comment.selector,
        selected_text=comment.selected_text,
        start_offset=comment.start_offset,
        end_offset=comment.end_offset,
        content_hash=comment.content_hash,
        author_name=comment.author_name,
        content=comment.content,
        is_resolved=comment.is_resolved,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        resolved_at=comment.resolved_at,
        reply_count=len(comment.replies) if comment.replies else 0
    )


@router.post("/inline-comments/{comment_id}/resolve", response_model=InlineCommentResponse)
async def resolve_inline_comment(
    comment_id: UUID,
    resolve_in: InlineCommentResolve,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Mark an inline comment thread as resolved or unresolved.

    Only the original comment author can resolve/unresolve.
    """
    comment_service = CommentService(db)
    comment = await comment_service.resolve_inline_comment(
        comment_id,
        resolve_in.author_token,
        resolve_in.resolved
    )

    if not comment:
        raise HTTPException(
            status_code=403,
            detail="Comment not found or you don't have permission to resolve it"
        )

    return InlineCommentResponse(
        id=comment.id,
        article_id=comment.article_id,
        parent_id=comment.parent_id,
        selector=comment.selector,
        selected_text=comment.selected_text,
        start_offset=comment.start_offset,
        end_offset=comment.end_offset,
        content_hash=comment.content_hash,
        author_name=comment.author_name,
        content=comment.content,
        is_resolved=comment.is_resolved,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        resolved_at=comment.resolved_at,
        reply_count=len(comment.replies) if comment.replies else 0
    )


@router.delete("/inline-comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inline_comment(
    comment_id: UUID,
    author_token: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an inline comment.

    If the comment has replies, it will be soft-deleted.
    Requires the original author_token for authorization.
    """
    comment_service = CommentService(db)
    success = await comment_service.delete_inline_comment(comment_id, author_token)

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Comment not found or you don't have permission to delete it"
        )


# ============================================
# Comment Statistics
# ============================================

@router.get("/articles/{article_id}/comment-stats")
async def get_comment_stats(
    article_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get comment statistics for an article."""
    article_service = ArticleService(db)
    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comment_service = CommentService(db)
    general_count = await comment_service.get_comment_count(article_id)
    inline_count = await comment_service.get_inline_comment_count(article_id)

    return {
        "article_id": article_id,
        "general_comments": general_count,
        "inline_comments": inline_count,
        "total": general_count + inline_count
    }


# ============================================
# Helper Functions
# ============================================

def _build_comment_tree(comment, children_map: dict = None) -> CommentWithReplies:
    """Recursively build comment tree with nested replies using pre-loaded map."""
    # Use the attached children_map or the passed one
    if children_map is None:
        children_map = getattr(comment, '_children_map', {})

    replies = []
    child_comments = children_map.get(comment.id, [])
    for reply in sorted(child_comments, key=lambda x: x.created_at):
        child_replies = children_map.get(reply.id, [])
        if not reply.is_deleted or len(child_replies) > 0:
            replies.append(_build_comment_tree(reply, children_map))

    return CommentWithReplies(
        id=comment.id,
        article_id=comment.article_id,
        parent_id=comment.parent_id,
        author_name=comment.author_name if not comment.is_deleted else None,
        content=comment.content,
        is_edited=comment.is_edited,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        reply_count=len(replies),
        replies=replies
    )

