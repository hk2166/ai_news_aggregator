"""Search and discovery service for articles."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.article import Article, Source, Channel


def search_articles(
    db: Session,
    query: str = "",
    source: Optional[str] = None,
    tags: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict:
    """Search articles with full-text search and filters."""
    q = db.query(
        Article,
        Source.name.label("source_name"),
        Channel.name.label("channel_name")
    ).join(Source, Article.source_id == Source.id) \
     .outerjoin(Channel, Article.channel_id == Channel.id)
    
    # Full-text search
    if query:
        search_query = " & ".join(query.split())
        q = q.filter(
            text("search_vector @@ to_tsquery('english', :query)")
        ).params(query=search_query)
        q = q.add_columns(
            text("ts_rank(search_vector, to_tsquery('english', :query)) as rank")
        ).params(query=search_query)
        q = q.order_by(text("rank DESC"))
    else:
        q = q.order_by(Article.published_at.desc())
    
    # Filters
    if source:
        q = q.filter(Source.name == source)
    if tags:
        q = q.filter(Article.tags.op('&&')(tags))
    if date_from:
        q = q.filter(Article.published_at >= date_from)
    if date_to:
        q = q.filter(Article.published_at <= date_to)
    
    q = q.filter(Article.is_processed == True)
    
    total = q.count()
    results = q.limit(limit).offset(offset).all()
    
    articles = []
    for row in results:
        article = row[0]
        articles.append({
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "tags": article.tags or [],
            "source": row[1],
            "channel": row[2],
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "view_count": article.view_count
        })
    
    pages = (total + limit - 1) // limit
    page = (offset // limit) + 1
    
    return {
        "results": articles,
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit
    }


def get_related_articles(db: Session, article_id: int, limit: int = 5) -> List[Dict]:
    """Find articles related to the given article based on shared tags."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article or not article.tags:
        return []
    
    related = db.query(
        Article,
        Source.name.label("source_name"),
        Channel.name.label("channel_name")
    ).join(Source, Article.source_id == Source.id) \
     .outerjoin(Channel, Article.channel_id == Channel.id) \
     .filter(
        Article.id != article_id,
        Article.is_processed == True,
        Article.tags.op('&&')(article.tags)
    ).order_by(
        (Article.source_id == article.source_id).desc(),
        Article.published_at.desc()
    ).limit(limit).all()
    
    results = []
    for row in related:
        art = row[0]
        shared_tags = list(set(art.tags or []) & set(article.tags or []))
        results.append({
            "id": art.id,
            "title": art.title,
            "url": art.url,
            "summary": art.summary,
            "tags": art.tags or [],
            "shared_tags": shared_tags,
            "source": row[1],
            "channel": row[2],
            "published_at": art.published_at.isoformat() if art.published_at else None
        })
    
    return results


def get_trending_topics(db: Session, days: int = 7, limit: int = 20) -> List[Dict]:
    """Get trending topics (tags) over the specified time period."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    articles = db.query(Article).filter(
        Article.published_at >= cutoff,
        Article.is_processed == True,
        Article.tags.isnot(None)
    ).all()
    
    tag_counts = {}
    for article in articles:
        for tag in (article.tags or []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    
    return [
        {
            "tag": tag,
            "count": count,
            "avg_per_day": round(count / days, 1)
        }
        for tag, count in sorted_tags[:limit]
    ]


def get_popular_articles(db: Session, days: int = 7, limit: int = 10) -> List[Dict]:
    """Get most popular articles based on view count."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    articles = db.query(
        Article,
        Source.name.label("source_name"),
        Channel.name.label("channel_name")
    ).join(Source, Article.source_id == Source.id) \
     .outerjoin(Channel, Article.channel_id == Channel.id) \
     .filter(
        Article.published_at >= cutoff,
        Article.is_processed == True
    ).order_by(Article.view_count.desc()).limit(limit).all()
    
    results = []
    for row in articles:
        art = row[0]
        results.append({
            "id": art.id,
            "title": art.title,
            "url": art.url,
            "summary": art.summary,
            "tags": art.tags or [],
            "source": row[1],
            "channel": row[2],
            "published_at": art.published_at.isoformat() if art.published_at else None,
            "view_count": art.view_count
        })
    
    return results


def increment_view_count(db: Session, article_id: int):
    """Increment the view count for an article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if article:
        article.view_count = (article.view_count or 0) + 1
        db.commit()


def update_search_vectors(db: Session):
    """Update search vectors for all articles."""
    db.execute(text("""
        UPDATE articles
        SET search_vector = 
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(summary, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(content_text, '')), 'C')
        WHERE search_vector IS NULL OR is_processed = TRUE
    """))
    db.commit()
