from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

class ArticleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    tags: List[str] = []
    is_published: bool = False

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None

class ArticleInDBBase(ArticleBase):
    id: UUID
    view_count: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Article(ArticleInDBBase):
    pass

class ArticleList(BaseModel):
    items: List[Article]
    total: int
    page: int
    per_page: int
