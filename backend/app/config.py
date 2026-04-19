from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    gemini_api_key:  str = ""
    groq_api_key:    str = ""
    redis_url:       str = "redis://redis:6379"
    timescale_url:   str = ""
    kafka_bootstrap: str = ""
    webhook_secret:  str = ""

settings = Settings()