from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import dependencies
from app.database import get_db
from app.models.article import Article
from app.schemas.article import Article as ArticleSchema

router = APIRouter()

@router.get("/stats", dependencies=[Depends(dependencies.get_current_active_superuser)])
async def get_stats(
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get dashboard statistics.
    """
    # Total articles
    total_query = select(func.count()).select_from(Article)
    total_articles = await db.scalar(total_query)

    # Total views
    views_query = select(func.sum(Article.view_count)).select_from(Article)
    total_views = await db.scalar(views_query) or 0

    # Most viewed
    popular_query = select(Article).order_by(Article.view_count.desc()).limit(5)
    popular_result = await db.execute(popular_query)
    popular_articles = popular_result.scalars().all()

    return {
        "total_articles": total_articles,
        "total_views": total_views,
        "popular_articles": [ArticleSchema.model_validate(a) for a in popular_articles]
    }

@router.get("/articles", response_model=List[ArticleSchema], dependencies=[Depends(dependencies.get_current_active_superuser)])
async def list_all_articles(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List ALL articles (including drafts) for admin.
    """
    query = select(Article).order_by(Article.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
