from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Text, Boolean, DateTime, Integer, Index, func
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Article(Base):
    __tablename__ = "articles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Full-text search vector (generated column handled by migration)
    # We define it here for SQLAlchemy to know about it, but the actual generation logic is in the migration
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)

    __table_args__ = (
        Index('idx_articles_search', 'search_vector', postgresql_using='gin'),
    )
