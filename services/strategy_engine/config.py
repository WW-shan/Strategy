from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
