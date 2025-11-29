from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import dependencies
from app.core import security
from app.database import get_db
from app.models.user import User
from app.services.article import ArticleService
from app.services.auth import AuthService
from app.schemas.article import ArticleCreate, ArticleUpdate

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

# Login

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid credentials"}
        )

    # Set cookie
    access_token = security.create_access_token(subject=user.username)
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

# Dashboard & CRUD
# Note: We need a dependency to check cookie auth for these routes
# Since `dependencies.get_current_user` looks for Authorization header, we might need a cookie extractor or just JS to set header?
# For SSR, cookies are better. Let's create a cookie dependency or just use a simple one here.

async def get_current_user_from_cookie(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        return await dependencies.get_current_user(token, db)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    service = ArticleService(db)
    articles, _ = await service.get_articles(limit=100, published_only=False)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "articles": articles, "user": user}
    )

@router.get("/articles/new", response_class=HTMLResponse)
async def new_article_page(
    request: Request,
    user: User = Depends(get_current_user_from_cookie)
):
    return templates.TemplateResponse("admin/edit.html", {"request": request, "article": None})

@router.post("/articles/new", response_class=HTMLResponse)
async def create_article(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    content: str = Form(...),
    description: str = Form(None),
    tags: str = Form(""),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    service = ArticleService(db)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    article_in = ArticleCreate(
        title=title,
        slug=slug,
        content=content,
        description=description,
        tags=tag_list,
        is_published=is_published
    )

    try:
        await service.create_article(article_in)
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "admin/edit.html",
            {"request": request, "error": str(e), "article": article_in} # article_in is not exactly Article model but close enough for form repopulation if we handle it
        )

@router.get("/articles/{slug}/edit", response_class=HTMLResponse)
async def edit_article_page(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    service = ArticleService(db)
    article = await service.get_article_by_slug(slug)
    if not article:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse("admin/edit.html", {"request": request, "article": article})

@router.post("/articles/{slug}/edit", response_class=HTMLResponse)
async def update_article(
    request: Request,
    slug: str,
    title: str = Form(...),
    content: str = Form(...),
    description: str = Form(None),
    tags: str = Form(""),
    is_published: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    service = ArticleService(db)
    article = await service.get_article_by_slug(slug)
    if not article:
        raise HTTPException(status_code=404)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    article_in = ArticleUpdate(
        title=title,
        content=content,
        description=description,
        tags=tag_list,
        is_published=is_published
    )

    await service.update_article(article.id, article_in)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
