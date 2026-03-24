from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str


    gemini_api_key: str = ""
    

    resend_api_key: str = ""  


    proxy_username: str = ""
    proxy_password: str = ""


    scrape_interval_hours: int = 6
    default_lookback_hours: int = 24

    class Config:
        env_file = ".env"


@lru_cache  # Singleton — loads .env once and caches it
def get_settings() -> Settings:
    """Get the application settings singleton."""
    return Settings()
