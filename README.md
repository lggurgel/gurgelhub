# Markdown Article Publishing Platform

A production-grade content management system built with FastAPI, PostgreSQL (Full-Text Search), and Server-Side Rendering (Jinja2 + HTMX).

## Features

- **Public Portal**:
    - Browse and read Markdown articles with syntax highlighting.
    - **Full-Text Search**: Fast, relevant search with highlighting, stemming, and ranking using PostgreSQL `tsvector`.
    - Responsive design with TailwindCSS.
- **Admin Portal**:
    - Secure authentication (JWT).
    - Dashboard with article statistics.
    - Create/Edit articles with Markdown support.
    - Draft/Publish workflow.

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL 15+ (with `pg_trgm` and `unaccent` extensions)
- **Frontend**: Jinja2 Templates, HTMX, TailwindCSS (CDN)
- **Infrastructure**: Docker, Redis (for caching/sessions)

## Local Setup

1.  **Clone the repository**
2.  **Start the environment**:
    ```bash
    docker-compose -f docker/docker-compose.yml up --build
    ```
    The application will be available at `http://localhost:8000`.

3.  **Run Migrations**:
    Migrations run automatically on startup, but you can run them manually:
    ```bash
    docker-compose -f docker/docker-compose.yml exec web alembic upgrade head
    ```

4.  **Create Admin User**:
    You can create an initial admin user via the database or a script.
    The default admin credentials in `docker-compose.yml` are:
    - Username: `admin`
    - Password: `password` (Hash in env is for "secret")

## Full-Text Search Implementation

We use PostgreSQL's native full-text search capabilities:
- **Vector Generation**: A `search_vector` column is automatically generated from Title (Weight A), Description (Weight B), Content (Weight C), and Tags (Weight B).
- **Indexing**: A GIN index is used for fast lookups.
- **Ranking**: Results are ranked using `ts_rank_cd`.
- **Highlighting**: `ts_headline` is used to generate snippets with `<mark>` tags.

## Deployment (Railway)

This project is configured for deployment on Railway.

1.  Connect your GitHub repository to Railway.
2.  Add a PostgreSQL database service.
3.  Add a Redis service.
4.  Set the environment variables in Railway:
    - `DATABASE_URL`: (Provided by Railway Postgres)
    - `REDIS_URL`: (Provided by Railway Redis)
    - `SECRET_KEY`: Generate a secure random string.
    - `ADMIN_USERNAME`: Your admin username.
    - `ADMIN_PASSWORD_HASH`: Bcrypt hash of your password.
    - `ENVIRONMENT`: `production`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
