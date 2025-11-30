import os

# Set environment variables BEFORE importing app.config because it instantiates Settings() on import
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["SECRET_KEY"] = "dummy"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD_HASH"] = "hash"

from app.config import Settings

def test_database_url_validation():
    # Test case 1: Standard postgresql:// URL
    # (Env vars already set above for import, but we can reset for clarity or just use Settings() which reads env)

    settings = Settings()
    print(f"Input: postgresql://user:pass@localhost:5432/db")
    print(f"Output: {settings.DATABASE_URL}")

    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"
    print("SUCCESS: URL was correctly transformed.")

    # Test case 2: Already correct URL
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
    settings = Settings()
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"
    print("SUCCESS: Correct URL was preserved.")

    # Test case 3: postgres:// URL (common in some providers)
    os.environ["DATABASE_URL"] = "postgres://user:pass@localhost:5432/db"
    settings = Settings()
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"
    print("SUCCESS: postgres:// URL was correctly transformed.")

if __name__ == "__main__":
    test_database_url_validation()
