import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .technical_analyzer import TechnicalAnalyzer
from .valuation_analyzer import ValuationAnalyzer, ValuationMetrics
from .data_provider import DataProvider
from .volatility_analyzer import VolatilityAnalyzer


class ScoreDimension(Enum):
    TECHNICAL_SIGNAL = "技术面信号"
    VALUATION = "估值合理性"
    MOMENTUM = "动量强度"
    MARKET_CAP = "市值规模"
    VOLUME_PRICE = "量价配合"
    VOLATILITY = "波动率风险"
    GROWTH_POTENTIAL = "成长潜力"


@dataclass
class DimensionScore:
    name: str
    score: float = 0.0
    weight: float = 0.0
    max_score: float = 100.0
    details: Dict[str, Any] = field(default_factory=dict)
    raw_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StockScoreResult:
    symbol: str
    name: str = ""
    total_score: float = 0.0
    weighted_score: float = 0.0
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=datetime.now)
    status: str = ""

    def get_all_dimensions(self) -> List[str]:
        return list(self.dimension_scores.keys())

    def get_score_by_dimension(self, dimension: str) -> float:
        if dimension in self.dimension_scores:
            return self.dimension_scores[dimension].score
        return 0.0


class ScoreCalculator:
    DEFAULT_WEIGHTS = {
        ScoreDimension.TECHNICAL_SIGNAL.value: 0.20,
        ScoreDimension.VALUATION.value: 0.20,
        ScoreDimension.MOMENTUM.value: 0.15,
        ScoreDimension.MARKET_CAP.value: 0.10,
        ScoreDimension.VOLUME_PRICE.value: 0.15,
        ScoreDimension.VOLATILITY.value: 0.10,
        ScoreDimension.GROWTH_POTENTIAL.value: 0.10,
    }

    def __init__(self):
        self._technical_analyzer = TechnicalAnalyzer()
        self._valuation_analyzer = ValuationAnalyzer()
        self._data_provider = DataProvider()
        self._volatility_analyzer = VolatilityAnalyzer()
        self._weights = self.DEFAULT_WEIGHTS.copy()

    def set_weights(self, weights: Dict[str, float]):
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            normalized = {k: v / total for k, v in weights.items()}
            self._weights = normalized
        else:
            self._weights = weights

    def get_weights(self) -> Dict[str, float]:
        return self._weights.copy()

    def reset_weights(self):
        self._weights = self.DEFAULT_WEIGHTS.copy()

    def calculate_score(
        self,
        symbol: str,
        weights: Optional[Dict[str, float]] = None
    ) -> Optional[StockScoreResult]:
        try:
            symbol = symbol.upper().strip()
            if not symbol:
                return None

            if weights:
                original_weights = self._weights.copy()
                self.set_weights(weights)
            else:
                original_weights = None

            result = StockScoreResult(symbol=symbol)

            technical_data = self._technical_analyzer.analyze_all_indicators(symbol, period='6mo')
            valuation_metrics = self._valuation_analyzer.get_valuation_metrics(symbol)
            quote = self._data_provider.get_stock_quote(symbol)

            result.raw_data = {
                'technical': technical_data,
                'valuation': valuation_metrics,
                'quote': quote,
            }

            if quote:
                result.name = quote.get('name', symbol)

            scores = {}

            tech_score = self._calculate_technical_signal_score(technical_data)
            scores[ScoreDimension.TECHNICAL_SIGNAL.value] = tech_score

            val_score = self._calculate_valuation_score(valuation_metrics, quote)
            scores[ScoreDimension.VALUATION.value] = val_score

            mom_score = self._calculate_momentum_score(technical_data, quote)
            scores[ScoreDimension.MOMENTUM.value] = mom_score

            cap_score = self._calculate_market_cap_score(quote, valuation_metrics)
            scores[ScoreDimension.MARKET_CAP.value] = cap_score

            vp_score = self._calculate_volume_price_score(technical_data)
            scores[ScoreDimension.VOLUME_PRICE.value] = vp_score

            vol_score = self._calculate_volatility_score(symbol)
            scores[ScoreDimension.VOLATILITY.value] = vol_score

            growth_score = self._calculate_growth_score(valuation_metrics)
            scores[ScoreDimension.GROWTH_POTENTIAL.value] = growth_score

            total_score = 0.0
            weighted_score = 0.0

            for dim_name, dim_score in scores.items():
                if dim_score:
                    weight = self._weights.get(dim_name, 0.0)
                    dim_score.weight = weight
                    result.dimension_scores[dim_name] = dim_score
                    total_score += dim_score.score
                    weighted_score += dim_score.score * weight

            result.total_score = total_score / len(scores) if scores else 0.0
            result.weighted_score = weighted_score

            if result.weighted_score >= 80:
                result.status = "优秀"
            elif result.weighted_score >= 65:
                result.status = "良好"
            elif result.weighted_score >= 50:
                result.status = "一般"
            elif result.weighted_score >= 35:
                result.status = "偏弱"
            else:
                result.status = "较差"

            if original_weights:
                self._weights = original_weights

            return result

        except Exception as e:
            print(f"计算股票 {symbol} 评分失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_technical_signal_score(
        self,
        technical_data: Optional[Dict[str, Any]]
    ) -> Optional[DimensionScore]:
        if not technical_data:
            return None

        score = DimensionScore(name=ScoreDimension.TECHNICAL_SIGNAL.value)
        signals = technical_data.get('signals', {})
        latest = technical_data.get('latest', {})

        buy_signals = signals.get('buy_signals', [])
        sell_signals = signals.get('sell_signals', [])
        neutral_signals = signals.get('neutral_signals', [])

        buy_count = len(buy_signals)
        sell_count = len(sell_signals)
        total_count = buy_count + sell_count

        score.raw_metrics = {
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'neutral_signals': neutral_signals,
            'buy_count': buy_count,
            'sell_count': sell_count,
        }

        total_signal_score = 0.0
        max_signal_score = 0.0

        for buy_signal in buy_signals:
            if '金叉' in buy_signal or '黄金交叉' in buy_signal:
                total_signal_score += 15
            elif '超卖' in buy_signal:
                total_signal_score += 10
            elif '放量上涨' in buy_signal:
                total_signal_score += 10
            elif '回升' in buy_signal or '转正' in buy_signal:
                total_signal_score += 8
            elif '触及下轨' in buy_signal:
                total_signal_score += 8
            else:
                total_signal_score += 5
            max_signal_score += 15

        for sell_signal in sell_signals:
            if '死叉' in sell_signal or '死亡交叉' in sell_signal:
                total_signal_score -= 15
            elif '超买' in sell_signal:
                total_signal_score -= 10
            elif '放量下跌' in sell_signal:
                total_signal_score -= 10
            elif '回落' in sell_signal or '转负' in sell_signal:
                total_signal_score -= 8
            elif '触及上轨' in sell_signal:
                total_signal_score -= 8
            else:
                total_signal_score -= 5
            max_signal_score += 15

        rsi = latest.get('rsi')
        if rsi is not None and not np.isnan(rsi):
            if 40 <= rsi <= 60:
                total_signal_score += 10
            elif 30 <= rsi < 40 or 60 < rsi <= 70:
                total_signal_score += 5
            max_signal_score += 10
            score.raw_metrics['rsi'] = rsi

        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        macd_hist = latest.get('macd_histogram')
        score.raw_metrics['macd'] = macd
        score.raw_metrics['macd_signal'] = macd_signal
        score.raw_metrics['macd_histogram'] = macd_hist

        if macd_hist is not None and not np.isnan(macd_hist):
            if macd_hist > 0:
                total_signal_score += 8
            elif macd_hist < 0:
                total_signal_score -= 5
            max_signal_score += 8

        k_value = latest.get('k')
        d_value = latest.get('d')
        j_value = latest.get('j')
        score.raw_metrics['kdj_k'] = k_value
        score.raw_metrics['kdj_d'] = d_value
        score.raw_metrics['kdj_j'] = j_value

        if k_value is not None and d_value is not None and not np.isnan(k_value) and not np.isnan(d_value):
            if k_value > d_value:
                total_signal_score += 5
            else:
                total_signal_score -= 3
            max_signal_score += 5

            if k_value < 20:
                total_signal_score += 8
            elif k_value > 80:
                total_signal_score -= 8
            max_signal_score += 8

        percent_b = latest.get('percent_b')
        score.raw_metrics['percent_b'] = percent_b
        if percent_b is not None and not np.isnan(percent_b):
            if 20 <= percent_b <= 80:
                total_signal_score += 5
            elif percent_b < 10:
                total_signal_score += 10
            elif percent_b > 90:
                total_signal_score -= 10
            max_signal_score += 10

        if max_signal_score > 0:
            normalized = ((total_signal_score + max_signal_score) / (2 * max_signal_score)) * 100
            score.score = max(0.0, min(100.0, normalized))
        else:
            score.score = 50.0

        score.details = self._generate_technical_details(buy_signals, sell_signals, neutral_signals, latest)

        return score

    def _generate_technical_details(
        self,
        buy_signals: List[str],
        sell_signals: List[str],
        neutral_signals: List[str],
        latest: Dict[str, Any]
    ) -> Dict[str, Any]:
        details = {
            'summary': '',
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'neutral_signals': neutral_signals,
            'indicators': {}
        }

        total = len(buy_signals) - len(sell_signals)
        if total > 0:
            details['summary'] = f"技术面偏多，{len(buy_signals)}个买入信号，{len(sell_signals)}个卖出信号"
        elif total < 0:
            details['summary'] = f"技术面偏空，{len(buy_signals)}个买入信号，{len(sell_signals)}个卖出信号"
        else:
            details['summary'] = f"技术面中性，{len(buy_signals)}个买入信号，{len(sell_signals)}个卖出信号"

        rsi = latest.get('rsi')
        if rsi is not None and not np.isnan(rsi):
            details['indicators']['RSI'] = f"{rsi:.1f}"
            if rsi < 30:
                details['indicators']['RSI状态'] = "超卖区"
            elif rsi > 70:
                details['indicators']['RSI状态'] = "超买区"
            else:
                details['indicators']['RSI状态'] = "正常区间"

        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        macd_hist = latest.get('macd_histogram')
        if macd_hist is not None and not np.isnan(macd_hist):
            details['indicators']['MACD柱'] = f"{macd_hist:.4f}"
            details['indicators']['MACD状态'] = "多头" if macd_hist > 0 else "空头"

        percent_b = latest.get('percent_b')
        if percent_b is not None and not np.isnan(percent_b):
            details['indicators']['布林带%b'] = f"{percent_b:.1f}"

        return details

    def _calculate_valuation_score(
        self,
        valuation_metrics: Optional[ValuationMetrics],
        quote: Optional[Dict[str, Any]]
    ) -> Optional[DimensionScore]:
        if not valuation_metrics:
            return None

        score = DimensionScore(name=ScoreDimension.VALUATION.value)
        total_score = 0.0
        max_score = 0.0

        score.raw_metrics = {
            'pe_trailing': valuation_metrics.pe_trailing,
            'pe_forward': valuation_metrics.pe_forward,
            'pb_ratio': valuation_metrics.pb_ratio,
            'peg_ratio': valuation_metrics.peg_ratio,
            'price_to_sales': valuation_metrics.price_to_sales,
            'ev_to_ebitda': valuation_metrics.ev_to_ebitda,
            'dividend_yield': valuation_metrics.dividend_yield,
            'margin_of_safety': valuation_metrics.margin_of_safety,
        }

        pe = valuation_metrics.pe_trailing
        if pe and pe > 0:
            if pe < 10:
                total_score += 20
            elif pe < 15:
                total_score += 18
            elif pe < 20:
                total_score += 15
            elif pe < 25:
                total_score += 10
            elif pe < 30:
                total_score += 5
            max_score += 20

        pe_forward = valuation_metrics.pe_forward
        if pe_forward and pe_forward > 0:
            if pe_forward < 10:
                total_score += 15
            elif pe_forward < 15:
                total_score += 13
            elif pe_forward < 20:
                total_score += 10
            elif pe_forward < 25:
                total_score += 7
            max_score += 15

        pb = valuation_metrics.pb_ratio
        if pb and pb > 0:
            if pb < 1:
                total_score += 20
            elif pb < 2:
                total_score += 16
            elif pb < 3:
                total_score += 12
            elif pb < 5:
                total_score += 6
            max_score += 20

        peg = valuation_metrics.peg_ratio
        if peg and peg > 0:
            if peg < 1:
                total_score += 15
            elif peg < 1.5:
                total_score += 12
            elif peg < 2:
                total_score += 8
            elif peg < 2.5:
                total_score += 4
            max_score += 15

        ps = valuation_metrics.price_to_sales
        if ps and ps > 0:
            if ps < 1:
                total_score += 10
            elif ps < 2:
                total_score += 8
            elif ps < 3:
                total_score += 5
            max_score += 10

        ev_ebitda = valuation_metrics.ev_to_ebitda
        if ev_ebitda and ev_ebitda > 0:
            if ev_ebitda < 5:
                total_score += 10
            elif ev_ebitda < 8:
                total_score += 8
            elif ev_ebitda < 10:
                total_score += 5
            elif ev_ebitda < 15:
                total_score += 2
            max_score += 10

        dy = valuation_metrics.dividend_yield
        if dy and dy > 0:
            if dy >= 5:
                total_score += 10
            elif dy >= 3:
                total_score += 8
            elif dy >= 2:
                total_score += 6
            elif dy >= 1:
                total_score += 4
            max_score += 10

        mos = valuation_metrics.margin_of_safety
        if mos is not None:
            if mos >= 50:
                total_score += 15
            elif mos >= 30:
                total_score += 12
            elif mos >= 15:
                total_score += 10
            elif mos >= 0:
                total_score += 5
            elif mos >= -20:
                total_score += 2
            max_score += 15

        if max_score > 0:
            score.score = (total_score / max_score) * 100
        else:
            score.score = 50.0

        score.details = self._generate_valuation_details(valuation_metrics)

        return score

    def _generate_valuation_details(self, metrics: ValuationMetrics) -> Dict[str, Any]:
        details = {
            'summary': '',
            'metrics': {},
            'status': ''
        }

        metric_items = []

        if metrics.pe_trailing and metrics.pe_trailing > 0:
            metric_items.append(f"PE(TTM): {metrics.pe_trailing:.2f}")
            details['metrics']['PE(TTM)'] = f"{metrics.pe_trailing:.2f}"

        if metrics.pe_forward and metrics.pe_forward > 0:
            metric_items.append(f"PE(Forward): {metrics.pe_forward:.2f}")
            details['metrics']['PE(Forward)'] = f"{metrics.pe_forward:.2f}"

        if metrics.pb_ratio and metrics.pb_ratio > 0:
            metric_items.append(f"PB: {metrics.pb_ratio:.2f}")
            details['metrics']['PB'] = f"{metrics.pb_ratio:.2f}"

        if metrics.peg_ratio and metrics.peg_ratio > 0:
            metric_items.append(f"PEG: {metrics.peg_ratio:.2f}")
            details['metrics']['PEG'] = f"{metrics.peg_ratio:.2f}"

        if metrics.dividend_yield and metrics.dividend_yield > 0:
            metric_items.append(f"股息率: {metrics.dividend_yield:.2f}%")
            details['metrics']['股息率'] = f"{metrics.dividend_yield:.2f}%"

        if metrics.margin_of_safety is not None:
            metric_items.append(f"安全边际: {metrics.margin_of_safety:.1f}%")
            details['metrics']['安全边际'] = f"{metrics.margin_of_safety:.1f}%"

            if metrics.margin_of_safety >= 30:
                details['status'] = "估值较低，有安全边际"
            elif metrics.margin_of_safety >= 0:
                details['status'] = "估值合理"
            else:
                details['status'] = "估值偏高"

        details['summary'] = " | ".join(metric_items) if metric_items else "暂无完整估值数据"

        return details

    def _calculate_momentum_score(
        self,
        technical_data: Optional[Dict[str, Any]],
        quote: Optional[Dict[str, Any]]
    ) -> Optional[DimensionScore]:
        if not technical_data:
            return None

        score = DimensionScore(name=ScoreDimension.MOMENTUM.value)
        total_score = 0.0
        max_score = 0.0

        price_data = technical_data.get('price_data', {})
        closes = price_data.get('close', [])
        volumes = price_data.get('volume', [])

        score.raw_metrics = {
            'close_prices': closes[-20:] if closes else [],
            'volumes': volumes[-20:] if volumes else [],
        }

        if len(closes) >= 5:
            last_close = closes[-1]
            prev_close = closes[-2] if len(closes) >= 2 else last_close

            ma = technical_data.get('ma', {})
            ma_5 = ma.get(5, [])
            ma_20 = ma.get(20, [])
            ma_50 = ma.get(50, [])
            ma_200 = ma.get(200, [])

            score.raw_metrics['ma_5'] = ma_5[-5:] if ma_5 else []
            score.raw_metrics['ma_20'] = ma_20[-5:] if ma_20 else []
            score.raw_metrics['ma_50'] = ma_50[-5:] if ma_50 else []

            if len(ma_5) >= 2 and len(ma_20) >= 2:
                ma5_last = ma_5[-1] if not np.isnan(ma_5[-1]) else None
                ma5_prev = ma_5[-2] if not np.isnan(ma_5[-2]) else None
                ma20_last = ma_20[-1] if not np.isnan(ma_20[-1]) else None
                ma20_prev = ma_20[-2] if not np.isnan(ma_20[-2]) else None

                if ma5_last and ma20_last and ma5_prev and ma20_prev:
                    if ma5_last > ma20_last:
                        total_score += 20
                        if ma5_prev <= ma20_prev:
                            total_score += 10
                    else:
                        total_score -= 10
                    max_score += 30

                    score.raw_metrics['ma5_above_ma20'] = ma5_last > ma20_last
                    score.raw_metrics['ma5_crossup_ma20'] = (ma5_last > ma20_last) and (ma5_prev <= ma20_prev)

            if len(ma_50) >= 2 and len(ma_200) >= 2:
                ma50_last = ma_50[-1] if not np.isnan(ma_50[-1]) else None
                ma50_prev = ma_50[-2] if not np.isnan(ma_50[-2]) else None
                ma200_last = ma_200[-1] if not np.isnan(ma_200[-1]) else None
                ma200_prev = ma_200[-2] if not np.isnan(ma_200[-2]) else None

                if ma50_last and ma200_last and ma50_prev and ma200_prev:
                    if ma50_last > ma200_last:
                        total_score += 15
                        if ma50_prev <= ma200_prev:
                            total_score += 10
                    else:
                        total_score -= 5
                    max_score += 25

                    score.raw_metrics['ma50_above_ma200'] = ma50_last > ma200_last
                    score.raw_metrics['golden_cross'] = (ma50_last > ma200_last) and (ma50_prev <= ma200_prev)

            if len(closes) >= 5:
                ma5_val = ma_5[-1] if ma_5 and len(ma_5) > 0 and not np.isnan(ma_5[-1]) else None
                if ma5_val:
                    if last_close > ma5_val:
                        total_score += 10
                    else:
                        total_score -= 5
                    max_score += 10
                    score.raw_metrics['price_above_ma5'] = last_close > ma5_val

            if len(closes) >= 10:
                returns_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if closes[-6] > 0 else 0
                returns_10d = (closes[-1] - closes[-11]) / closes[-11] * 100 if closes[-11] > 0 else 0

                score.raw_metrics['returns_5d'] = returns_5d
                score.raw_metrics['returns_10d'] = returns_10d

                if returns_5d > 5:
                    total_score += 15
                elif returns_5d > 2:
                    total_score += 10
                elif returns_5d > 0:
                    total_score += 5
                elif returns_5d < -5:
                    total_score -= 15
                elif returns_5d < -2:
                    total_score -= 10
                elif returns_5d < 0:
                    total_score -= 5
                max_score += 15

                if returns_10d > 10:
                    total_score += 10
                elif returns_10d > 5:
                    total_score += 7
                elif returns_10d > 0:
                    total_score += 3
                elif returns_10d < -10:
                    total_score -= 10
                elif returns_10d < -5:
                    total_score -= 7
                elif returns_10d < 0:
                    total_score -= 3
                max_score += 10

        if max_score > 0:
            normalized = ((total_score + max_score) / (2 * max_score)) * 100
            score.score = max(0.0, min(100.0, normalized))
        else:
            score.score = 50.0

        score.details = self._generate_momentum_details(score.raw_metrics)

        return score

    def _generate_momentum_details(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        details = {
            'summary': '',
            'signals': [],
            'performance': {}
        }

        signals = []

        if raw_metrics.get('ma5_above_ma20'):
            signals.append("MA5 > MA20 (短期偏多)")
        else:
            signals.append("MA5 < MA20 (短期偏空)")

        if raw_metrics.get('ma50_above_ma200'):
            signals.append("MA50 > MA200 (中长期偏多)")
        else:
            signals.append("MA50 < MA200 (中长期偏空)")

        if raw_metrics.get('golden_cross'):
            signals.append("黄金交叉！")

        if raw_metrics.get('price_above_ma5'):
            signals.append("价格在MA5上方")
        else:
            signals.append("价格在MA5下方")

        returns_5d = raw_metrics.get('returns_5d')
        returns_10d = raw_metrics.get('returns_10d')

        if returns_5d is not None:
            details['performance']['5日收益'] = f"{returns_5d:+.2f}%"
        if returns_10d is not None:
            details['performance']['10日收益'] = f"{returns_10d:+.2f}%"

        details['signals'] = signals
        details['summary'] = " | ".join(signals) if signals else "暂无动量数据"

        return details

    def _calculate_market_cap_score(
        self,
        quote: Optional[Dict[str, Any]],
        valuation_metrics: Optional[ValuationMetrics]
    ) -> Optional[DimensionScore]:
        score = DimensionScore(name=ScoreDimension.MARKET_CAP.value)

        market_cap = None
        if quote and quote.get('market_cap'):
            market_cap = quote.get('market_cap')
        elif valuation_metrics and valuation_metrics.market_cap:
            market_cap = valuation_metrics.market_cap

        score.raw_metrics = {
            'market_cap': market_cap,
        }

        if market_cap and market_cap > 0:
            if market_cap >= 2e11:
                score.score = 85
                score.details = {'category': '超大盘股 (>$200B)', 'size': f"${market_cap/1e12:.2f}T"}
            elif market_cap >= 1e11:
                score.score = 80
                score.details = {'category': '大盘股 ($100B-$200B)', 'size': f"${market_cap/1e9:.2f}B"}
            elif market_cap >= 2e10:
                score.score = 75
                score.details = {'category': '中大盘股 ($20B-$100B)', 'size': f"${market_cap/1e9:.2f}B"}
            elif market_cap >= 1e10:
                score.score = 70
                score.details = {'category': '中盘股 ($10B-$20B)', 'size': f"${market_cap/1e9:.2f}B"}
            elif market_cap >= 2e9:
                score.score = 65
                score.details = {'category': '中小盘股 ($2B-$10B)', 'size': f"${market_cap/1e9:.2f}B"}
            elif market_cap >= 3e8:
                score.score = 55
                score.details = {'category': '小盘股 ($300M-$2B)', 'size': f"${market_cap/1e6:.2f}M"}
            else:
                score.score = 40
                score.details = {'category': '微盘股 (<$300M)', 'size': f"${market_cap/1e6:.2f}M"}
        else:
            score.score = 50.0
            score.details = {'category': '未知', 'size': 'N/A'}

        score.details['summary'] = f"{score.details.get('category', '未知')} - 市值评分: {score.score:.0f}分"

        return score

    def _calculate_volume_price_score(
        self,
        technical_data: Optional[Dict[str, Any]]
    ) -> Optional[DimensionScore]:
        if not technical_data:
            return None

        score = DimensionScore(name=ScoreDimension.VOLUME_PRICE.value)
        total_score = 0.0
        max_score = 0.0

        volume = technical_data.get('volume', {})
        price_data = technical_data.get('price_data', {})
        closes = price_data.get('close', [])
        volumes = price_data.get('volume', [])

        score.raw_metrics = {
            'volume_ma_5': volume.get('volume_ma_5', [])[-5:] if volume.get('volume_ma_5') else [],
            'volume_ma_20': volume.get('volume_ma_20', [])[-5:] if volume.get('volume_ma_20') else [],
            'volume_change': volume.get('volume_change', [])[-5:] if volume.get('volume_change') else [],
            'volume_price_trend': volume.get('volume_price_trend', [])[-5:] if volume.get('volume_price_trend') else [],
        }

        vp_trend = volume.get('volume_price_trend', [])
        if vp_trend and len(vp_trend) > 0:
            latest_trend = vp_trend[-1]
            score.raw_metrics['latest_vp_trend'] = latest_trend

            if latest_trend == 1:
                total_score += 30
            elif latest_trend == -1:
                total_score -= 20
            max_score += 30

            if len(vp_trend) >= 3:
                recent_trends = vp_trend[-3:]
                bullish_count = sum(1 for t in recent_trends if t == 1)
                bearish_count = sum(1 for t in recent_trends if t == -1)

                if bullish_count >= 2:
                    total_score += 15
                elif bearish_count >= 2:
                    total_score -= 10
                max_score += 15

        vol_ma_5 = volume.get('volume_ma_5', [])
        vol_ma_20 = volume.get('volume_ma_20', [])

        if len(vol_ma_5) >= 1 and len(vol_ma_20) >= 1 and len(volumes) >= 1:
            latest_vol = volumes[-1]
            ma5_vol = vol_ma_5[-1] if not np.isnan(vol_ma_5[-1]) else None
            ma20_vol = vol_ma_20[-1] if not np.isnan(vol_ma_20[-1]) else None

            if ma20_vol and ma20_vol > 0:
                volume_ratio = latest_vol / ma20_vol
                score.raw_metrics['volume_ratio'] = volume_ratio

                if volume_ratio > 2:
                    total_score += 20
                elif volume_ratio > 1.5:
                    total_score += 15
                elif volume_ratio > 1:
                    total_score += 8
                elif volume_ratio < 0.5:
                    total_score -= 5
                max_score += 20

        if len(closes) >= 5 and len(volumes) >= 5:
            price_changes = []
            vol_changes = []

            for i in range(1, min(5, len(closes))):
                if closes[i-1] > 0:
                    price_changes.append((closes[i] - closes[i-1]) / closes[i-1])
                if volumes[i-1] > 0:
                    vol_changes.append((volumes[i] - volumes[i-1]) / volumes[i-1])

            if price_changes and vol_changes:
                price_up = sum(1 for p in price_changes if p > 0)
                price_down = sum(1 for p in price_changes if p < 0)
                vol_up = sum(1 for v in vol_changes if v > 0)

                if price_up > price_down and vol_up > len(vol_changes) / 2:
                    total_score += 20
                elif price_up < price_down and vol_up > len(vol_changes) / 2:
                    total_score -= 15
                max_score += 20

        if max_score > 0:
            normalized = ((total_score + max_score) / (2 * max_score)) * 100
            score.score = max(0.0, min(100.0, normalized))
        else:
            score.score = 50.0

        score.details = self._generate_volume_price_details(score.raw_metrics)

        return score

    def _generate_volume_price_details(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        details = {
            'summary': '',
            'signals': [],
            'metrics': {}
        }

        signals = []

        latest_trend = raw_metrics.get('latest_vp_trend')
        if latest_trend == 1:
            signals.append("放量上涨")
        elif latest_trend == -1:
            signals.append("放量下跌")
        else:
            signals.append("量价平稳")

        volume_ratio = raw_metrics.get('volume_ratio')
        if volume_ratio is not None:
            details['metrics']['量比'] = f"{volume_ratio:.2f}"
            if volume_ratio > 2:
                signals.append("明显放量")
            elif volume_ratio > 1.5:
                signals.append("温和放量")
            elif volume_ratio < 0.5:
                signals.append("缩量")

        details['signals'] = signals
        details['summary'] = " | ".join(signals) if signals else "暂无量价数据"

        return details

    def _calculate_volatility_score(
        self,
        symbol: str
    ) -> Optional[DimensionScore]:
        score = DimensionScore(name=ScoreDimension.VOLATILITY.value)

        try:
            metrics = self._volatility_analyzer.analyze_stock(symbol, period='6mo')

            if metrics is None:
                score.score = 50.0
                score.details = {'summary': '无法获取波动率数据'}
                score.raw_metrics = {}
                return score

            score.raw_metrics = {
                'vol_5d': metrics.vol_5d,
                'vol_5d_annualized': metrics.vol_5d_annualized,
                'vol_10d': metrics.vol_10d,
                'vol_10d_annualized': metrics.vol_10d_annualized,
                'vol_20d': metrics.vol_20d,
                'vol_20d_annualized': metrics.vol_20d_annualized,
                'vol_60d': metrics.vol_60d,
                'vol_60d_annualized': metrics.vol_60d_annualized,
                'vol_ratio_5_20': metrics.vol_ratio_5_20,
                'vol_ratio_20_60': metrics.vol_ratio_20_60,
                'vol_trend': metrics.vol_trend,
                'current_vol': metrics.current_vol,
                'historical_vol_mean': metrics.historical_vol_mean,
                'historical_vol_std': metrics.historical_vol_std,
                'alert_type': metrics.alert_type.value if metrics.alert_type else None,
                'volatility_return_correlation': metrics.volatility_return_correlation,
                'correlation_significance': metrics.correlation_significance,
            }

            total_score = 0.0
            max_score = 0.0

            ann_vol = metrics.vol_20d_annualized
            if ann_vol and ann_vol > 0:
                if ann_vol < 0.15:
                    total_score += 35
                elif ann_vol < 0.25:
                    total_score += 30
                elif ann_vol < 0.35:
                    total_score += 20
                elif ann_vol < 0.50:
                    total_score += 10
                else:
                    total_score -= 15
                max_score += 35

            vol_ratio_20_60 = metrics.vol_ratio_20_60
            if vol_ratio_20_60 and vol_ratio_20_60 > 0:
                if 0.9 <= vol_ratio_20_60 <= 1.1:
                    total_score += 20
                elif 0.8 <= vol_ratio_20_60 < 0.9 or 1.1 < vol_ratio_20_60 <= 1.2:
                    total_score += 15
                elif 0.7 <= vol_ratio_20_60 < 0.8 or 1.2 < vol_ratio_20_60 <= 1.4:
                    total_score += 8
                else:
                    total_score -= 5
                max_score += 20

            alert_type = metrics.alert_type
            if alert_type:
                from .volatility_analyzer import VolatilityAlertType
                if alert_type == VolatilityAlertType.NO_ALERT:
                    total_score += 15
                elif alert_type == VolatilityAlertType.BREAKOUT_LOW:
                    total_score += 10
                elif alert_type == VolatilityAlertType.BREAKOUT_HIGH:
                    total_score -= 10
                max_score += 15

            vol_return_corr = metrics.volatility_return_correlation
            if vol_return_corr is not None and not np.isnan(vol_return_corr):
                if vol_return_corr < -0.3:
                    total_score += 15
                elif vol_return_corr < -0.1:
                    total_score += 10
                elif vol_return_corr < 0.1:
                    total_score += 5
                elif vol_return_corr > 0.3:
                    total_score -= 10
                max_score += 15

            if max_score > 0:
                score.score = (total_score / max_score) * 100
            else:
                score.score = 50.0

            score.score = max(0.0, min(100.0, score.score))

            score.details = self._generate_volatility_details(metrics)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"计算波动率评分失败: {e}")
            score.score = 50.0
            score.details = {'summary': '波动率计算失败'}
            score.raw_metrics = {}

        return score

    def _generate_volatility_details(self, metrics) -> Dict[str, Any]:
        details = {
            'summary': '',
            'metrics': {},
            'risk_level': ''
        }

        metric_items = []

        if metrics.vol_20d_annualized:
            details['metrics']['20日年化波动率'] = f"{metrics.vol_20d_annualized*100:.1f}%"
            metric_items.append(f"20日年化波动: {metrics.vol_20d_annualized*100:.1f}%")

        if metrics.vol_5d_annualized:
            details['metrics']['5日年化波动率'] = f"{metrics.vol_5d_annualized*100:.1f}%"
            metric_items.append(f"5日年化波动: {metrics.vol_5d_annualized*100:.1f}%")

        if metrics.vol_60d_annualized:
            details['metrics']['60日年化波动率'] = f"{metrics.vol_60d_annualized*100:.1f}%"

        if metrics.vol_ratio_20_60 and metrics.vol_ratio_20_60 > 0:
            details['metrics']['20日/60日波动率比'] = f"{metrics.vol_ratio_20_60:.2f}"
            metric_items.append(f"20日/60日波动比: {metrics.vol_ratio_20_60:.2f}")

        if metrics.vol_trend:
            details['metrics']['波动率趋势'] = metrics.vol_trend
            metric_items.append(f"波动趋势: {metrics.vol_trend}")

        if metrics.alert_type:
            details['metrics']['波动率预警'] = metrics.alert_type.value
            metric_items.append(f"预警状态: {metrics.alert_type.value}")

        if metrics.correlation_significance:
            details['metrics']['波动率-收益相关性'] = metrics.correlation_significance

        ann_vol = metrics.vol_20d_annualized
        if ann_vol:
            if ann_vol < 0.15:
                details['risk_level'] = "低风险"
            elif ann_vol < 0.25:
                details['risk_level'] = "中低风险"
            elif ann_vol < 0.35:
                details['risk_level'] = "中等风险"
            elif ann_vol < 0.50:
                details['risk_level'] = "中高风险"
            else:
                details['risk_level'] = "高风险"

        details['summary'] = " | ".join(metric_items) if metric_items else "暂无波动率数据"

        return details

    def _calculate_growth_score(
        self,
        valuation_metrics: Optional[ValuationMetrics]
    ) -> Optional[DimensionScore]:
        if not valuation_metrics:
            return None

        score = DimensionScore(name=ScoreDimension.GROWTH_POTENTIAL.value)
        total_score = 0.0
        max_score = 0.0

        score.raw_metrics = {
            'growth_rate_5y': valuation_metrics.growth_rate_5y,
            'roe': valuation_metrics.roe,
            'roa': valuation_metrics.roa,
            'revenue_growth': valuation_metrics.revenue_growth,
            'earnings_growth': valuation_metrics.earnings_growth,
            'fcf_growth': valuation_metrics.fcf_growth,
        }

        growth_5y = valuation_metrics.growth_rate_5y
        if growth_5y and growth_5y > 0:
            if growth_5y >= 20:
                total_score += 30
            elif growth_5y >= 15:
                total_score += 25
            elif growth_5y >= 10:
                total_score += 20
            elif growth_5y >= 5:
                total_score += 12
            elif growth_5y >= 0:
                total_score += 5
            max_score += 30

        roe = valuation_metrics.roe
        if roe and roe > 0:
            if roe >= 20:
                total_score += 25
            elif roe >= 15:
                total_score += 20
            elif roe >= 10:
                total_score += 15
            elif roe >= 5:
                total_score += 8
            max_score += 25

        roa = valuation_metrics.roa
        if roa and roa > 0:
            if roa >= 15:
                total_score += 20
            elif roa >= 10:
                total_score += 15
            elif roa >= 5:
                total_score += 10
            elif roa >= 2:
                total_score += 5
            max_score += 20

        de = valuation_metrics.debt_to_equity
        if de is not None:
            if de < 0.5:
                total_score += 15
            elif de < 1.0:
                total_score += 12
            elif de < 1.5:
                total_score += 8
            elif de < 2.0:
                total_score += 4
            max_score += 15

        fcf = valuation_metrics.free_cash_flow
        if fcf and fcf > 0:
            total_score += 10
            max_score += 10

        if max_score > 0:
            score.score = (total_score / max_score) * 100
        else:
            score.score = 50.0

        score.details = self._generate_growth_details(valuation_metrics)

        return score

    def _generate_growth_details(self, metrics: ValuationMetrics) -> Dict[str, Any]:
        details = {
            'summary': '',
            'metrics': {},
            'growth_outlook': ''
        }

        metric_items = []

        if metrics.growth_rate_5y and metrics.growth_rate_5y > 0:
            details['metrics']['预期5年增长'] = f"{metrics.growth_rate_5y:.1f}%"
            metric_items.append(f"预期增长: {metrics.growth_rate_5y:.1f}%")

        if metrics.roe and metrics.roe > 0:
            details['metrics']['ROE'] = f"{metrics.roe:.1f}%"
            metric_items.append(f"ROE: {metrics.roe:.1f}%")

        if metrics.roa and metrics.roa > 0:
            details['metrics']['ROA'] = f"{metrics.roa:.1f}%"
            metric_items.append(f"ROA: {metrics.roa:.1f}%")

        if metrics.debt_to_equity is not None:
            details['metrics']['债务权益比'] = f"{metrics.debt_to_equity:.2f}"
            metric_items.append(f"债务权益比: {metrics.debt_to_equity:.2f}")

        growth_indicators = 0
        if metrics.growth_rate_5y and metrics.growth_rate_5y >= 10:
            growth_indicators += 1
        if metrics.roe and metrics.roe >= 15:
            growth_indicators += 1
        if metrics.debt_to_equity is not None and metrics.debt_to_equity < 1:
            growth_indicators += 1

        if growth_indicators >= 3:
            details['growth_outlook'] = "成长潜力优秀"
        elif growth_indicators >= 2:
            details['growth_outlook'] = "成长潜力良好"
        elif growth_indicators >= 1:
            details['growth_outlook'] = "成长潜力一般"
        else:
            details['growth_outlook'] = "成长潜力较弱"

        details['summary'] = " | ".join(metric_items) if metric_items else "暂无成长数据"

        return details

    def calculate_multiple(
        self,
        symbols: List[str],
        weights: Optional[Dict[str, float]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Optional[StockScoreResult]]:
        results = []
        total = len(symbols)

        for idx, symbol in enumerate(symbols):
            try:
                if progress_callback:
                    progress_callback(idx + 1, total, symbol)

                result = self.calculate_score(symbol, weights)
                results.append(result)
            except Exception as e:
                print(f"计算股票 {symbol} 评分失败: {e}")
                results.append(None)

        return results
