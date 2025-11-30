import os
from pydantic import ValidationError

# Mock environment variables
os.environ["DATABASE_URL"] = " postgresql://user:pass@host:5432/db "
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["SECRET_KEY"] = "secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD_HASH"] = "hash"

try:
    from app.config import settings
    print(f"Original URL in env: '{os.environ['DATABASE_URL']}'")
    print(f"Parsed URL in settings: '{settings.DATABASE_URL}'")

    expected = "postgresql+asyncpg://user:pass@host:5432/db"
    if settings.DATABASE_URL == expected:
        print("SUCCESS: URL was correctly stripped and transformed.")
    else:
        print(f"FAILURE: Expected '{expected}', got '{settings.DATABASE_URL}'")

except ValidationError as e:
    print(f"Validation Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")
