"""
Comment Service for GurgelHub

Business logic for comment operations including:
- CRUD for general comments with threading
- CRUD for inline comments with text selection
- Efficient querying with relationship loading
"""
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment, InlineComment
from app.schemas.comment import (
    CommentCreate, CommentUpdate,
    InlineCommentCreate, InlineCommentUpdate,
    CommentWithReplies, InlineCommentWithReplies, InlineCommentGroup
)


class CommentService:
    """Service for managing article comments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================
    # General Comments
    # ============================================

    async def create_comment(
        self,
        article_id: UUID,
        comment_in: CommentCreate
    ) -> Comment:
        """Create a new comment or reply."""
        db_comment = Comment(
            article_id=article_id,
            parent_id=comment_in.parent_id,
            author_name=comment_in.author_name,
            author_token=comment_in.author_token,
            content=comment_in.content
        )
        self.db.add(db_comment)
        await self.db.commit()
        await self.db.refresh(db_comment)
        return db_comment

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        """Get a single comment by ID (without replies loaded)."""
        result = await self.db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
        )
        return result.scalar_one_or_none()

    async def get_comment_with_replies(self, comment_id: UUID) -> Optional[CommentWithReplies]:
        """Get a single comment by ID with all nested replies."""
        result = await self.db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return None

        # Load all comments for the article to build tree
        all_result = await self.db.execute(
            select(Comment)
            .where(Comment.article_id == comment.article_id)
        )
        all_comments = list(all_result.scalars().all())

        # Build children map
        children_map: dict = {c.id: [] for c in all_comments}
        for c in all_comments:
            if c.parent_id and c.parent_id in children_map:
                children_map[c.parent_id].append(c)

        return self._build_comment_tree(comment, children_map)

    def _build_comment_tree(self, comment: Comment, children_map: dict) -> CommentWithReplies:
        """Build comment with nested replies from pre-loaded map."""
        replies = []
        for child in sorted(children_map.get(comment.id, []), key=lambda x: x.created_at):
            if not child.is_deleted or len(children_map.get(child.id, [])) > 0:
                replies.append(self._build_comment_tree(child, children_map))

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

    async def get_comments_for_article(
        self,
        article_id: UUID,
        page: int = 1,
        per_page: int = 20,
        include_deleted: bool = False
    ) -> Tuple[List[dict], int]:
        """
        Get top-level comments for an article with nested replies.
        Returns comments (as dicts with replies) and total count.
        """
        # First, count top-level comments for pagination
        count_query = select(func.count()).select_from(Comment).where(
            and_(
                Comment.article_id == article_id,
                Comment.parent_id.is_(None),
                Comment.is_deleted == False if not include_deleted else True
            )
        )
        total = await self.db.scalar(count_query) or 0

        # Get ALL comments for the article to avoid lazy loading issues
        base_query = select(Comment).where(Comment.article_id == article_id)
        if not include_deleted:
            base_query = base_query.where(Comment.is_deleted == False)

        result = await self.db.execute(base_query.order_by(Comment.created_at.desc()))
        all_comments = list(result.scalars().all())

        # Build lookup maps
        children_map: dict = {c.id: [] for c in all_comments}
        top_level_comments = []

        for comment in all_comments:
            if comment.parent_id is None:
                top_level_comments.append(comment)
            elif comment.parent_id in children_map:
                children_map[comment.parent_id].append(comment)

        # Apply pagination to top-level comments only
        start = (page - 1) * per_page
        end = start + per_page
        paginated_top_level = top_level_comments[start:end]

        # Build comment trees with children_map
        comments_with_replies = []
        for comment in paginated_top_level:
            comment._children_map = children_map  # Attach map for tree building
            comments_with_replies.append(comment)

        return comments_with_replies, total

    def get_comment_replies(self, comment: Comment, children_map: dict) -> List[Comment]:
        """Get replies for a comment from pre-loaded map."""
        return children_map.get(comment.id, [])

    async def update_comment(
        self,
        comment_id: UUID,
        comment_in: CommentUpdate
    ) -> Optional[Comment]:
        """Update a comment if the author token matches."""
        comment = await self.get_comment(comment_id)
        if not comment:
            return None

        # Verify ownership
        if comment.author_token != comment_in.author_token:
            return None

        comment.content = comment_in.content
        comment.is_edited = True

        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(
        self,
        comment_id: UUID,
        author_token: str,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete a comment. Uses soft delete if comment has replies.

        Returns True if deleted, False if not found or unauthorized.
        """
        comment = await self.get_comment(comment_id)
        if not comment:
            return False

        # Verify ownership
        if comment.author_token != author_token:
            return False

        # Check if comment has replies using a query (avoid lazy loading)
        reply_count = await self.db.scalar(
            select(func.count()).select_from(Comment).where(Comment.parent_id == comment_id)
        )
        has_replies = (reply_count or 0) > 0

        if has_replies and not hard_delete:
            # Soft delete - preserve thread structure
            comment.is_deleted = True
            comment.content = "[deleted]"
            comment.author_name = None
            await self.db.commit()
        else:
            # Hard delete
            await self.db.delete(comment)
            await self.db.commit()

        return True

    async def get_reply_count(self, comment_id: UUID) -> int:
        """Get total reply count for a comment (recursive)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Comment)
            .where(Comment.parent_id == comment_id)
        )
        return result.scalar() or 0

    # ============================================
    # Inline Comments
    # ============================================

    async def create_inline_comment(
        self,
        article_id: UUID,
        comment_in: InlineCommentCreate
    ) -> InlineComment:
        """Create a new inline comment on selected text."""
        db_comment = InlineComment(
            article_id=article_id,
            parent_id=comment_in.parent_id,
            selector=comment_in.selector,
            selected_text=comment_in.selected_text,
            start_offset=comment_in.start_offset,
            end_offset=comment_in.end_offset,
            content_hash=comment_in.content_hash,
            author_name=comment_in.author_name,
            author_token=comment_in.author_token,
            content=comment_in.content
        )
        self.db.add(db_comment)
        await self.db.commit()
        await self.db.refresh(db_comment)
        return db_comment

    async def get_inline_comment(self, comment_id: UUID) -> Optional[InlineComment]:
        """Get a single inline comment by ID (without replies loaded)."""
        result = await self.db.execute(
            select(InlineComment)
            .where(InlineComment.id == comment_id)
        )
        return result.scalar_one_or_none()

    async def get_inline_comment_with_replies(self, comment_id: UUID) -> Optional[InlineCommentWithReplies]:
        """Get a single inline comment by ID with all nested replies."""
        # First get the comment
        result = await self.db.execute(
            select(InlineComment)
            .where(InlineComment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return None

        # Load all replies for this thread
        all_replies_result = await self.db.execute(
            select(InlineComment)
            .where(InlineComment.article_id == comment.article_id)
        )
        all_comments = list(all_replies_result.scalars().all())

        # Build children map
        children_map: dict = {c.id: [] for c in all_comments}
        for c in all_comments:
            if c.parent_id and c.parent_id in children_map:
                children_map[c.parent_id].append(c)

        return self._build_inline_comment_tree(comment, children_map)

    async def get_inline_comments_for_article(
        self,
        article_id: UUID,
        include_resolved: bool = True,
        include_deleted: bool = False
    ) -> Tuple[List[InlineCommentGroup], int]:
        """
        Get all inline comments for an article, grouped by text selection.

        Returns groups of comments and total count.
        """
        # Load ALL comments for the article (not just top-level)
        # This avoids lazy loading issues with nested replies
        base_query = select(InlineComment).where(
            InlineComment.article_id == article_id
        )

        if not include_resolved:
            base_query = base_query.where(InlineComment.is_resolved == False)

        if not include_deleted:
            base_query = base_query.where(InlineComment.is_deleted == False)

        query = base_query.order_by(InlineComment.start_offset, InlineComment.created_at)

        result = await self.db.execute(query)
        all_comments = list(result.scalars().all())

        # Build a lookup map by ID
        comments_by_id = {c.id: c for c in all_comments}

        # Build children map
        children_map: dict = {c.id: [] for c in all_comments}
        top_level_comments = []

        for comment in all_comments:
            if comment.parent_id is None:
                top_level_comments.append(comment)
            elif comment.parent_id in children_map:
                children_map[comment.parent_id].append(comment)

        # Group top-level comments by selector + offsets
        groups_dict = {}
        for comment in top_level_comments:
            key = (comment.selector, comment.start_offset, comment.end_offset)
            if key not in groups_dict:
                groups_dict[key] = InlineCommentGroup(
                    selector=comment.selector,
                    selected_text=comment.selected_text,
                    start_offset=comment.start_offset,
                    end_offset=comment.end_offset,
                    comments=[],
                    total_count=0
                )

            # Build comment with replies from our maps
            comment_with_replies = self._build_inline_comment_tree(comment, children_map)
            groups_dict[key].comments.append(comment_with_replies)
            groups_dict[key].total_count += 1 + self._count_children(comment.id, children_map)

        groups = list(groups_dict.values())
        total = sum(g.total_count for g in groups)

        return groups, total

    def _build_inline_comment_tree(
        self,
        comment: InlineComment,
        children_map: dict
    ) -> InlineCommentWithReplies:
        """Build inline comment with nested replies from pre-loaded data."""
        replies = []
        for child in children_map.get(comment.id, []):
            if not child.is_deleted:
                replies.append(self._build_inline_comment_tree(child, children_map))

        return InlineCommentWithReplies(
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
            reply_count=len(replies),
            replies=replies
        )

    def _count_children(self, comment_id: UUID, children_map: dict) -> int:
        """Count all children recursively from pre-loaded map."""
        count = 0
        for child in children_map.get(comment_id, []):
            count += 1 + self._count_children(child.id, children_map)
        return count

    async def update_inline_comment(
        self,
        comment_id: UUID,
        comment_in: InlineCommentUpdate
    ) -> Optional[InlineComment]:
        """Update an inline comment if the author token matches."""
        comment = await self.get_inline_comment(comment_id)
        if not comment:
            return None

        # Verify ownership
        if comment.author_token != comment_in.author_token:
            return None

        comment.content = comment_in.content
        comment.is_edited = True

        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def resolve_inline_comment(
        self,
        comment_id: UUID,
        author_token: str,
        resolved: bool = True
    ) -> Optional[InlineComment]:
        """Mark an inline comment thread as resolved/unresolved."""
        comment = await self.get_inline_comment(comment_id)
        if not comment:
            return None

        # Only the original comment author can resolve
        if comment.author_token != author_token:
            return None

        comment.is_resolved = resolved
        comment.resolved_at = datetime.utcnow() if resolved else None

        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete_inline_comment(
        self,
        comment_id: UUID,
        author_token: str,
        hard_delete: bool = False
    ) -> bool:
        """Delete an inline comment."""
        comment = await self.get_inline_comment(comment_id)
        if not comment:
            return False

        # Verify ownership
        if comment.author_token != author_token:
            return False

        # Check if comment has replies using a query (avoid lazy loading)
        reply_count = await self.db.scalar(
            select(func.count()).select_from(InlineComment).where(InlineComment.parent_id == comment_id)
        )
        has_replies = (reply_count or 0) > 0

        if has_replies and not hard_delete:
            # Soft delete
            comment.is_deleted = True
            comment.content = "[deleted]"
            comment.author_name = None
            await self.db.commit()
        else:
            # Hard delete
            await self.db.delete(comment)
            await self.db.commit()

        return True

    # ============================================
    # Statistics
    # ============================================

    async def get_comment_count(self, article_id: UUID) -> int:
        """Get total comment count for an article (general comments only)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Comment)
            .where(
                and_(
                    Comment.article_id == article_id,
                    Comment.is_deleted == False
                )
            )
        )
        return result.scalar() or 0

    async def get_inline_comment_count(self, article_id: UUID) -> int:
        """Get total inline comment count for an article."""
        result = await self.db.execute(
            select(func.count())
            .select_from(InlineComment)
            .where(
                and_(
                    InlineComment.article_id == article_id,
                    InlineComment.is_deleted == False
                )
            )
        )
        return result.scalar() or 0

