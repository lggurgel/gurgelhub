import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.services.article import ArticleService
from app.schemas.article import ArticleCreate

@pytest.mark.asyncio
async def test_search_articles(client: AsyncClient, db_session: AsyncSession, admin_token_headers):
    # Create articles
    service = ArticleService(db_session)

    a1 = await service.create_article(ArticleCreate(
        title="Python Tutorial",
        slug="python-tutorial",
        content="Learn Python programming language basics.",
        tags=["python", "coding"],
        is_published=True
    ))

    a2 = await service.create_article(ArticleCreate(
        title="Rust Guide",
        slug="rust-guide",
        content="Rust is a systems programming language.",
        tags=["rust"],
        is_published=True
    ))

    # Test basic search
    response = await client.get("/api/v1/search/?q=python")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) >= 1
    assert data["results"][0]["slug"] == "python-tutorial"

    # Test stemming (prog -> programming)
    response = await client.get("/api/v1/search/?q=prog")
    assert response.status_code == 200
    data = response.json()
    # Should match "programming" in content
    found = any(r["slug"] == "python-tutorial" for r in data["results"])
    assert found

    # Test ranking (Title match should be higher than content match)
    # Let's add another article with "Python" only in content
    a3 = await service.create_article(ArticleCreate(
        title="Other Lang",
        slug="other-lang",
        content="This mentions Python briefly.",
        is_published=True
    ))

    response = await client.get("/api/v1/search/?q=python")
    data = response.json()
    # a1 (Title match) should be first
    assert data["results"][0]["slug"] == "python-tutorial"

    # Test highlighting
    snippet = data["results"][0]["snippet"]
    assert "<mark>" in snippet
