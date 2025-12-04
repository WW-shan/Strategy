from .base import BaseStrategy
import pandas as pd
import logging
from datetime import datetime
from pytz import timezone

# 设置时区
CN_TZ = timezone('Asia/Shanghai')
logger = logging.getLogger(__name__)

class BtcFiveDownStrategy(BaseStrategy):
    def __init__(self, strategy_id: int, name: str, config: dict, exchange, signal_callback):
        # 初始化父类
        super().__init__(strategy_id, name, config, exchange)
        self.signal_callback = signal_callback
        
        # 从 config 读取，或使用默认值
        self.symbol = config.get('symbol', 'BTC/USDT')  # 交易对
        self.timeframe = config.get('timeframe', '1h')  # 时间级别
        self.exchange_name = config.get('exchange', 'binance')  # 交易所名称
        
        # 状态记录：记录上一次处理的K线时间戳，防止单根K线重复报警
        self.last_processed_timestamp = None

    def start(self):
        self.is_running = True
        self.log(f"🚀 策略启动: {self.symbol} {self.timeframe} @ {self.exchange_name} (5连阴追空策略)")

    def stop(self):
        self.is_running = False
        self.log("🛑 策略停止")

    def on_tick(self):
        """
        每分钟执行一次的主逻辑
        """
        if not self.is_running:
            return

        try:
            # 1. 获取 K 线数据
            # 获取最近 10 根，确保有足够的历史数据来判断前 5 根
            ohlcv = self.exchange.get_ohlcv(self.symbol, self.timeframe, limit=10, exchange_name=self.exchange_name)
            
            if not ohlcv or len(ohlcv) < 6:
                self.log(f"K线数据不足: 只有 {len(ohlcv) if ohlcv else 0} 根 (从 {self.exchange_name})")
                return

            # 转换为 DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 2. 锁定"上一根已完成"的K线
            # df.iloc[-1] 是当前正在走的K线（未完成）
            # df.iloc[-2] 是刚刚走完的那根K线（即潜在的第5根阴线）
            last_completed_idx = len(df) - 2
            last_completed_candle = df.iloc[last_completed_idx]
            last_completed_ts = int(last_completed_candle['timestamp'])

            # 3. 检查是否是新的一根K线
            # 只有当K线刚收盘（新的小时/周期开始）时才检查，避免在周期中间重复发信号
            if self.last_processed_timestamp == last_completed_ts:
                return
            
            # 标记为已处理
            self.last_processed_timestamp = last_completed_ts

            # 4. 核心逻辑：检查最近 5 根已完成 K 线
            # 从倒数第6根到倒数第2根（包含）= 共5根
            start_idx = max(0, last_completed_idx - 4)
            end_idx = last_completed_idx + 1
            target_candles = df.iloc[start_idx:end_idx]
            
            if len(target_candles) < 5:
                self.log(f"K线数据不足以进行5根K线判断: 只有 {len(target_candles)} 根")
                return
            
            # 判断是否全部为阴线 (Close < Open)
            is_all_bearish = (target_candles['close'] < target_candles['open']).all()

            if is_all_bearish:
                current_price = float(df['close'].iloc[-1])
                
                # 构造信号 - 做空 (SELL)
                reason = "连续5根1小时阴线确认，顺势追空 (5 Consecutive Bearish Candles -> Short)"
                self.log(f"⚡️ 信号触发: {reason} | 现价: {current_price}")

                signal_data = {
                    "strategy_id": self.strategy_id,
                    "strategy_name": self.name,
                    "symbol": self.symbol,
                    "side": "SELL",
                    "price": current_price,
                    "reason": reason,
                    "timestamp": datetime.now(CN_TZ).isoformat()
                }
                
                # 发送信号
                self.signal_callback(signal_data)
            else:
                self.log(f"K线检查完成: 未满足5连阴条件 (Last Close: {last_completed_candle['close']:.2f})")

        except Exception as e:
            logger.error(f"[{self.name}] 策略执行出错: {e}", exc_info=True)