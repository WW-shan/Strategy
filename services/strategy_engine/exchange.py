import ccxt
from config import settings
import logging

logger = logging.getLogger(__name__)

class ExchangeManager:
    def __init__(self):
        self.exchange = None
        self._init_exchange()

    def _init_exchange(self):
        try:
            config = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Default to futures trading
                }
            }
            
            if settings.BINANCE_API_KEY and settings.BINANCE_SECRET_KEY:
                config['apiKey'] = settings.BINANCE_API_KEY
                config['secret'] = settings.BINANCE_SECRET_KEY
                logger.info("Initializing Binance with API keys")
            else:
                logger.warning("Binance API Key/Secret not found. Initializing in public mode (read-only).")

            self.exchange = ccxt.binance(config)
            # Load markets to verify connection
            self.exchange.load_markets()
            logger.info("Successfully connected to Binance Futures")
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.exchange = None
            self.exchange = None

    def get_ticker(self, symbol: str):
        if not self.exchange:
            return None
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    def get_balance(self):
        if not self.exchange:
            return None
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return None

exchange_manager = ExchangeManager()
