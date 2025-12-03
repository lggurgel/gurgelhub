from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes import articles, search, auth, admin, comments
from app.config import settings

app = FastAPI(
    title="Markdown Article Platform",
    description="A platform for publishing and searching markdown articles.",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000", # If we were using a separate frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(articles.router, prefix="/api/v1/articles", tags=["articles"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(comments.router, prefix="/api/v1", tags=["comments"])

# Web Routes (SSR)
from app.web import routes as web_routes
from app.web import admin_routes
app.include_router(web_routes.router)
app.include_router(admin_routes.router)

# Static Files (for SSR)
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
