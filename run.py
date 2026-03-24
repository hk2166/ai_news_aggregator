from app.models.base import engine, Base
from app.models.article import Article, Source, Channel
from app.models.user import User, UserInteraction
from app.scrapers.openai_scraper import OpenAIBlogScraper
from app.scrapers.youtube import YouTubeScraper
from app.services.article_service import save_articles, from_scraped_article, from_channel_video, get_recent_articles


YOUTUBE_CHANNELS = [
    "UCn8ujwUInbJkBhffxqAPBVQ",  # Yannic Kilcher
    "UCbfYPyITQ-7l4upoX8nvctg",  # Two Minute Papers
]


def main():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables ready\n")

    # Scrape OpenAI
    print("Scraping OpenAI blog...")
    openai_articles = OpenAIBlogScraper().scrape(hours=72)
    result = save_articles([from_scraped_article(a) for a in openai_articles])
    print(f"  Found {len(openai_articles)} | Saved: {result['saved']} | Skipped: {result['skipped']}\n")

    # Scrape YouTube
    yt = YouTubeScraper()
    for channel_id in YOUTUBE_CHANNELS:
        print(f"Scraping YouTube: {channel_id}...")
        videos = yt.scrape_channel(channel_id, hours=72)
        result = save_articles([from_channel_video(v, channel_id) for v in videos])
        print(f"  Found {len(videos)} | Saved: {result['saved']} | Skipped: {result['skipped']}\n")

    # Show results
    print("Recent articles:")
    print("-" * 60)
    for a in get_recent_articles(limit=10):
        print(f"{a.published_at.strftime('%b %d')} | {a.title[:45]}")
    print("-" * 60)


if __name__ == "__main__":
    main()
