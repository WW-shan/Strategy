from .base import BaseStrategy
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class RsiStrategy(BaseStrategy):
    def __init__(self, strategy_id: int, name: str, config: dict, exchange, signal_callback):
        super().__init__(strategy_id, name, config, exchange)
        self.signal_callback = signal_callback
        
        # Strategy Parameters
        self.symbol = config.get('symbol', 'BTC/USDT')
        self.timeframe = config.get('timeframe', '1h')
        self.rsi_period = int(config.get('rsi_period', 14))
        self.rsi_overbought = int(config.get('rsi_overbought', 70))
        self.rsi_oversold = int(config.get('rsi_oversold', 30))
        
        self.last_signal = None # To avoid repeating signals

    def start(self):
        self.is_running = True
        self.log(f"Started RSI Strategy for {self.symbol} ({self.timeframe})")

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
            # 1. Fetch OHLCV data
            # Fetch enough candles to calculate RSI (e.g., 100 candles)
            ohlcv = self.exchange.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
            if not ohlcv:
                return

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = df['close'].astype(float)
            
            # 2. Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'])
            
            current_rsi = df['rsi'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            self.log(f"Current RSI: {current_rsi:.2f} | Price: {current_price}")

            # 3. Generate Signal
            signal_side = None
            reason = ""

            if current_rsi < self.rsi_oversold:
                signal_side = "BUY"
                reason = f"RSI ({current_rsi:.2f}) < {self.rsi_oversold} (Oversold)"
            elif current_rsi > self.rsi_overbought:
                signal_side = "SELL"
                reason = f"RSI ({current_rsi:.2f}) > {self.rsi_overbought} (Overbought)"

            # 4. Publish Signal if new
            if signal_side and signal_side != self.last_signal:
                self.log(f"SIGNAL GENERATED: {signal_side} @ {current_price}")
                
                signal_data = {
                    "strategy_id": self.strategy_id,
                    "strategy_name": self.name,
                    "symbol": self.symbol,
                    "side": signal_side,
                    "price": current_price,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Call the callback function to handle the signal (save to DB, publish to Redis)
                self.signal_callback(signal_data)
                
                self.last_signal = signal_side

        except Exception as e:
            logger.error(f"Error in RSI Strategy on_tick: {e}")
