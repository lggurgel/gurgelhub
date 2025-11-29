FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata files first for better caching
COPY pyproject.toml README.md ./

# Install dependencies
# We use `pip install .` which reads pyproject.toml
# This requires README.md to be present
RUN pip install --no-cache-dir .

# Copy the rest of the application
COPY . .

# Expose port (Railway sets PORT env var, but good to document)
EXPOSE 8000

# Command to run the application
# Using shell form to allow variable expansion if needed, but exec form is generally better.
# Railway passes $PORT, so we use sh -c to expand it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
