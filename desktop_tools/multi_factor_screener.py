import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from .technical_analyzer import TechnicalAnalyzer
from .data_provider import DataProvider


class FactorType(Enum):
    MA = "MA"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER = "BOLLINGER"
    KDJ = "KDJ"
    PE = "PE"


class LogicOperator(Enum):
    AND = "AND"
    OR = "OR"


@dataclass
class FactorConfig:
    factor_type: str
    enabled: bool = False
    weight: int = 20
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'factor_type': self.factor_type,
            'enabled': self.enabled,
            'weight': self.weight,
            'params': self.params
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FactorConfig':
        return cls(
            factor_type=data.get('factor_type', ''),
            enabled=data.get('enabled', False),
            weight=data.get('weight', 20),
            params=data.get('params', {})
        )


@dataclass
class StrategyConfig:
    name: str = "默认策略"
    buy_logic: str = "AND"
    sell_logic: str = "AND"
    factors: Dict[str, FactorConfig] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if not self.factors:
            self._init_default_factors()

    def _init_default_factors(self):
        default_params = {
            'MA': {'ma_short': 5, 'ma_long': 20, 'condition': 'golden_cross'},
            'RSI': {'period': 14, 'oversold': 30, 'overbought': 70},
            'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
            'BOLLINGER': {'period': 20, 'std_dev': 2.0, 'width_threshold': 10},
            'KDJ': {'n': 9, 'm1': 3, 'm2': 3},
            'PE': {'min_pe': 5.0, 'max_pe': 25.0}
        }
        for ft in FactorType:
            self.factors[ft.value] = FactorConfig(
                factor_type=ft.value,
                enabled=False,
                weight=20,
                params=default_params.get(ft.value, {})
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'buy_logic': self.buy_logic,
            'sell_logic': self.sell_logic,
            'factors': {k: v.to_dict() for k, v in self.factors.items()},
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        factors = {}
        if 'factors' in data:
            for k, v in data['factors'].items():
                factors[k] = FactorConfig.from_dict(v)
        return cls(
            name=data.get('name', '默认策略'),
            buy_logic=data.get('buy_logic', 'AND'),
            sell_logic=data.get('sell_logic', 'AND'),
            factors=factors,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', '')
        )


@dataclass
class FactorResult:
    factor_type: str
    enabled: bool
    score: float
    max_score: float
    normalized_score: float
    trigger_condition: str
    is_buy_signal: bool
    is_sell_signal: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StockAnalysisResult:
    symbol: str
    name: str
    current_price: float
    total_score: float
    max_total_score: float
    match_percent: float
    buy_signals: List[str]
    sell_signals: List[str]
    factor_results: Dict[str, FactorResult]
    trigger_reasons: List[str]
    has_buy_signal: bool
    has_sell_signal: bool
    analysis_time: str


class MultiFactorScreener:
    _instance: Optional['MultiFactorScreener'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._technical_analyzer = TechnicalAnalyzer()
        self._data_provider = DataProvider()
        self._config_dir = Path.home() / ".stock_monitor" / "strategies"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._strategies: Dict[str, StrategyConfig] = {}
        self._load_strategies()

    def _load_strategies(self):
        strategy_files = list(self._config_dir.glob("*.json"))
        for file_path in strategy_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    strategy = StrategyConfig.from_dict(data)
                    self._strategies[strategy.name] = strategy
            except (json.JSONDecodeError, IOError):
                continue

        if not self._strategies:
            default_strategy = StrategyConfig(name="默认策略")
            self._strategies["默认策略"] = default_strategy
            self._save_strategy(default_strategy)

    def _save_strategy(self, strategy: StrategyConfig):
        strategy.updated_at = datetime.now().isoformat()
        file_path = self._config_dir / f"{strategy.name.replace(' ', '_')}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(strategy.to_dict(), f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"保存策略失败: {e}")

    def get_strategy_names(self) -> List[str]:
        return list(self._strategies.keys())

    def get_strategy(self, name: str) -> Optional[StrategyConfig]:
        return self._strategies.get(name)

    def save_strategy(self, strategy: StrategyConfig):
        self._strategies[strategy.name] = strategy
        self._save_strategy(strategy)

    def delete_strategy(self, name: str) -> bool:
        if name in self._strategies:
            del self._strategies[name]
            file_path = self._config_dir / f"{name.replace(' ', '_')}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    def duplicate_strategy(self, source_name: str, new_name: str) -> Optional[StrategyConfig]:
        source = self._strategies.get(source_name)
        if not source:
            return None
        if new_name in self._strategies:
            return None
        new_strategy = StrategyConfig.from_dict(source.to_dict())
        new_strategy.name = new_name
        new_strategy.created_at = datetime.now().isoformat()
        new_strategy.updated_at = datetime.now().isoformat()
        self._strategies[new_name] = new_strategy
        self._save_strategy(new_strategy)
        return new_strategy

    def analyze_stock(
        self,
        symbol: str,
        strategy: StrategyConfig,
        period: str = '1y',
        interval: str = '1d'
    ) -> Optional[StockAnalysisResult]:
        technical_data = self._technical_analyzer.analyze_all_indicators(
            symbol, period, interval
        )
        if not technical_data:
            return None

        quote = self._data_provider.get_stock_quote(symbol)
        if not quote:
            quote = {'name': symbol, 'current_price': technical_data['latest']['price']}

        factor_results = {}
        total_score = 0.0
        max_total_score = 0.0
        buy_signals = []
        sell_signals = []
        trigger_reasons = []

        enabled_factors = [fc for fc in strategy.factors.values() if fc.enabled]
        for factor_config in enabled_factors:
            result = self._evaluate_factor(
                symbol, factor_config, technical_data, quote
            )
            if result:
                factor_results[factor_config.factor_type] = result
                total_score += result.score
                max_total_score += result.max_score
                if result.is_buy_signal:
                    buy_signals.append(result.trigger_condition)
                if result.is_sell_signal:
                    sell_signals.append(result.trigger_condition)

        has_buy_signal = self._evaluate_logic(
            [fr.is_buy_signal for fr in factor_results.values() if fr.enabled],
            strategy.buy_logic
        )
        has_sell_signal = self._evaluate_logic(
            [fr.is_sell_signal for fr in factor_results.values() if fr.enabled],
            strategy.sell_logic
        )

        if has_buy_signal:
            trigger_reasons.append("买入信号触发")
        if has_sell_signal:
            trigger_reasons.append("卖出信号触发")

        match_percent = (total_score / max_total_score * 100) if max_total_score > 0 else 0.0

        return StockAnalysisResult(
            symbol=symbol.upper(),
            name=quote.get('name', symbol),
            current_price=quote.get('current_price', technical_data['latest']['price']),
            total_score=total_score,
            max_total_score=max_total_score,
            match_percent=round(match_percent, 2),
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            factor_results=factor_results,
            trigger_reasons=trigger_reasons,
            has_buy_signal=has_buy_signal,
            has_sell_signal=has_sell_signal,
            analysis_time=datetime.now().isoformat()
        )

    def _evaluate_factor(
        self,
        symbol: str,
        factor_config: FactorConfig,
        technical_data: Dict[str, Any],
        quote: Dict[str, Any]
    ) -> Optional[FactorResult]:
        factor_type = factor_config.factor_type
        weight = factor_config.weight

        if factor_type == FactorType.MA.value:
            return self._evaluate_ma(factor_config, technical_data, weight)
        elif factor_type == FactorType.RSI.value:
            return self._evaluate_rsi(factor_config, technical_data, weight)
        elif factor_type == FactorType.MACD.value:
            return self._evaluate_macd(factor_config, technical_data, weight)
        elif factor_type == FactorType.BOLLINGER.value:
            return self._evaluate_bollinger(factor_config, technical_data, weight)
        elif factor_type == FactorType.KDJ.value:
            return self._evaluate_kdj(factor_config, technical_data, weight)
        elif factor_type == FactorType.PE.value:
            return self._evaluate_pe(factor_config, quote, weight)

        return None

    def _evaluate_ma(
        self,
        factor_config: FactorConfig,
        technical_data: Dict[str, Any],
        weight: int
    ) -> FactorResult:
        params = factor_config.params
        ma_short = params.get('ma_short', 5)
        ma_long = params.get('ma_long', 20)
        condition = params.get('condition', 'golden_cross')

        ma_values = technical_data.get('ma', {})
        latest = technical_data.get('latest', {})
        data = technical_data.get('data', pd.DataFrame())

        score = 0.0
        max_score = float(weight)
        is_buy_signal = False
        is_sell_signal = False
        trigger_condition = ""
        details = {}

        if len(data) >= 2 and ma_short in ma_values and ma_long in ma_values:
            ma_short_series = ma_values[ma_short]
            ma_long_series = ma_values[ma_long]

            if len(ma_short_series) >= 2 and len(ma_long_series) >= 2:
                current_short = ma_short_series[-1]
                current_long = ma_long_series[-1]
                prev_short = ma_short_series[-2]
                prev_long = ma_long_series[-2]

                details = {
                    f'MA{ma_short}': current_short,
                    f'MA{ma_long}': current_long,
                    'prev_short': prev_short,
                    'prev_long': prev_long
                }

                if condition == 'golden_cross':
                    if current_short > current_long and prev_short <= prev_long:
                        score = weight
                        is_buy_signal = True
                        trigger_condition = f"MA{ma_short}上穿MA{ma_long} (金叉)"
                    elif current_short < current_long and prev_short >= prev_long:
                        is_sell_signal = True
                        trigger_condition = f"MA{ma_short}下穿MA{ma_long} (死叉)"
                elif condition == 'above_ma':
                    current_price = latest.get('price', 0)
                    if current_price > current_long:
                        score = weight
                        is_buy_signal = True
                        trigger_condition = f"价格位于MA{ma_long}上方"
                    else:
                        is_sell_signal = True
                        trigger_condition = f"价格位于MA{ma_long}下方"
                elif condition == 'ma_up':
                    if current_long > prev_long:
                        score = weight * 0.7
                        is_buy_signal = True
                        trigger_condition = f"MA{ma_long}向上"
                    else:
                        is_sell_signal = True
                        trigger_condition = f"MA{ma_long}向下"

        normalized_score = (score / max_score * 100) if max_score > 0 else 0

        return FactorResult(
            factor_type=FactorType.MA.value,
            enabled=True,
            score=score,
            max_score=max_score,
            normalized_score=normalized_score,
            trigger_condition=trigger_condition,
            is_buy_signal=is_buy_signal,
            is_sell_signal=is_sell_signal,
            details=details
        )

    def _evaluate_rsi(
        self,
        factor_config: FactorConfig,
        technical_data: Dict[str, Any],
        weight: int
    ) -> FactorResult:
        params = factor_config.params
        period = params.get('period', 14)
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)

        latest = technical_data.get('latest', {})
        rsi = latest.get('rsi')

        score = 0.0
        max_score = float(weight)
        is_buy_signal = False
        is_sell_signal = False
        trigger_condition = ""
        details = {'rsi': rsi, 'oversold': oversold, 'overbought': overbought}

        if rsi is not None:
            if rsi < oversold:
                score = weight
                is_buy_signal = True
                trigger_condition = f"RSI超卖 ({rsi:.1f} < {oversold})"
            elif rsi > overbought:
                is_sell_signal = True
                trigger_condition = f"RSI超买 ({rsi:.1f} > {overbought})"
            elif rsi < 50:
                score = weight * 0.5
                trigger_condition = f"RSI偏弱 ({rsi:.1f})"
            else:
                score = weight * 0.3
                trigger_condition = f"RSI偏强 ({rsi:.1f})"

        normalized_score = (score / max_score * 100) if max_score > 0 else 0

        return FactorResult(
            factor_type=FactorType.RSI.value,
            enabled=True,
            score=score,
            max_score=max_score,
            normalized_score=normalized_score,
            trigger_condition=trigger_condition,
            is_buy_signal=is_buy_signal,
            is_sell_signal=is_sell_signal,
            details=details
        )

    def _evaluate_macd(
        self,
        factor_config: FactorConfig,
        technical_data: Dict[str, Any],
        weight: int
    ) -> FactorResult:
        latest = technical_data.get('latest', {})
        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        histogram = latest.get('macd_histogram')

        data = technical_data.get('data', pd.DataFrame())
        macd_data = technical_data.get('macd', {})

        score = 0.0
        max_score = float(weight)
        is_buy_signal = False
        is_sell_signal = False
        trigger_condition = ""
        details = {
            'macd': macd,
            'signal': macd_signal,
            'histogram': histogram
        }

        if macd is not None and macd_signal is not None:
            if 'macd_line' in macd_data and 'signal_line' in macd_data:
                macd_line = macd_data['macd_line']
                signal_line = macd_data['signal_line']

                if len(macd_line) >= 2 and len(signal_line) >= 2:
                    current_macd = macd_line[-1]
                    current_signal = signal_line[-1]
                    prev_macd = macd_line[-2]
                    prev_signal = signal_line[-2]

                    if current_macd > current_signal and prev_macd <= prev_signal:
                        score = weight
                        is_buy_signal = True
                        trigger_condition = "MACD上穿信号线 (金叉)"
                    elif current_macd < current_signal and prev_macd >= prev_signal:
                        is_sell_signal = True
                        trigger_condition = "MACD下穿信号线 (死叉)"

            if histogram is not None:
                if histogram > 0:
                    if score == 0:
                        score = weight * 0.6
                        trigger_condition = "MACD柱状图为正"
                else:
                    if not is_sell_signal and score == 0:
                        trigger_condition = "MACD柱状图为负"

        normalized_score = (score / max_score * 100) if max_score > 0 else 0

        return FactorResult(
            factor_type=FactorType.MACD.value,
            enabled=True,
            score=score,
            max_score=max_score,
            normalized_score=normalized_score,
            trigger_condition=trigger_condition,
            is_buy_signal=is_buy_signal,
            is_sell_signal=is_sell_signal,
            details=details
        )

    def _evaluate_bollinger(
        self,
        factor_config: FactorConfig,
        technical_data: Dict[str, Any],
        weight: int
    ) -> FactorResult:
        params = factor_config.params
        period = params.get('period', 20)
        width_threshold = params.get('width_threshold', 10)

        latest = technical_data.get('latest', {})
        current_price = latest.get('price', 0)
        upper = latest.get('bollinger_upper')
        lower = latest.get('bollinger_lower')
        middle = latest.get('bollinger_middle')
        percent_b = latest.get('percent_b')

        bollinger_data = technical_data.get('bollinger', {})

        score = 0.0
        max_score = float(weight)
        is_buy_signal = False
        is_sell_signal = False
        trigger_condition = ""
        details = {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'percent_b': percent_b,
            'price': current_price
        }

        if upper is not None and lower is not None and middle is not None:
            if current_price <= lower:
                score = weight
                is_buy_signal = True
                trigger_condition = f"价格触及布林带下轨 ({current_price:.2f} <= {lower:.2f})"
            elif current_price >= upper:
                is_sell_signal = True
                trigger_condition = f"价格触及布林带上轨 ({current_price:.2f} >= {upper:.2f})"
            elif percent_b is not None:
                if percent_b < 20:
                    score = weight * 0.8
                    is_buy_signal = True
                    trigger_condition = f"布林带%b超卖 ({percent_b:.1f}%)"
                elif percent_b > 80:
                    is_sell_signal = True
                    trigger_condition = f"布林带%b超买 ({percent_b:.1f}%)"
                elif percent_b < 50:
                    score = weight * 0.4
                    trigger_condition = f"布林带%b偏低 ({percent_b:.1f}%)"
                else:
                    score = weight * 0.2
                    trigger_condition = f"布林带%b偏高 ({percent_b:.1f}%)"

            if middle > 0:
                bandwidth = (upper - lower) / middle * 100
                details['bandwidth'] = bandwidth
                if bandwidth < width_threshold:
                    trigger_condition += f" (带宽收窄: {bandwidth:.1f}%)"

        normalized_score = (score / max_score * 100) if max_score > 0 else 0

        return FactorResult(
            factor_type=FactorType.BOLLINGER.value,
            enabled=True,
            score=score,
            max_score=max_score,
            normalized_score=normalized_score,
            trigger_condition=trigger_condition,
            is_buy_signal=is_buy_signal,
            is_sell_signal=is_sell_signal,
            details=details
        )

    def _evaluate_kdj(
        self,
        factor_config: FactorConfig,
        technical_data: Dict[str, Any],
        weight: int
    ) -> FactorResult:
        latest = technical_data.get('latest', {})
        k = latest.get('k')
        d = latest.get('d')
        j = latest.get('j')

        kdj_data = technical_data.get('kdj', {})

        score = 0.0
        max_score = float(weight)
        is_buy_signal = False
        is_sell_signal = False
        trigger_condition = ""
        details = {'k': k, 'd': d, 'j': j}

        if k is not None and d is not None:
            if 'k' in kdj_data and 'd' in kdj_data:
                k_series = kdj_data['k']
                d_series = kdj_data['d']

                if len(k_series) >= 2 and len(d_series) >= 2:
                    current_k = k_series[-1]
                    current_d = d_series[-1]
                    prev_k = k_series[-2]
                    prev_d = d_series[-2]

                    if current_k > current_d and prev_k <= prev_d:
                        score = weight
                        is_buy_signal = True
                        trigger_condition = "KDJ K线上穿D线 (金叉)"
                    elif current_k < current_d and prev_k >= prev_d:
                        is_sell_signal = True
                        trigger_condition = "KDJ K线下穿D线 (死叉)"

            if k < 20:
                if score == 0:
                    score = weight * 0.7
                    is_buy_signal = True
                    trigger_condition = f"KDJ K值超卖 ({k:.1f})"
            elif k > 80:
                if not is_sell_signal and score == 0:
                    is_sell_signal = True
                    trigger_condition = f"KDJ K值超买 ({k:.1f})"
            elif k < 50 and score == 0:
                score = weight * 0.3
                trigger_condition = f"KDJ K值偏弱 ({k:.1f})"
            elif score == 0:
                score = weight * 0.1
                trigger_condition = f"KDJ K值偏强 ({k:.1f})"

        normalized_score = (score / max_score * 100) if max_score > 0 else 0

        return FactorResult(
            factor_type=FactorType.KDJ.value,
            enabled=True,
            score=score,
            max_score=max_score,
            normalized_score=normalized_score,
            trigger_condition=trigger_condition,
            is_buy_signal=is_buy_signal,
            is_sell_signal=is_sell_signal,
            details=details
        )

    def _evaluate_pe(
        self,
        factor_config: FactorConfig,
        quote: Dict[str, Any],
        weight: int
    ) -> FactorResult:
        params = factor_config.params
        min_pe = params.get('min_pe', 5.0)
        max_pe = params.get('max_pe', 25.0)

        pe_ratio = quote.get('pe_ratio', 0)

        score = 0.0
        max_score = float(weight)
        is_buy_signal = False
        is_sell_signal = False
        trigger_condition = ""
        details = {'pe_ratio': pe_ratio, 'min_pe': min_pe, 'max_pe': max_pe}

        if pe_ratio and pe_ratio > 0:
            if min_pe <= pe_ratio <= max_pe:
                score = weight
                is_buy_signal = True
                trigger_condition = f"PE估值合理 ({pe_ratio:.2f} 在 [{min_pe}, {max_pe}] 范围内)"
            elif pe_ratio < min_pe:
                score = weight * 0.8
                is_buy_signal = True
                trigger_condition = f"PE估值偏低 ({pe_ratio:.2f} < {min_pe})"
            elif pe_ratio > max_pe:
                is_sell_signal = True
                trigger_condition = f"PE估值偏高 ({pe_ratio:.2f} > {max_pe})"
        else:
            trigger_condition = "PE数据不可用"

        normalized_score = (score / max_score * 100) if max_score > 0 else 0

        return FactorResult(
            factor_type=FactorType.PE.value,
            enabled=True,
            score=score,
            max_score=max_score,
            normalized_score=normalized_score,
            trigger_condition=trigger_condition,
            is_buy_signal=is_buy_signal,
            is_sell_signal=is_sell_signal,
            details=details
        )

    def _evaluate_logic(self, conditions: List[bool], logic: str) -> bool:
        if not conditions:
            return False

        if logic == 'AND':
            return all(conditions)
        elif logic == 'OR':
            return any(conditions)
        return False

    def analyze_watchlist(
        self,
        symbols: List[str],
        strategy: StrategyConfig,
        progress_callback: Optional[Any] = None
    ) -> List[StockAnalysisResult]:
        results = []
        total = len(symbols)

        for idx, symbol in enumerate(symbols):
            try:
                if progress_callback:
                    progress_callback(idx + 1, total, symbol)

                result = self.analyze_stock(symbol, strategy)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"分析股票 {symbol} 失败: {e}")
                continue

        return results
