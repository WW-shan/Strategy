import ccxt
from config import settings
import logging

logger = logging.getLogger(__name__)

class ExchangeManager:
    def __init__(self):
        self.exchange = None
        self._init_exchange()

    def _init_exchange(self):
        if not settings.BINANCE_API_KEY or not settings.BINANCE_SECRET_KEY:
            logger.warning("Binance API Key or Secret not found. Exchange functionality will be limited.")
            return

        try:
            self.exchange = ccxt.binance({
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_SECRET_KEY,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Default to futures trading
                }
            })
            # Load markets to verify connection
            self.exchange.load_markets()
            logger.info("Successfully connected to Binance Futures")
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
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
