from typing import Any, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import SearchResponse
from app.services.search import SearchService

router = APIRouter()

@router.get("/", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Full-text search for articles.
    """
    service = SearchService(db)
    items, total, duration = await service.search_articles(q, page=page, per_page=per_page)

    total_pages = (total + per_page - 1) // per_page

    return {
        "query": q,
        "results": items,
        "total_count": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "search_time_ms": duration
    }

@router.get("/suggestions", response_model=List[str])
async def search_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get search suggestions.
    """
    service = SearchService(db)
    return await service.get_suggestions(q, limit=limit)
