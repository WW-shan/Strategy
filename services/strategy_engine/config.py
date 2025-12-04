from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    
    # ========== Binance ==========
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    
    # ========== Bitget ==========
    BITGET_API_KEY: str = ""
    BITGET_SECRET_KEY: str = ""
    BITGET_PASSPHRASE: str = ""
    
    # ========== Common ==========
    REDIS_URL: str = "redis://redis:6379/0"
    PROXY_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
