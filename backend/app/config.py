from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = ""
    redis_url: str = "redis://redis:6379"
    timescale_url: str = ""
    kafka_bootstrap: str = "kafka:9092"
    webhook_secret: str = ""

    class Config:
        env_file = ".env"

settings = Settings()