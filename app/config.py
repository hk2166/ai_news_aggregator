from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str
    
    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        extra = "ignore"  # Ignore extra fields in .env

@lru_cache
def get_settings() -> Settings:
    return Settings()