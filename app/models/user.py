from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class User(Base):
    """A registered user who receives personalized news."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    name = Column(String(100))
    hashed_password = Column(String(255))

    # Preferences (set during onboarding)
    preferred_topics = Column(JSON, default=list)    # ["LLMs", "robotics"]
    preferred_sources = Column(JSON, default=list)   # ["YouTube", "ArXiv"]

    # Delivery settings
    delivery_method = Column(String(20), default="email")  # "email" | "telegram"
    delivery_time = Column(String(5), default="08:00")     # When to send digest (HH:MM)
    telegram_chat_id = Column(String(100), nullable=True)

    # ML - average embedding of liked content for recommendations
    taste_vector = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


class UserInteraction(Base):
    """
    Tracks every time a user interacts with an article.
    This is the feedback loop that powers recommendations.
    
    Interaction types:
    - "view": User opened the article
    - "like": User liked the article
    - "save": User saved/bookmarked the article
    - "dismiss": User dismissed/disliked the article (negative signal)
    """
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article_id = Column(Integer, ForeignKey("articles.id"))
    interaction_type = Column(String(20))            # "view" | "like" | "save" | "dismiss"
    created_at = Column(DateTime, server_default=func.now())
