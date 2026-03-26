from app.models.base import engine, Base
from app.models.article import Article, Source, Channel
from app.models.user import User, UserInteraction
from app.scrapers.openai_scraper import OpenAIBlogScraper
from app.scrapers.youtube import YouTubeScraper
from app.services.article_service import save_articles, from_scraped_article, from_channel_video, get_recent_articles
from app.services.pipeline import process_new_articles

YOUTUBE_CHANNELS = [
    "UCn8ujwUInbJkBhffxqAPBVQ",  # Yannic Kilcher
    "UCbfYPyITQ-7l4upoX8nvctg",  # Two Minute Papers
    "UC9x0AN7BWHpCDHSm9NiJFJQ",
    "UCXuqSBlHAE6Xw-yeJA0Tunw",  # LTT
    "UCXUJJNoP1QupwsYIWFXmsZg",  # Tech Burner
    "UCOxwrh1M-3cYk1iS6b6pH8w",  # OpenAI
    "UCXZCJLdBC09xxGZ6gcdrc6A",  # Two Minute Papers
    "UC5lbdURzjB0irr-FTbjWN1A",  # AI Explained
    "UCYwLV1Y8Z0zRZk0kqC7X3HQ",  # Matt Wolfe
    "UCv83tO5cePwHMt1952IVVHw",  # MattVidPro AI
    "UCx0L2ZdYfiq-tsAXb8IXpQg",  # The AI Advantage
]


def main():
    Base.metadata.create_all(bind=engine)

    # Scrape
    openai_articles = OpenAIBlogScraper().scrape(hours=168)
    r = save_articles([from_scraped_article(a) for a in openai_articles])
    print(f"OpenAI blog: {r['saved']} saved, {r['skipped']} skipped")

    yt = YouTubeScraper()
    for cid in YOUTUBE_CHANNELS:
        videos = yt.scrape_channel(cid, hours=168)
        r = save_articles([from_channel_video(v, cid) for v in videos])
        print(f"YT {cid[:8]}: {r['saved']} saved, {r['skipped']} skipped")

    # Summarize + Tag
    r = process_new_articles()
    print(f"Processed: {r['processed']}, Failed: {r['failed']}")

    # Display
    for a in get_recent_articles(limit=10):
        tags = ", ".join(a.tags[:3]) if a.tags else "-"
        print(f"{a.published_at:%b %d} | {a.title[:50]:<50} | {tags}")


if __name__ == "__main__":
    main()