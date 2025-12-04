from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from pytz import timezone

# UTC+8 时区
CN_TZ = timezone('Asia/Shanghai')

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(CN_TZ))
    
    subscriptions = relationship("Subscription", back_populates="user")

    def __str__(self):
        return f"{self.username} ({self.telegram_id})"

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    price_monthly = Column(Float, default=0.0)
    config_json = Column(Text, default="{}") # Store strategy parameters as JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(CN_TZ))

    def __str__(self):
        return self.name

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    start_date = Column(DateTime, default=lambda: datetime.now(CN_TZ))
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")
    strategy = relationship("Strategy")

    def __str__(self):
        status = "活跃" if self.is_active else "已停用"
        # 转换到 UTC+8 时区
        if self.end_date:
            end_date_cn = self.end_date.replace(tzinfo=None)
            if self.end_date.tzinfo:
                end_date_cn = self.end_date.astimezone(CN_TZ)
            end = end_date_cn.strftime("%Y-%m-%d")
        else:
            end = "永久"
        strategy_name = self.strategy.name if self.strategy else "未知策略"
        return f"{strategy_name} ({status}, 到期: {end})"

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    symbol = Column(String, index=True)
    side = Column(String)  # BUY or SELL
    price = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(CN_TZ))
    reason = Column(String, nullable=True) # e.g., "RSI < 30"
    
    strategy = relationship("Strategy")
