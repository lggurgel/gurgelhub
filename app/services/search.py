import time
from typing import List, Tuple
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.schemas.search import SearchResultItem

class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_articles(
        self, query: str, page: int = 1, per_page: int = 10
    ) -> Tuple[List[SearchResultItem], int, float]:
        start_time = time.time()

        # Sanitize and prepare query
        # We use plainto_tsquery for simple input, or we can format it for prefix matching
        # For "search as you type" prefix matching on the last word is good.
        # Let's try to construct a query that supports prefix matching for the last term.

        terms = query.strip().split()
        if not terms:
            return [], 0, 0.0

        # Construct tsquery string: "term1 & term2 & term3:*"
        # This is a simple approach. For more complex queries we might need more logic.
        ts_query_parts = []
        for i, term in enumerate(terms):
            if i == len(terms) - 1:
                ts_query_parts.append(f"{term}:*") # Prefix match last term
            else:
                ts_query_parts.append(term)

        ts_query_str = " & ".join(ts_query_parts)

        # Raw SQL for maximum control over ranking and highlighting
        # We use SQLAlchemy text()

        sql = text("""
            WITH search_query AS (
                SELECT to_tsquery('english', :query) as query
            ),
            ranked_articles AS (
                SELECT
                    id,
                    title,
                    slug,
                    description,
                    content,
                    tags,
                    published_at,
                    view_count,
                    ts_rank_cd(search_vector, query) as rank,
                    ts_headline('english', content, query, 'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15') as snippet
                FROM articles, search_query
                WHERE search_vector @@ query
                AND is_published = true
            ),
            total_count AS (
                SELECT count(*) as count FROM ranked_articles
            )
            SELECT
                r.*,
                t.count
            FROM ranked_articles r, total_count t
            ORDER BY rank DESC
            OFFSET :skip LIMIT :limit
        """)

        skip = (page - 1) * per_page

        result = await self.db.execute(
            sql,
            {"query": ts_query_str, "skip": skip, "limit": per_page}
        )

        rows = result.fetchall()

        if not rows:
            return [], 0, (time.time() - start_time) * 1000

        total_count = rows[0].count
        items = []

        for row in rows:
            items.append(SearchResultItem(
                id=row.id,
                title=row.title,
                slug=row.slug,
                description=row.description,
                snippet=row.snippet, # ts_headline result
                tags=row.tags,
                published_at=row.published_at,
                view_count=row.view_count,
                relevance_score=row.rank
            ))

        duration_ms = (time.time() - start_time) * 1000
        return items, total_count, duration_ms

    async def get_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        # Simple implementation using ILIKE on title for now,
        # or we could use pg_trgm if we had it set up on a separate column for suggestions.
        # The requirements mentioned pg_trgm.
        # Let's assume we can use it on title.

        if not partial_query:
            return []

        sql = text("""
            SELECT title
            FROM articles
            WHERE title ILIKE :query
            AND is_published = true
            ORDER BY title <-> :raw_query
            LIMIT :limit
        """)

        result = await self.db.execute(
            sql,
            {"query": f"%{partial_query}%", "raw_query": partial_query, "limit": limit}
        )

        return [row.title for row in result.scalars().all()]
