import ccxt
from config import settings
import logging

logger = logging.getLogger(__name__)

class ExchangeManager:
    def __init__(self):
        self.exchanges = {}  # {exchange_name: exchange_instance}
        self.primary_exchange = None  # 默认交易所
        self._init_exchanges()

    def _init_exchanges(self):
        """初始化所有配置的交易所"""
        
        # ==================== Binance ====================
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

            if settings.PROXY_URL:
                config['proxies'] = {
                    'http': settings.PROXY_URL,
                    'https': settings.PROXY_URL,
                }
                logger.info(f"Using Proxy for Binance: {settings.PROXY_URL}")

            binance = ccxt.binance(config)
            binance.load_markets()
            self.exchanges['binance'] = binance
            self.primary_exchange = binance  # 设置为主交易所
            logger.info("✅ Successfully connected to Binance Futures")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Binance: {e}", exc_info=True)
        
        # ==================== Bitget ====================
        try:
            config = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Bitget 使用 swap
                }
            }
            
            if settings.BITGET_API_KEY and settings.BITGET_SECRET_KEY and settings.BITGET_PASSPHRASE:
                config['apiKey'] = settings.BITGET_API_KEY
                config['secret'] = settings.BITGET_SECRET_KEY
                config['password'] = settings.BITGET_PASSPHRASE
                logger.info("Initializing Bitget with API keys")
            else:
                logger.warning("Bitget credentials not found. Initializing in public mode (read-only).")

            if settings.PROXY_URL:
                config['proxies'] = {
                    'http': settings.PROXY_URL,
                    'https': settings.PROXY_URL,
                }
                logger.info(f"Using Proxy for Bitget: {settings.PROXY_URL}")

            bitget = ccxt.bitget(config)
            bitget.load_markets()
            self.exchanges['bitget'] = bitget
            logger.info("✅ Successfully connected to Bitget Futures")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Bitget: {e}", exc_info=True)

    def get_exchange(self, exchange_name: str = 'binance'):
        """获取指定交易所实例"""
        return self.exchanges.get(exchange_name, self.primary_exchange)

    @property
    def exchange(self):
        """向后兼容：返回主交易所"""
        return self.primary_exchange

    def get_ticker(self, symbol: str, exchange_name: str = 'binance'):
        """从指定交易所获取行情"""
        exch = self.get_exchange(exchange_name)
        if not exch:
            logger.warning(f"Exchange {exchange_name} not available")
            return None
        try:
            return exch.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker {symbol} from {exchange_name}: {e}")
            return None

    def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100, exchange_name: str = 'binance'):
        """从指定交易所获取K线数据"""
        exch = self.get_exchange(exchange_name)
        if not exch:
            logger.warning(f"Exchange {exchange_name} not available")
            return None
        try:
            return exch.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching OHLCV {symbol} from {exchange_name}: {e}")
            return None

    def get_balance(self, exchange_name: str = 'binance'):
        """从指定交易所获取余额"""
        exch = self.get_exchange(exchange_name)
        if not exch:
            logger.warning(f"Exchange {exchange_name} not available")
            return None
        try:
            return exch.fetch_balance()
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange_name}: {e}")
            return None

    def list_exchanges(self):
        """列出所有已连接的交易所"""
        return list(self.exchanges.keys())

exchange_manager = ExchangeManager()
