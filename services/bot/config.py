from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_API_URL: str
    REDIS_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
