"""Reddit scraper for AI-related subreddits."""
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel


class ScrapedArticle(BaseModel):
    title: str
    url: str
    content_text: Optional[str]
    published_at: datetime


class RedditScraper:
    """
    Scrapes Reddit for AI content.
    Uses Reddit's JSON API (no auth required for public posts).
    """
    
    SUBREDDITS = [
        'MachineLearning',
        'artificial',
        'OpenAI',
        'LocalLLaMA',
        'StableDiffusion',
        'ArtificialIntelligence',
        'ChatGPT',
        'Bing',
        'singularity',
        'MLQuestions',
        'learnmachinelearning',
        'deeplearning',
        'LanguageTechnology',
        'computervision',
    ]
    
    def scrape(self, hours: int = 96, limit_per_sub: int = 10) -> List[ScrapedArticle]:
        """
        Scrape hot posts from AI-related subreddits.
        
        Args:
            hours: Only get posts from last N hours
            limit_per_sub: Max posts per subreddit
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles = []
        
        for subreddit in self.SUBREDDITS:
            try:
                posts = self._fetch_subreddit(subreddit, limit_per_sub)
                for post in posts:
                    if post.published_at >= cutoff:
                        articles.append(post)
            except Exception as e:
                print(f"Error scraping r/{subreddit}: {e}")
                continue
        
        print(f"Found {len(articles)} Reddit posts")
        return articles
    
    def _fetch_subreddit(self, subreddit: str, limit: int) -> List[ScrapedArticle]:
        """Fetch hot posts from a subreddit."""
        try:
            
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            headers = {'User-Agent': 'AI-News-Aggregator/1.0'}
            
            response = requests.get(url, headers=headers, params={'limit': limit}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for post in data['data']['children']:
                post_data = post['data']
                
                # Skip stickied posts and self posts without external links
                if post_data.get('stickied') or post_data.get('is_self'):
                    continue
                
                # Convert Unix timestamp
                published_at = datetime.fromtimestamp(post_data['created_utc'], tz=timezone.utc)
                
                # Use post URL if no external URL
                url = post_data.get('url') or f"https://reddit.com{post_data['permalink']}"
                
                articles.append(ScrapedArticle(
                    title=post_data['title'],
                    url=url,
                    content_text=post_data.get('selftext', ''),
                    published_at=published_at
                ))
            
            return articles
            
        except Exception as e:
            print(f"Error fetching r/{subreddit}: {e}")
            return []
