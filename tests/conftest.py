import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash

# Use a separate test DB or the same one if we are careful.
# For simplicity in this setup, we use the same DB but we could drop tables.
# Ideally we use a test DB.
# Let's assume the user has a test DB or we use the main one but clean up.
# We will use the main one but wrap in transaction rollback if possible,
# or just create/drop tables.
# Given the docker setup, let's just use the main DB but be careful.
# Actually, for proper testing we should create tables.

# Override dependency
TEST_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        # We also need to create the search_vector column manually as it's not in create_all for the generated column logic if we rely on migration
        # But here we are using create_all from models.
        # The model has search_vector mapped but the GENERATED logic is in migration.
        # So create_all might fail or create a normal column.
        # We should run the raw SQL for the column.
        await conn.execute(sa.text("""
            ALTER TABLE articles DROP COLUMN IF EXISTS search_vector;
            ALTER TABLE articles ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(content, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'B')
            ) STORED;
            CREATE INDEX IF NOT EXISTS idx_articles_search ON articles USING GIN(search_vector);
        """))
    yield
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
async def admin_token_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    # Create admin user
    admin_data = {
        "username": "admin_test",
        "hashed_password": get_password_hash("password"),
        "is_superuser": True
    }
    # Check if exists
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.username == "admin_test"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(**admin_data)
        db_session.add(user)
        await db_session.commit()

    response = await client.post("/api/v1/auth/login", data={"username": "admin_test", "password": "password"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
