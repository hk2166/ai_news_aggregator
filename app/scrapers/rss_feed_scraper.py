"""Generic RSS feed scraper for custom sources."""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel
import time


class ScrapedArticle(BaseModel):
    title: str
    url: str
    content_text: Optional[str]
    published_at: datetime


class RSSFeedScraper:
    """
    Generic RSS feed scraper that can handle any RSS/Atom feed.
    """
    
    def scrape_feed(self, feed_url: str, hours: int = 96) -> List[ScrapedArticle]:
        """
        Scrape articles from an RSS feed.
        
        Args:
            feed_url: URL of the RSS/Atom feed
            hours: Only get articles from last N hours
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles = []
        
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                try:
                    # Get published date
                    if hasattr(entry, 'published_parsed'):
                        pub = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
                    elif hasattr(entry, 'updated_parsed'):
                        pub = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
                    else:
                        pub = datetime.now(timezone.utc)
                    
                    if pub <= cutoff:
                        continue
                    
                    # Get content
                    content = ''
                    if hasattr(entry, 'content'):
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # Clean HTML from content
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text(separator='\n', strip=True)
                    
                    articles.append(ScrapedArticle(
                        title=entry.title,
                        url=entry.link,
                        content_text=content,
                        published_at=pub
                    ))
                    
                except Exception as e:
                    print(f"Error parsing feed entry: {e}")
                    continue
            
            print(f"Found {len(articles)} articles from {feed_url}")
            return articles
            
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {e}")
            return []
    
    def scrape_multiple_feeds(self, feed_urls: List[str], hours: int = 96) -> List[ScrapedArticle]:
        """Scrape multiple RSS feeds."""
        all_articles = []
        
        for feed_url in feed_urls:
            articles = self.scrape_feed(feed_url, hours)
            all_articles.extend(articles)
        
        return all_articles


# Popular AI-related RSS feeds
AI_RSS_FEEDS = [
    'https://blog.google/technology/ai/rss/',  # Google AI Blog
    'https://www.deepmind.com/blog/rss.xml',  # DeepMind
    'https://aws.amazon.com/blogs/machine-learning/feed/',  # AWS ML Blog
    'https://blogs.microsoft.com/ai/feed/',  # Microsoft AI Blog
    'https://huggingface.co/blog/feed.xml',  # Hugging Face
]
