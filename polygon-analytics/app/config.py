from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    polygon_api_key: str
    openai_api_key: str
    database_url: str
    redis_url: str
    secret_key: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()