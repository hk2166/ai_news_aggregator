# AI News Aggregator — Detailed Build Guide

> A step-by-step guide explaining **what** to build, **how** it works, and **why** each piece matters.

---

## What You Already Have ✅

### YouTube Scraper ([youtube.py](file:///Users/hemant/Desktop/news/ai/ai-news-agg/app/scrapers/youtube.py))

**What it does:** Fetches the latest videos from any YouTube channel using RSS feeds (no API key needed), then grabs the transcript of each video.

**How it works:**
1. Every YouTube channel has a hidden RSS feed at `youtube.com/feeds/videos.xml?channel_id=UCxxxx`
2. `feedparser` reads this XML and gives you a list of recent videos
3. You filter videos by publish time (e.g., last 24 hours)
4. For each video, `youtube-transcript-api` fetches the auto-generated or manual captions
5. You now have the full text of the video — this is a goldmine for an AI summarizer

**Current status:** Working. Has Pydantic models ([ChannelVideo](file:///Users/hemant/Desktop/news/ai/ai-news-agg/app/scrapers/youtube.py#15-22), [Transcript](file:///Users/hemant/Desktop/news/ai/ai-news-agg/app/scrapers/youtube.py#11-13)), proxy support, shorts filtering. This is roughly **15% of the full project** but it's the hardest scraper.

### Transcript Service ([transcript.py](file:///Users/hemant/Desktop/news/ai/ai-news-agg/app/sevices/transcript.py))

**What it does:** A standalone utility that takes any YouTube URL and returns the transcript with segment timestamps.

**Status:** Working but partially duplicated with youtube.py. Will be consolidated later.

---

## What You Need to Build 🔨

---

## Phase 1: Foundation & Config (~2 days)

### 1.1 — Fix folder typo + Create `app/__init__.py`

**Why:** `sevices` → `services`. Do this first before any imports reference it.

**How:**
```bash
# Rename the folder
mv app/sevices app/services

# Create the package init
touch app/__init__.py
```

---

### 1.2 — Create `.env` + Config loader

**Why:** You'll need secrets (DB password, API keys, SMTP credentials) and they should never be hardcoded. `pydantic-settings` validates env vars at startup — if something is missing, the app crashes immediately with a clear error instead of failing midway.

**How it works:** You create a `.env` file with key-value pairs, and a `Settings` class that reads them. Pydantic automatically validates types and gives errors for missing values.

**File: `.env`**
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_news

# LLM API (for summarization + embeddings later)
GEMINI_API_KEY=your-key-here

# Email delivery (Phase 5)
RESEND_API_KEY=your-key-here

# YouTube proxy (optional)
PROXY_USERNAME=
PROXY_PASSWORD=
```

**File: `app/config.py`**
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str

    # LLM
    gemini_api_key: str = ""  # Optional until Phase 3

    # Email
    resend_api_key: str = ""  # Optional until Phase 5

    # YouTube proxy
    proxy_username: str = ""
    proxy_password: str = ""

    # Scraping
    scrape_interval_hours: int = 6
    default_lookback_hours: int = 24

    class Config:
        env_file = ".env"

@lru_cache  # Singleton — loads .env once
def get_settings() -> Settings:
    return Settings()
```

**How to use it anywhere:**
```python
from app.config import get_settings
settings = get_settings()
print(settings.database_url)
```

---

### 1.3 — Database Models (SQLAlchemy + PostgreSQL)

**Why:** Right now your scraped data vanishes when the script ends. You need a database to:
- Store articles so you don't scrape the same thing twice
- Track which users liked what (for recommendations)
- Store embeddings (for ML-based similarity search)

**How PostgreSQL fits:** PostgreSQL is the best choice here because:
1. It has `pgvector` — a plugin that lets you store and search embeddings directly in SQL
2. SQLAlchemy gives you Python classes that map to database tables
3. Alembic handles schema changes over time (migrations)

**The key concept: Everything is an "Article"**
Whether it's a YouTube video, a blog post, or an ArXiv paper — they all become an `Article` row with the same fields. This makes the recommendation engine simpler (it just scores Articles, regardless of source).

**File: `app/models/base.py`**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

engine = create_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """Dependency: yields a DB session, auto-closes after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**File: `app/models/article.py`**
```python
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
    external_id = Column(String(200))               # "UCsBjURrPoezykLs9EqgamOA"
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
    url = Column(String(1000), unique=True)         # Dedupe key
    external_id = Column(String(200))               # video_id, post slug, etc.
    content_text = Column(Text, nullable=True)       # Transcript or full blog text
    summary = Column(Text, nullable=True)            # AI-generated (Phase 3)
    thumbnail_url = Column(String(1000), nullable=True)

    # Metadata
    published_at = Column(DateTime)
    tags = Column(JSON, default=list)                # ["LLMs", "GPT-5", "reasoning"]
    embedding = Column(JSON, nullable=True)          # Vector as list[float] (Phase 3)

    created_at = Column(DateTime, server_default=func.now())
```

**File: `app/models/user.py`**
```python
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

    # Delivery
    delivery_method = Column(String(20), default="email")  # "email" | "telegram"
    delivery_time = Column(String(5), default="08:00")     # when to send digest
    telegram_chat_id = Column(String(100), nullable=True)

    # ML
    taste_vector = Column(JSON, nullable=True)       # Average embedding of liked content

    created_at = Column(DateTime, server_default=func.now())


class UserInteraction(Base):
    """
    Tracks every time a user interacts with an article.
    This is the feedback loop that powers recommendations.
    """
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article_id = Column(Integer, ForeignKey("articles.id"))
    interaction_type = Column(String(20))            # "view" | "like" | "save" | "dismiss"
    created_at = Column(DateTime, server_default=func.now())
```

**How these tables relate:**
```
Source (1) ──→ (many) Channel ──→ (many) Article
User (1) ──→ (many) UserInteraction ←── (many) Article
```

---

### 1.4 — Wire YouTube Scraper to Database

**Why:** Make [scrape_channel()](file:///Users/hemant/Desktop/news/ai/ai-news-agg/app/scrapers/youtube.py#84-91) save results to the `articles` table instead of just printing them.

**How:** Create a service function that takes scraper output and writes to DB:

**File: `app/services/article_service.py`**
```python
from sqlalchemy.orm import Session
from app.models.article import Article
from app.scrapers.youtube import ChannelVideo

def save_videos_to_db(db: Session, videos: list[ChannelVideo], source_id: int, channel_id: int):
    """Save scraped videos to the articles table, skipping duplicates."""
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
            content_text=video.transcript,
            published_at=video.published_at,
            summary=None,       # Will be filled in Phase 3
            embedding=None,     # Will be filled in Phase 3
        )
        db.add(article)
        saved += 1

    db.commit()
    return saved
```

---

## Phase 2: More Scrapers (~2 days)

### 2.1 — Abstract Base Scraper

**Why:** All scrapers should follow the same interface so the scheduler can loop through them generically.

**File: `app/scrapers/base.py`**
```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ScrapedArticle(BaseModel):
    """Universal output format for all scrapers."""
    title: str
    url: str
    external_id: str
    content_text: Optional[str] = None
    published_at: datetime
    description: str = ""
    thumbnail_url: str = ""

class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, hours: int = 24) -> list[ScrapedArticle]:
        """Return articles published within the last `hours` hours."""
        ...
```

Now every scraper (YouTube, blog, RSS) returns `list[ScrapedArticle]` — the DB layer doesn't care where the data came from.

---

### 2.2 — Blog Scraper (OpenAI, Anthropic, Google)

**Why:** AI company blogs are where the biggest announcements happen — new models, research, product launches.

**How it works:**
1. `requests` fetches the blog page HTML
2. `BeautifulSoup` parses it and extracts article cards (title, URL, date)
3. For each article, you fetch the full page and extract the body text
4. You filter by date (last 24h)

**File: `app/scrapers/blog_scraper.py`** (example for OpenAI)
```python
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from app.scrapers.base import BaseScraper, ScrapedArticle

class OpenAIBlogScraper(BaseScraper):
    BASE_URL = "https://openai.com/news/"

    def scrape(self, hours: int = 24) -> list[ScrapedArticle]:
        response = requests.get(self.BASE_URL, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []

        # Find article cards — inspect the HTML to find the right selectors
        for card in soup.select("a[href*='/index/']"):  # Adjust selector
            title = card.get_text(strip=True)
            url = "https://openai.com" + card["href"]

            # Fetch full article page for body text
            body_text = self._fetch_article_body(url)

            articles.append(ScrapedArticle(
                title=title,
                url=url,
                external_id=card["href"],
                content_text=body_text,
                published_at=datetime.now(timezone.utc),  # Parse from page
            ))

        return articles

    def _fetch_article_body(self, url: str) -> str:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Extract main content — depends on site structure
        content_div = soup.find("article") or soup.find("main")
        return content_div.get_text(separator="\n", strip=True) if content_div else ""
```

> [!NOTE]
> Blog scrapers are **fragile** — sites change their HTML structure. You'll need to inspect each site and adjust CSS selectors. An alternative is to use their RSS feeds if available (Anthropic has one).

---

### 2.3 — Generic RSS Scraper

**Why:** Many tech sites offer RSS feeds. One scraper can handle TechCrunch, The Verge, Hacker News, etc.

**How:** Same as YouTube's RSS approach but for any feed URL:
```python
class RSSFeedScraper(BaseScraper):
    def __init__(self, feed_url: str, source_name: str):
        self.feed_url = feed_url
        self.source_name = source_name

    def scrape(self, hours: int = 24) -> list[ScrapedArticle]:
        feed = feedparser.parse(self.feed_url)
        # Filter by time, extract title/link/summary, return ScrapedArticle list
```

**Popular AI RSS feeds to add:**
- `https://techcrunch.com/category/artificial-intelligence/feed/`
- `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
- `https://news.ycombinator.com/rss` (Hacker News)
- `https://blog.google/technology/ai/rss/` (Google AI Blog)

---

## Phase 3: AI Processing Pipeline (~3-4 days)

> [!IMPORTANT]
> This phase is the **brain** of the aggregator. Raw text goes in → summaries, tags, and embeddings come out.

### 3.1 — AI Summarizer

**Why:** Nobody reads a 10,000-word transcript. A 3-sentence summary makes it digestible. This is what shows up in the daily email.

**How it works:**
1. Take the `content_text` from an Article (transcript, blog body)
2. Send it to an LLM (Gemini) with a prompt like: *"Summarize this AI news article in 3 sentences"*
3. Save the summary back to `Article.summary`

**File: `app/services/summarizer.py`**
```python
import google.generativeai as genai
from app.config import get_settings

genai.configure(api_key=get_settings().gemini_api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

SUMMARIZE_PROMPT = """Summarize the following AI news article in exactly 3 concise sentences.
Focus on: what happened, why it matters, and impact on the AI field.

Article:
{text}
"""

def summarize_article(text: str) -> str:
    """Returns a 3-sentence summary of the article."""
    if not text or len(text) < 100:
        return ""

    # Truncate very long texts to avoid token limits
    truncated = text[:15000]
    response = model.generate_content(SUMMARIZE_PROMPT.format(text=truncated))
    return response.text.strip()
```

**Usage:**
```python
article = db.query(Article).filter(Article.summary == None).first()
article.summary = summarize_article(article.content_text)
db.commit()
```

---

### 3.2 — Topic Tagger

**Why:** Tags are how you match articles to user preferences. If a user likes "LLMs" and "reasoning", you need to know which articles are about those topics.

**How:** Same LLM, different prompt:

**File: `app/services/tagger.py`**
```python
import json

TAG_PROMPT = """Extract 3-7 topic tags from this AI news article.
Return ONLY a JSON array of lowercase strings.
Example: ["llms", "gpt-5", "reasoning", "benchmarks", "openai"]

Article:
{text}
"""

def extract_tags(text: str) -> list[str]:
    """Returns a list of topic tags for the article."""
    if not text:
        return []

    truncated = text[:10000]
    response = model.generate_content(TAG_PROMPT.format(text=truncated))

    try:
        tags = json.loads(response.text.strip())
        return [t.lower().strip() for t in tags if isinstance(t, str)]
    except json.JSONDecodeError:
        return []
```

**Example output:**
```
Input:  "OpenAI released GPT-5 with improved reasoning..."
Output: ["openai", "gpt-5", "reasoning", "llms", "benchmarks"]
```

---

### 3.3 — Embedding Generator

**Why:** This is the core of the ML recommendation. An embedding is a list of ~768 numbers that captures the *meaning* of a text. Similar articles have similar embeddings. Similar users (based on what they read) also have similar embedding vectors.

**How embeddings enable recommendations:**
```
Article about GPT-5 reasoning → [0.12, -0.45, 0.88, ...]  (768 floats)
Article about GPT-5 safety    → [0.11, -0.43, 0.85, ...]  (very similar!)
Article about robotics         → [0.92, 0.31, -0.12, ...]  (very different)
```

If a user likes the first article, the system knows to recommend the second one (similar embedding) and not the third (different embedding).

**File: `app/services/embedder.py`**
```python
# Option A: Using Gemini embeddings (free tier available)
import google.generativeai as genai

def generate_embedding(text: str) -> list[float]:
    """Generate a semantic embedding vector for the given text."""
    # Use first 2000 chars of summary + title for efficiency
    truncated = text[:2000]
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=truncated,
    )
    return result["embedding"]  # Returns list of 768 floats
```

**How to store it:**
```python
article.embedding = generate_embedding(article.title + " " + article.summary)
db.commit()
```

---

### 3.4 — Processing Pipeline (ties it all together)

**File: `app/services/pipeline.py`**
```python
def process_new_articles(db: Session):
    """Find unprocessed articles and run summarize → tag → embed."""
    unprocessed = db.query(Article).filter(Article.summary == None).all()

    for article in unprocessed:
        if not article.content_text:
            continue

        print(f"Processing: {article.title}")

        # Step 1: Summarize
        article.summary = summarize_article(article.content_text)

        # Step 2: Tag
        article.tags = extract_tags(article.content_text)

        # Step 3: Embed (using summary for efficiency)
        article.embedding = generate_embedding(
            article.title + " " + (article.summary or "")
        )

        db.commit()
        print(f"  ✅ Done — tags: {article.tags}")
```

---

## Phase 4: Recommendation Engine (~3 days)

### 4.1 — How the Recommendation Works (The Theory)

The recommendation uses **cosine similarity** — a math formula that measures how similar two vectors are. Score goes from -1 (opposite) to 1 (identical).

```
User's taste vector:   [0.15, -0.42, 0.80, ...]   (average of articles they liked)
New article embedding: [0.12, -0.45, 0.88, ...]   (Phase 3 output)
Cosine similarity:     0.97                         → Highly relevant! Recommend it.
```

**The feedback loop:**
```
User signs up → picks topics (explicit preference)
    → System finds articles matching those topics
    → User reads/likes some articles
    → System averages those article embeddings → user taste vector
    → New articles ranked by similarity to taste vector
    → Better recommendations over time!
```

---

### 4.2 — User Profile Builder

**File: `app/recommendation/user_profile.py`**
```python
import numpy as np
from sqlalchemy.orm import Session
from app.models.user import User, UserInteraction
from app.models.article import Article

def build_user_taste_vector(db: Session, user_id: int) -> list[float]:
    """
    Build a user's taste vector from their interactions.
    It's a weighted average of embeddings of articles they liked/viewed.
    """
    # Weight by interaction type
    weights = {"like": 3.0, "save": 2.0, "view": 1.0, "dismiss": -1.0}

    interactions = (
        db.query(UserInteraction, Article)
        .join(Article)
        .filter(UserInteraction.user_id == user_id)
        .filter(Article.embedding.isnot(None))
        .all()
    )

    if not interactions:
        return None

    vectors = []
    interaction_weights = []
    for interaction, article in interactions:
        w = weights.get(interaction.interaction_type, 0)
        vectors.append(np.array(article.embedding))
        interaction_weights.append(w)

    # Weighted average
    interaction_weights = np.array(interaction_weights)
    vectors = np.array(vectors)
    taste_vector = np.average(vectors, axis=0, weights=interaction_weights)

    return taste_vector.tolist()
```

---

### 4.3 — Article Ranker

**File: `app/recommendation/ranker.py`**
```python
import numpy as np
from numpy.linalg import norm
from datetime import datetime, timezone

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns -1 to 1."""
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (norm(a) * norm(b) + 1e-8))

def rank_articles_for_user(
    user,
    articles,
    top_k: int = 10
):
    """
    Rank articles by relevance to the user.
    Uses a combined score of:
      - Embedding similarity (how close to user's taste)
      - Tag overlap (how many tags match user preferences)
      - Recency (newer articles get a small boost)
    """
    if not user.taste_vector:
        # Cold start: fall back to tag matching only
        return _rank_by_tags(user, articles, top_k)

    scored = []
    for article in articles:
        score = 0.0

        # 1. Embedding similarity (0 to 1) — 60% weight
        if article.embedding:
            sim = cosine_similarity(user.taste_vector, article.embedding)
            score += 0.6 * sim

        # 2. Tag overlap — 25% weight
        if user.preferred_topics and article.tags:
            user_tags = set(t.lower() for t in user.preferred_topics)
            article_tags = set(t.lower() for t in article.tags)
            overlap = len(user_tags & article_tags) / max(len(user_tags), 1)
            score += 0.25 * overlap

        # 3. Recency bonus — 15% weight (articles from last 6h get full boost)
        hours_old = (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600
        recency = max(0, 1 - hours_old / 48)  # Decays over 48 hours
        score += 0.15 * recency

        scored.append((score, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in scored[:top_k]]
```

---

## Phase 5: Delivery System (~2 days)

### 5.1 — Email Digest

**Why:** This is the main delivery channel. A daily email at the user's preferred time with their top 10 recommended articles.

**How it works:**
1. Scheduler triggers at the user's `delivery_time`
2. Recommendation engine picks top 10 articles for that user
3. An HTML template renders them into a nice email
4. An email service (Resend / SendGrid / raw SMTP) sends it

**File: `app/delivery/email_sender.py`**
```python
import resend  # or use smtplib for raw SMTP
from datetime import datetime
from app.config import get_settings

resend.api_key = get_settings().resend_api_key

def send_daily_digest(user_email: str, user_name: str, articles):
    """Send the daily AI news digest to a user."""

    # Build HTML from articles
    articles_html = ""
    for i, article in enumerate(articles, 1):
        articles_html += f"""
        <div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #6366f1;">
            <h3 style="margin: 0;">#{i} {article.title}</h3>
            <p style="color: #666; font-size: 13px;">
                {article.published_at.strftime('%b %d, %Y')} · {', '.join(article.tags[:3])}
            </p>
            <p>{article.summary}</p>
            <a href="{article.url}">Read more →</a>
        </div>
        """

    resend.Emails.send({
        "from": "AI News <digest@yourdomain.com>",
        "to": user_email,
        "subject": f"🤖 Your AI News Digest — {datetime.now().strftime('%b %d')}",
        "html": f"""
            <h1>Good morning, {user_name}! 👋</h1>
            <p>Here are your top AI news picks for today:</p>
            {articles_html}
            <hr>
            <p style="color: #999; font-size: 12px;">
                <a href="https://yourapp.com/preferences">Update preferences</a> ·
                <a href="https://yourapp.com/unsubscribe">Unsubscribe</a>
            </p>
        """
    })
```

---

### 5.2 — Telegram Bot (optional)

**How:** Use `python-telegram-bot` library. Users send `/subscribe` in a Telegram chat, the bot saves their `chat_id`, and sends daily digests as formatted messages.

```
# Key commands
/start       → Welcome + register
/subscribe   → Start receiving digests
/preferences → Set topics (inline keyboard buttons)
/digest      → Get digest right now (on demand)
```

---

### 5.3 — Scheduler

**Why:** Everything needs to run automatically — scrape every 6 hours, process right after, deliver daily.

**File: `app/scheduler/jobs.py`**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# Job 1: Scrape all sources every 6 hours
@scheduler.scheduled_job("interval", hours=6)
def scrape_all_sources():
    # Loop through all active sources/channels → run scrapers → save to DB
    ...

# Job 2: Process new articles (summarize, tag, embed)
@scheduler.scheduled_job("interval", hours=6, minutes=30)  # 30min after scrape
def process_new():
    process_new_articles(db)

# Job 3: Send digests daily at 8 AM
@scheduler.scheduled_job("cron", hour=8)
def send_digests():
    for user in get_all_active_users():
        articles = rank_articles_for_user(user, get_todays_articles())
        send_daily_digest(user.email, user.name, articles)

# Job 4: Update user taste vectors weekly
@scheduler.scheduled_job("cron", day_of_week="sun")
def update_profiles():
    for user in get_all_active_users():
        user.taste_vector = build_user_taste_vector(db, user.id)
        db.commit()
```

---

## Phase 6: FastAPI Backend (~3 days)

### 6.1 — API Setup

**File: [main.py](file:///Users/hemant/Desktop/news/ai/ai-news-agg/main.py)**
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.scheduler.jobs import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()  # Start background jobs
    yield
    scheduler.shutdown()

app = FastAPI(title="AI News Aggregator", lifespan=lifespan)

# Mount routes
app.include_router(auth_router, prefix="/auth")
app.include_router(feed_router, prefix="/feed")
app.include_router(articles_router, prefix="/articles")
app.include_router(preferences_router, prefix="/preferences")
```

### 6.2 — Key API Endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| `POST` | `/auth/signup` | Register user + pick topics |
| `POST` | `/auth/login` | Returns JWT token |
| `GET` | `/feed` | Personalized feed (top 20 articles for this user) |
| `GET` | `/articles` | Browse all recent articles, with search/filter |
| `GET` | `/articles/{id}` | Single article detail + full text |
| `POST` | `/articles/{id}/interact` | Record view/like/save/dismiss (feeds recommendation) |
| `GET` | `/preferences` | Get user's current preferences |
| `PUT` | `/preferences` | Update topics, sources, delivery time |

### 6.3 — The Feedback Loop (most important API)

```
User opens email → clicks article link →
  Link goes through your API: /articles/123/interact?type=view →
    Redirect to actual article URL
    + Record the "view" interaction in DB
    + Next time, similar articles rank higher
```

This is how the system **learns** without the user doing anything special.

---

## Phase 7: Frontend (optional, ~3-4 days)

A simple web dashboard where users can:
- Sign up and select preferred topics via checkboxes
- Browse their personalized feed
- Like/save/dismiss articles (inline buttons)
- View past digest history
- Update delivery preferences

Tech: Next.js or a simple Jinja2 template rendered by FastAPI.

---

## 🧭 Summary Flow (End to End)

```
Every 6 hours:
┌─────────────────────────────────────────────────────────────────┐
│  1. SCRAPE: YouTube RSS, Blogs, RSS feeds, ArXiv               │
│     → Raw articles saved to PostgreSQL                         │
│                                                                │
│  2. PROCESS: For each new article                              │
│     → Summarize with Gemini (3-sentence summary)               │
│     → Tag with Gemini (["llms", "gpt-5", "reasoning"])         │
│     → Embed with Gemini (768-dim vector)                       │
│     → Save summary, tags, embedding to DB                      │
│                                                                │
│  3. UPDATE: Rebuild user taste vectors from recent interactions │
└─────────────────────────────────────────────────────────────────┘

Daily at 8 AM (per user):
┌─────────────────────────────────────────────────────────────────┐
│  4. RECOMMEND: For each user                                   │
│     → Score all recent articles using:                         │
│        cosine_similarity(user_vector, article_embedding)       │
│        + tag overlap + recency                                 │
│     → Pick top 10                                              │
│                                                                │
│  5. DELIVER:                                                   │
│     → Render HTML email with summaries + links                 │
│     → Send via Resend/SendGrid/SMTP                            │
│     → Or send via Telegram bot                                 │
│                                                                │
│  6. LEARN:                                                     │
│     → Track which articles user clicks/reads                   │
│     → Update taste vector → better recommendations tomorrow    │
└─────────────────────────────────────────────────────────────────┘
```

---

> [!TIP]
> **Start with Phase 1 right now.** Once articles are in the database, everything else plugs in incrementally. You don't need all phases to have something useful — even Phase 1 + Phase 3 (scrape → summarize → store) gives you a searchable AI news database.
