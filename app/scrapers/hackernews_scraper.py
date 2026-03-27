"""Hacker News scraper using the official API."""
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel


class ScrapedArticle(BaseModel):
    title: str
    url: str
    content_text: Optional[str]
    published_at: datetime


class HackerNewsScraper:
    """
    Scrapes Hacker News for AI-related stories.
    Uses the official HN API: https://github.com/HackerNews/API
    """
    BASE_URL = "https://thehackernews.com/"
    
    
    def scrape(self, hours: int = 96, limit: int = 50) -> List[ScrapedArticle]:
        """
        Scrape top stories from Hacker News.
        
        Args:
            hours: Only get stories from last N hours
            limit: Maximum number of stories to fetch
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles = []
        
        try:
            # Get top story IDs
            response = requests.get(f"{self.BASE_URL}/topstories.json", timeout=10)
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            # Fetch each story
            for story_id in story_ids:
                try:
                    story = self._fetch_story(story_id)
                    if story and story.published_at >= cutoff:
                        # Filter for AI-related content
                        if self._is_ai_related(story.title):
                            articles.append(story)
                except Exception as e:
                    print(f"Error fetching HN story {story_id}: {e}")
                    continue
            
            print(f"Found {len(articles)} AI-related HN stories")
            return articles
            
        except Exception as e:
            print(f"Error fetching HN top stories: {e}")
            return []
    
    def _fetch_story(self, story_id: int) -> Optional[ScrapedArticle]:
        """Fetch a single story by ID."""
        try:
            response = requests.get(f"{self.BASE_URL}/item/{story_id}.json", timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Skip if not a story or no URL
            if data.get('type') != 'story' or not data.get('url'):
                return None
            
            # Convert Unix timestamp to datetime
            published_at = datetime.fromtimestamp(data['time'], tz=timezone.utc)
            
            return ScrapedArticle(
                title=data['title'],
                url=data['url'],
                content_text=data.get('text', ''),  # HN stories don't have full text
                published_at=published_at
            )
        except Exception:
            return None
    
    def _is_ai_related(self, title: str) -> bool:
        """Check if title is AI-related."""
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'ml',
            'deep learning', 'neural', 'gpt', 'llm', 'openai', 'anthropic',
            'chatgpt', 'claude', 'gemini', 'transformer', 'diffusion',
            'stable diffusion', 'midjourney', 'dall-e', 'generative',
            'reinforcement learning', 'nlp', 'computer vision', 'pytorch',
            'tensorflow', 'hugging face', 'langchain', 'embedding'
        ]
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in ai_keywords)
