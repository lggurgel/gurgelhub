from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError

def test_url(url, name):
    print(f"Testing {name}: '{url}'")
    try:
        u = make_url(url)
        print(f"  Success: {u}")
    except ArgumentError as e:
        print(f"  Failed: {e}")
    except Exception as e:
        print(f"  Failed with unexpected error: {e}")

# Test cases
test_url("postgresql://user:pass@host:5432/db", "Standard URL")
test_url(" postgresql://user:pass@host:5432/db", "Leading whitespace")
test_url("postgresql://user:pass@host:5432/db ", "Trailing whitespace")
test_url("postgresql://user:p@ssword@host:5432/db", "Special char in password (unencoded)")
test_url("postgresql://postgr", "Incomplete URL")
