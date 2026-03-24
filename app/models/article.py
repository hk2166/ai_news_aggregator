from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class Source(Base):
    """A news source type — e.g., 'YouTube', 'OpenAI Blog', 'ArXiv'"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)        # "YouTube"
    source_type = Column(String(50))                # "youtube" | "blog" | "rss" | "arxiv"
    base_url = Column(String(500), nullable=True)   # "https://youtube.com"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Channel(Base):
    """A specific channel/feed within a source — e.g., a YouTube channel."""
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    name = Column(String(200))                      # "Fireship"
    external_id = Column(String(200))               # Channel ID like "UCsBjURrPoezykLs9EqgamOA"
    url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Article(Base):
    """
    Unified content model — a YouTube video, blog post, or paper.
    Everything the user consumes is an Article.
    """
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)

    # Content
    title = Column(String(500))
    url = Column(String(1000), unique=True)         # Dedupe key - prevents duplicates
    external_id = Column(String(200))               # video_id, post slug, etc.
    content_text = Column(Text, nullable=True)      # Transcript or full blog text
    summary = Column(Text, nullable=True)           # AI-generated (Phase 3)
    thumbnail_url = Column(String(1000), nullable=True)

    # Metadata
    published_at = Column(DateTime)
    tags = Column(JSON, default=list)               # ["LLMs", "GPT-5", "reasoning"]
    embedding = Column(JSON, nullable=True)         # Vector as list[float] (Phase 3)

    created_at = Column(DateTime, server_default=func.now())
