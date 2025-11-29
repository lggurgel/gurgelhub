from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class SearchResultItem(BaseModel):
    id: UUID
    title: str
    slug: str
    description: Optional[str]
    snippet: str
    tags: List[str]
    published_at: Optional[datetime]
    view_count: int
    relevance_score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_count: int
    page: int
    per_page: int
    total_pages: int
    search_time_ms: float
