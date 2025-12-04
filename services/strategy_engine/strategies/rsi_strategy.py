from .base import BaseStrategy
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from pytz import timezone
import json

CN_TZ = timezone('Asia/Shanghai')

logger = logging.getLogger(__name__)

# 导入缓存管理器（延迟导入以避免循环依赖）
cache_manager = None

def set_cache_manager(cm):
    """设置缓存管理器（在 main.py 中调用）"""
    global cache_manager
    cache_manager = cm

class RsiStrategy(BaseStrategy):
    def __init__(self, strategy_id: int, name: str, config: dict, exchange, signal_callback):
        super().__init__(strategy_id, name, config, exchange)
        self.signal_callback = signal_callback
        
        # Strategy Parameters
        self.symbol = config.get('symbol', 'BTC/USDT')
        self.timeframe = config.get('timeframe', '1h')
        self.exchange_name = config.get('exchange', 'binance')
        self.rsi_period = int(config.get('rsi_period', 14))
        self.rsi_overbought = int(config.get('rsi_overbought', 70))
        self.rsi_oversold = int(config.get('rsi_oversold', 30))
        
        self.last_signal_rsi = None  # 记录上次信号时的RSI状态（0=正常, 1=超卖, 2=超买）

    def start(self):
        self.is_running = True
        self.log(f"🚀 Started RSI Strategy for {self.symbol} ({self.timeframe}) @ {self.exchange_name}")

    def stop(self):
        self.is_running = False
        self.log("Stopped RSI Strategy")

    def calculate_rsi(self, closes):
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def on_tick(self):
        if not self.is_running:
            return

        try:
            # 1. 尝试从缓存获取 OHLCV 数据
            cache_key = f"{self.exchange_name}:{self.symbol}:{self.timeframe}"
            ohlcv = None
            
            if cache_manager:
                ohlcv = cache_manager.get_cache('market_data', self.exchange_name, self.symbol, self.timeframe)
                if ohlcv:
                    self.log(f"✓ Using cached OHLCV for {cache_key}")
            
            # 2. 如果缓存未命中，从交易所获取
            if not ohlcv:
                ohlcv = self.exchange.get_ohlcv(self.symbol, self.timeframe, limit=100, exchange_name=self.exchange_name)
                if not ohlcv:
                    self.log(f"Failed to fetch OHLCV from {self.exchange_name}")
                    return
                
                # 3. 存入缓存
                if cache_manager:
                    cache_manager.set_cache('market_data', self.exchange_name, self.symbol, ohlcv, self.timeframe)
                    self.log(f"📦 Cached OHLCV for {cache_key}")

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = df['close'].astype(float)
            
            # 4. Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'])
            
            current_rsi = df['rsi'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            self.log(f"Current RSI: {current_rsi:.2f} | Price: {current_price}")

            # 3. Generate Signal
            signal_side = None
            reason = ""
            current_rsi_state = 0  # 0=正常, 1=超卖, 2=超买

            if current_rsi < self.rsi_oversold:
                signal_side = "BUY"
                current_rsi_state = 1  # 超卖状态
                reason = f"RSI ({current_rsi:.2f}) < {self.rsi_oversold} (Oversold)"
            elif current_rsi > self.rsi_overbought:
                signal_side = "SELL"
                current_rsi_state = 2  # 超买状态
                reason = f"RSI ({current_rsi:.2f}) > {self.rsi_overbought} (Overbought)"

            # 4. Publish Signal if RSI state changed (entered oversold/overbought)
            if signal_side and current_rsi_state != self.last_signal_rsi:
                self.log(f"SIGNAL GENERATED: {signal_side} @ {current_price}")
                
                signal_data = {
                    "strategy_id": self.strategy_id,
                    "strategy_name": self.name,
                    "symbol": self.symbol,
                    "side": signal_side,
                    "price": current_price,
                    "reason": reason,
                    "timestamp": datetime.now(CN_TZ).isoformat()
                }
                
                # Call the callback function to handle the signal (save to DB, publish to Redis)
                self.signal_callback(signal_data)
                
                self.last_signal_rsi = current_rsi_state

        except Exception as e:
            logger.error(f"Error in RSI Strategy on_tick: {e}")
