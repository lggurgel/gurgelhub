from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import dependencies
from app.database import get_db
from app.models.user import User
from app.schemas.article import Article, ArticleCreate, ArticleUpdate, ArticleList
from app.services.article import ArticleService

router = APIRouter()

# Public Endpoints

@router.get("/", response_model=ArticleList)
async def list_articles(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List published articles.
    """
    service = ArticleService(db)
    skip = (page - 1) * per_page
    items, total = await service.get_articles(skip=skip, limit=per_page, published_only=True)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page
    }

@router.get("/{slug}", response_model=Article)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific article by slug.
    """
    service = ArticleService(db)
    article = await service.get_article_by_slug(slug)
    if not article or not article.is_published:
        # Check if admin to allow preview?
        # For now, strict public view.
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.post("/{slug}/view")
async def increment_view(
    slug: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Increment view count for an article.
    """
    service = ArticleService(db)
    await service.increment_view_count(slug)
    return {"status": "ok"}

# Admin Endpoints

@router.post("/", response_model=Article, dependencies=[Depends(dependencies.get_current_active_superuser)])
async def create_article(
    article_in: ArticleCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create new article.
    """
    service = ArticleService(db)
    # Check slug uniqueness
    existing = await service.get_article_by_slug(article_in.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    return await service.create_article(article_in)

@router.put("/{article_id}", response_model=Article, dependencies=[Depends(dependencies.get_current_active_superuser)])
async def update_article(
    article_id: UUID,
    article_in: ArticleUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update an article.
    """
    service = ArticleService(db)
    article = await service.update_article(article_id, article_in)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.delete("/{article_id}", dependencies=[Depends(dependencies.get_current_active_superuser)])
async def delete_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete an article.
    """
    service = ArticleService(db)
    success = await service.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "ok"}
