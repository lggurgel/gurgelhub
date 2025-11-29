from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.schemas.article import ArticleCreate, ArticleUpdate

class ArticleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_article(self, article_id: UUID) -> Optional[Article]:
        result = await self.db.execute(select(Article).where(Article.id == article_id))
        return result.scalar_one_or_none()

    async def get_article_by_slug(self, slug: str) -> Optional[Article]:
        result = await self.db.execute(select(Article).where(Article.slug == slug))
        return result.scalar_one_or_none()

    async def get_articles(
        self, skip: int = 0, limit: int = 10, published_only: bool = True
    ) -> Tuple[List[Article], int]:
        query = select(Article)
        if published_only:
            query = query.where(Article.is_published == True)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Get items
        query = query.offset(skip).limit(limit).order_by(Article.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all(), total or 0

    async def create_article(self, article_in: ArticleCreate) -> Article:
        db_article = Article(
            **article_in.model_dump(),
            published_at=datetime.utcnow() if article_in.is_published else None
        )
        self.db.add(db_article)
        await self.db.commit()
        await self.db.refresh(db_article)
        return db_article

    async def update_article(
        self, article_id: UUID, article_in: ArticleUpdate
    ) -> Optional[Article]:
        db_article = await self.get_article(article_id)
        if not db_article:
            return None

        update_data = article_in.model_dump(exclude_unset=True)
        if "is_published" in update_data and update_data["is_published"] and not db_article.is_published:
            update_data["published_at"] = datetime.utcnow()

        for field, value in update_data.items():
            setattr(db_article, field, value)

        self.db.add(db_article)
        await self.db.commit()
        await self.db.refresh(db_article)
        return db_article

    async def delete_article(self, article_id: UUID) -> bool:
        result = await self.db.execute(delete(Article).where(Article.id == article_id))
        await self.db.commit()
        return result.rowcount > 0

    async def increment_view_count(self, slug: str) -> None:
        await self.db.execute(
            update(Article)
            .where(Article.slug == slug)
            .values(view_count=Article.view_count + 1)
        )
        await self.db.commit()
