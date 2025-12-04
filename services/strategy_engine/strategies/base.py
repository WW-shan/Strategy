from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    def __init__(self, strategy_id: int, name: str, config: dict, exchange):
        self.strategy_id = strategy_id
        self.name = name
        self.config = config
        self.exchange = exchange
        self.is_running = False

    @abstractmethod
    def start(self):
        """Start the strategy"""
        pass

    @abstractmethod
    def stop(self):
        """Stop the strategy"""
        pass

    @abstractmethod
    def on_tick(self):
        """Called on every tick/loop iteration"""
        pass

    def log(self, message: str):
        logger.info(f"[{self.name}] {message}")
