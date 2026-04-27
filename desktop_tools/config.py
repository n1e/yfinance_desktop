import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any


@dataclass
class Position:
    symbol: str = ""
    quantity: int = 0
    cost_price: float = 0.0

    @property
    def cost_value(self) -> float:
        return self.quantity * self.cost_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'cost_price': self.cost_price
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        return cls(
            symbol=data.get('symbol', ''),
            quantity=data.get('quantity', 0),
            cost_price=data.get('cost_price', 0.0)
        )


@dataclass
class AppConfig:
    refresh_interval: int = 60
    auto_refresh: bool = True
    default_watchlist: List[str] = None
    news_count: int = 10
    screener_limit: int = 25

    def __post_init__(self):
        if self.default_watchlist is None:
            self.default_watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


class ConfigManager:
    _instance: Optional['ConfigManager'] = None
    _config_file: Path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config = AppConfig()
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self):
        config_dir = Path.home() / ".stock_monitor"
        config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = config_dir / "config.json"
        self._watchlist_file = config_dir / "watchlist.json"
        self._portfolio_file = config_dir / "portfolio.json"

    def _load_config(self):
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config.refresh_interval = data.get('refresh_interval', 60)
                    self._config.auto_refresh = data.get('auto_refresh', True)
                    self._config.news_count = data.get('news_count', 10)
                    self._config.screener_limit = data.get('screener_limit', 25)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_config(self):
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"保存配置失败: {e}")

    @property
    def refresh_interval(self) -> int:
        return self._config.refresh_interval

    @refresh_interval.setter
    def refresh_interval(self, value: int):
        if value < 10:
            value = 10
        self._config.refresh_interval = value
        self._save_config()

    @property
    def auto_refresh(self) -> bool:
        return self._config.auto_refresh

    @auto_refresh.setter
    def auto_refresh(self, value: bool):
        self._config.auto_refresh = value
        self._save_config()

    @property
    def news_count(self) -> int:
        return self._config.news_count

    @news_count.setter
    def news_count(self, value: int):
        self._config.news_count = max(1, min(50, value))
        self._save_config()

    @property
    def screener_limit(self) -> int:
        return self._config.screener_limit

    @screener_limit.setter
    def screener_limit(self, value: int):
        self._config.screener_limit = max(1, min(250, value))
        self._save_config()

    def load_watchlist(self) -> List[str]:
        if self._watchlist_file.exists():
            try:
                with open(self._watchlist_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._config.default_watchlist.copy()

    def save_watchlist(self, tickers: List[str]):
        try:
            with open(self._watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(tickers, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"保存自选股失败: {e}")

    def load_portfolio(self) -> Dict[str, Position]:
        portfolio = {}
        if self._portfolio_file.exists():
            try:
                with open(self._portfolio_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for symbol, pos_data in data.items():
                        portfolio[symbol.upper()] = Position.from_dict(pos_data)
            except (json.JSONDecodeError, IOError):
                pass
        return portfolio

    def save_portfolio(self, portfolio: Dict[str, Position]):
        try:
            data = {}
            for symbol, position in portfolio.items():
                data[symbol.upper()] = position.to_dict()
            with open(self._portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"保存持仓数据失败: {e}")
