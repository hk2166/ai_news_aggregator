from sqlalchemy.orm import Session
from app.models.article import Article
from app.scrapers.youtube import ChannelVideo


def save_videos_to_db(
    db: Session, 
    videos: list[ChannelVideo], 
    source_id: int, 
    channel_id: int
) -> int:
    """Save scraped YouTube videos to the articles table, skipping duplicates.
    
    Args:
        db: Database session
        videos: List of ChannelVideo objects from the scraper
        source_id: ID of the Source record (e.g., YouTube source)
        channel_id: ID of the Channel record (e.g., specific YouTube channel)
    
    Returns:
        Number of new articles saved
    """
    saved = 0
    for video in videos:
        # Skip if already exists (dedupe by URL)
        exists = db.query(Article).filter(Article.url == video.url).first()
        if exists:
            continue

        article = Article(
            source_id=source_id,
            channel_id=channel_id,
            title=video.title,
            url=video.url,
            external_id=video.video_id,
            content_text=video.transcript,  # The transcript from YouTube
            published_at=video.published_at,
            summary=None,       # Will be filled in Phase 3 (AI summarizer)
            embedding=None,     # Will be filled in Phase 3 (embedding generator)
        )
        db.add(article)
        saved += 1

    db.commit()
    return saved
