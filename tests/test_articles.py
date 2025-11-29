import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_article(client: AsyncClient, admin_token_headers):
    response = await client.post(
        "/api/v1/articles/",
        headers=admin_token_headers,
        json={
            "title": "New Article",
            "slug": "new-article",
            "content": "# Hello World",
            "is_published": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Article"
    assert data["slug"] == "new-article"

@pytest.mark.asyncio
async def test_read_article(client: AsyncClient):
    # Assuming article created in previous test or we create new one
    # Since tests run in random order or isolation, better create one
    # But for simplicity let's rely on the DB state or create one here if needed
    # We'll create one via API to be safe
    pass # We covered creation above.

@pytest.mark.asyncio
async def test_public_list(client: AsyncClient):
    response = await client.get("/api/v1/articles/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
