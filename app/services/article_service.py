from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from app.models.base import SessionLocal
from app.models.article import Article, Source, Channel


@dataclass
class ArticleInput:
    title: str
    url: str
    published_at: datetime
    source_name: str
    source_type: str
    content_text: Optional[str] = None
    channel_external_id: Optional[str] = None
    channel_name: Optional[str] = None


def from_scraped_article(a) -> ArticleInput:
    return ArticleInput(
        title=a.title, url=a.url, content_text=a.content_text,
        published_at=a.published_at, source_name="openai", source_type="blog",
    )


def from_channel_video(v, channel_id: str) -> ArticleInput:
    return ArticleInput(
        title=v.title, url=v.url, content_text=v.transcript,
        published_at=v.published_at, source_name="youtube", source_type="youtube",
        channel_external_id=channel_id, channel_name=channel_id,
    )


def save_articles(articles: list[ArticleInput]) -> dict:
    db = SessionLocal()
    saved = skipped = 0

    try:
        for item in articles:
            source = db.query(Source).filter(Source.name == item.source_name).first()
            if not source:
                source = Source(name=item.source_name, source_type=item.source_type)
                db.add(source)
                db.flush()

            channel_id = None
            if item.channel_external_id:
                channel = db.query(Channel).filter(Channel.external_id == item.channel_external_id).first()
                if not channel:
                    channel = Channel(source_id=source.id, external_id=item.channel_external_id,
                                      name=item.channel_name or item.channel_external_id)
                    db.add(channel)
                    db.flush()
                channel_id = channel.id

            db.add(Article(source_id=source.id, channel_id=channel_id, title=item.title,
                           url=item.url, content_text=item.content_text, published_at=item.published_at))
            try:
                db.flush()
                saved += 1
            except IntegrityError:
                db.rollback()
                skipped += 1

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return {"saved": saved, "skipped": skipped}


def get_recent_articles(limit: int = 20) -> list[Article]:
    db = SessionLocal()
    try:
        return db.query(Article).order_by(Article.published_at.desc()).limit(limit).all()
    finally:
        db.close()
