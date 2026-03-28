from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    source_type = Column(String(50))


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    name = Column(String(200))
    external_id = Column(String(200), unique=True)


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    title = Column(String(500))
    url = Column(String(1000), unique=True)
    content_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True, default=list)
    is_processed = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # Full-text search vector (combines title + summary + content)
    search_vector = Column(TSVECTOR)
    
    # View count for popularity ranking
    view_count = Column(Integer, default=0)
    
    # Indexes for better performance
    __table_args__ = (
        Index('idx_article_search', 'search_vector', postgresql_using='gin'),
        Index('idx_article_published', 'published_at'),
    )
