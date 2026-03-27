from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.base import SessionLocal
from app.models.article import Article, Source, Channel
from app.models.user import User
from app.scheduler import start_scheduler
from app.services.search_service import (
    search_articles,
    get_related_articles,
    get_trending_topics,
    get_popular_articles,
    increment_view_count
)
import pathlib

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Start the background scheduler
scheduler = None

@app.on_event("startup")
async def startup_event():
    global scheduler
    scheduler = start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    if scheduler:
        scheduler.shutdown()

HTML_PATH = pathlib.Path(__file__).parent / "index.html"


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PATH.read_text()


@app.get("/articles")
def get_articles(limit: int = 30, source: str = None):
    db = SessionLocal()
    try:
        q = db.query(Article, Source.name.label("source_name"), Channel.name.label("channel_name")) \
              .join(Source, Article.source_id == Source.id) \
              .outerjoin(Channel, Article.channel_id == Channel.id)
        if source:
            q = q.filter(Source.name == source)
        rows = q.order_by(Article.published_at.desc()).limit(limit).all()

        return [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "summary": a.summary,
                "tags": a.tags or [],
                "source": source_name,
                "channel": channel_name,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a, source_name, channel_name in rows
        ]
    finally:
        db.close()


class SubscribeRequest(BaseModel):
    name: str
    email: str


@app.post("/subscribe")
def subscribe(req: SubscribeRequest):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == req.email).first()
        if existing:
            return {"ok": False, "reason": "already_subscribed"}
        db.add(User(name=req.name, email=req.email))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    db = SessionLocal()
    try:
        # Check database connection
        article_count = db.query(Article).count()
        latest_article = db.query(Article).order_by(Article.created_at.desc()).first()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_articles": article_count,
            "latest_article": latest_article.created_at.isoformat() if latest_article else None,
            "scheduler": "running" if scheduler else "not_started"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    finally:
        db.close()


@app.post("/admin/trigger-scrape")
def trigger_manual_scrape():
    """Manually trigger a scrape (for testing/admin)"""
    from app.scheduler import scrape_all_sources
    try:
        # Run in background to avoid blocking
        import threading
        thread = threading.Thread(target=scrape_all_sources)
        thread.start()
        return {"status": "triggered", "message": "Scraping started in background"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/search")
def search(
    q: str = "",
    source: Optional[str] = None,
    tags: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
    page: int = 1
):
    """
    Search articles with full-text search and filters.
    
    Query Parameters:
    - q: Search query (searches title, summary, content)
    - source: Filter by source (e.g., "openai", "youtube")
    - tags: Comma-separated tags (e.g., "gpt-4,research")
    - date_from: ISO date string (e.g., "2026-03-01")
    - date_to: ISO date string
    - limit: Results per page (default 20)
    - page: Page number (default 1)
    
    Example:
        GET /search?q=GPT-4&source=openai&tags=gpt-4,research&limit=10&page=1
    """
    db = SessionLocal()
    try:
        # Parse tags
        tag_list = tags.split(",") if tags else None
        
        # Parse dates
        date_from_obj = datetime.fromisoformat(date_from) if date_from else None
        date_to_obj = datetime.fromisoformat(date_to) if date_to else None
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Search
        results = search_articles(
            db=db,
            query=q,
            source=source,
            tags=tag_list,
            date_from=date_from_obj,
            date_to=date_to_obj,
            limit=limit,
            offset=offset
        )
        
        return results
    finally:
        db.close()


@app.get("/articles/{article_id}/related")
def get_related(article_id: int, limit: int = 5):
    """
    Get articles related to the specified article.
    
    Example:
        GET /articles/123/related?limit=5
    """
    db = SessionLocal()
    try:
        related = get_related_articles(db, article_id, limit)
        return {"related": related}
    finally:
        db.close()


@app.get("/trending")
def get_trending(days: int = 7, limit: int = 20):
    """
    Get trending topics (tags) over the specified period.
    
    Query Parameters:
    - days: Number of days to analyze (default 7)
    - limit: Number of topics to return (default 20)
    
    Example:
        GET /trending?days=7&limit=20
    """
    db = SessionLocal()
    try:
        trending = get_trending_topics(db, days, limit)
        return {"trending": trending, "period_days": days}
    finally:
        db.close()


@app.get("/popular")
def get_popular(days: int = 7, limit: int = 10):
    """
    Get most popular articles based on view count.
    
    Example:
        GET /popular?days=7&limit=10
    """
    db = SessionLocal()
    try:
        popular = get_popular_articles(db, days, limit)
        return {"popular": popular, "period_days": days}
    finally:
        db.close()


@app.post("/articles/{article_id}/view")
def track_view(article_id: int):
    """
    Track that a user viewed an article.
    
    Call this when user clicks on an article.
    
    Example:
        POST /articles/123/view
    """
    db = SessionLocal()
    try:
        increment_view_count(db, article_id)
        return {"status": "success"}
    finally:
        db.close()