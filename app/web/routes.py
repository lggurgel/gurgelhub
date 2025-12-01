from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.article import ArticleService
from app.services.search import SearchService
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension
from markdown.extensions.nl2br import Nl2BrExtension
from markdown.extensions.sane_lists import SaneListExtension
from markdown.extensions.smarty import SmartyExtension
from markdown.extensions.abbr import AbbrExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.md_in_html import MarkdownInHtmlExtension

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def create_markdown_renderer():
    """Create a fully-featured Markdown renderer with all extensions configured."""
    return markdown.Markdown(
        extensions=[
            # Fenced code blocks with language detection
            FencedCodeExtension(),
            # Syntax highlighting with Pygments
            CodeHiliteExtension(
                css_class='codehilite',
                linenums=False,
                guess_lang=True,
                pygments_style='monokai',
                noclasses=False,
                use_pygments=True
            ),
            # GFM-style tables
            TableExtension(),
            # Table of contents with anchor links
            TocExtension(
                permalink=True,
                permalink_class='anchor-link',
                permalink_title='Link to this section',
                slugify=lambda value, separator: value.lower().replace(' ', separator).replace('.', '')
            ),
            # Convert newlines to <br>
            Nl2BrExtension(),
            # Better list handling
            SaneListExtension(),
            # Smart quotes and dashes
            SmartyExtension(
                smart_quotes=True,
                smart_dashes=True,
                smart_ellipses=True
            ),
            # Abbreviations
            AbbrExtension(),
            # Footnotes
            FootnoteExtension(
                BACKLINK_TEXT='↩',
                SEPARATOR='-'
            ),
            # Add attributes to elements
            AttrListExtension(),
            # Definition lists
            DefListExtension(),
            # Markdown inside HTML blocks
            MarkdownInHtmlExtension(),
        ],
        extension_configs={},
        output_format='html5'
    )


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db)
):
    service = ArticleService(db)
    articles, total = await service.get_articles(skip=(page-1)*10, limit=10, published_only=True)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "page": page,
            "total": total,
            "has_next": (page * 10) < total,
            "has_prev": page > 1
        }
    )


@router.get("/article/{slug}", response_class=HTMLResponse)
async def article_detail(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    service = ArticleService(db)
    article = await service.get_article_by_slug(slug)

    if not article or not article.is_published:
        raise HTTPException(status_code=404, detail="Article not found")

    # Render Markdown with full feature set
    md = create_markdown_renderer()
    content_html = md.convert(article.content)

    # Increment view count (fire and forget or await)
    await service.increment_view_count(slug)

    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "article": article,
            "content_html": content_html
        }
    )


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    page: int = 1,
    db: AsyncSession = Depends(get_db)
):
    service = SearchService(db)
    results = []
    total = 0
    duration = 0

    if q:
        results, total, duration = await service.search_articles(q, page=page, per_page=10)

    # Check if HTMX request
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/search_results.html",
            {
                "request": request,
                "results": results,
                "query": q,
                "total": total,
                "duration": duration
            }
        )

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "results": results,
            "query": q,
            "total": total,
            "duration": duration
        }
    )


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request}
    )
