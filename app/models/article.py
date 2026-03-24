from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
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
    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
