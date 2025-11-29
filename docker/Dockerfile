FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PDM or just use pip with pyproject.toml (using pip for simplicity here with standard requirements)
# We will generate requirements.txt from pyproject.toml or just install directly if using a tool like pip-tools.
# For simplicity in this environment, let's assume we can install from pyproject.toml using pip if we had a build tool,
# but to be safe and standard, I'll write a requirements.txt based on pyproject.toml content or just install packages.
# Actually, let's use a multi-stage build or just install the dependencies.
# Since I created pyproject.toml, I should probably use a tool that understands it, or just list deps in requirements.txt for Docker simplicity if I don't want to install PDM.
# Let's stick to standard pip install for now.

COPY pyproject.toml .
# We can use `pip install .` if we have a build backend, but let's just install the libs manually to be robust without extra tools
# Or better, let's just use a requirements.txt for Docker to avoid complexity.
# I will create a requirements.txt in the next step or just inline the install.
# Let's use `pip install` with the packages listed.

RUN pip install --no-cache-dir \
    fastapi[all] \
    sqlalchemy \
    alembic \
    asyncpg \
    pydantic-settings \
    python-jose[cryptography] \
    passlib[bcrypt] \
    jinja2 \
    redis \
    markdown \
    pygments \
    psycopg2-binary \
    email-validator \
    httpx \
    pytest \
    pytest-asyncio

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
