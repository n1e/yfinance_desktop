import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

from .technical_analyzer import TechnicalAnalyzer
from .valuation_analyzer import ValuationAnalyzer, ValuationMetrics
from .data_provider import DataProvider
from .volatility_analyzer import VolatilityAnalyzer
from .config import ConfigManager


class HealthDimension(Enum):
    LIQUIDITY = "流动性评分"
    VALUATION = "估值评分"
    DIVERSIFICATION = "分散度评分"
    VOLATILITY = "波动性评分"
    TREND = "趋势评分"


@dataclass
class DimensionScore:
    name: str
    score: float = 0.0
    weight: float = 0.2
    max_score: float = 100.0
    details: Dict[str, Any] = field(default_factory=dict)
    raw_metrics: Dict[str, Any] = field(default_factory=dict)
    calculation_logic: str = ""
    current_value: str = ""


@dataclass
class OptimizationSuggestion:
    category: str
    severity: str
    title: str
    description: str
    action: str
    related_symbols: List[str] = field(default_factory=list)


@dataclass
class PortfolioHealthResult:
    total_symbols: int = 0
    valid_symbols: int = 0
    total_score: float = 0.0
    weighted_score: float = 0.0
    status: str = ""
    calculated_at: datetime = field(default_factory=datetime.now)
    
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    individual_scores: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    industry_distribution: Dict[str, float] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_dimensions(self) -> List[str]:
        return list(self.dimension_scores.keys())
    
    def get_score_by_dimension(self, dimension: str) -> float:
        if dimension in self.dimension_scores:
            return self.dimension_scores[dimension].score
        return 0.0


@dataclass
class HealthHistoryRecord:
    date: datetime
    total_score: float
    weighted_score: float
    status: str
    dimension_scores: Dict[str, float]
    total_symbols: int


class PortfolioHealthAnalyzer:
    DEFAULT_WEIGHTS = {
        HealthDimension.LIQUIDITY.value: 0.20,
        HealthDimension.VALUATION.value: 0.20,
        HealthDimension.DIVERSIFICATION.value: 0.20,
        HealthDimension.VOLATILITY.value: 0.20,
        HealthDimension.TREND.value: 0.20,
    }
    
    def __init__(self):
        self._technical_analyzer = TechnicalAnalyzer()
        self._valuation_analyzer = ValuationAnalyzer()
        self._data_provider = DataProvider()
        self._volatility_analyzer = VolatilityAnalyzer()
        self._config = ConfigManager()
        self._weights = self.DEFAULT_WEIGHTS.copy()
        self._history_file = self._get_history_file_path()
        self._history: List[HealthHistoryRecord] = []
        self._load_history()
    
    def _get_history_file_path(self) -> str:
        config_dir = Path.home() / ".stock_monitor"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "health_history.json")
    
    def _load_history(self):
        if not os.path.exists(self._history_file):
            self._history = []
            return
        
        try:
            with open(self._history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._history = []
            for item in data:
                record = HealthHistoryRecord(
                    date=datetime.fromisoformat(item['date']),
                    total_score=item['total_score'],
                    weighted_score=item['weighted_score'],
                    status=item['status'],
                    dimension_scores=item.get('dimension_scores', {}),
                    total_symbols=item.get('total_symbols', 0)
                )
                self._history.append(record)
            
            self._history.sort(key=lambda x: x.date)
            
        except Exception as e:
            print(f"加载健康度历史数据失败: {e}")
            self._history = []
    
    def _save_history(self):
        try:
            data = []
            for record in self._history:
                data.append({
                    'date': record.date.isoformat(),
                    'total_score': record.total_score,
                    'weighted_score': record.weighted_score,
                    'status': record.status,
                    'dimension_scores': record.dimension_scores,
                    'total_symbols': record.total_symbols
                })
            
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存健康度历史数据失败: {e}")
    
    def add_history_record(self, result: PortfolioHealthResult):
        today = datetime.now().date()
        
        existing = [r for r in self._history if r.date.date() == today]
        if existing:
            return
        
        dimension_scores = {}
        for name, dim in result.dimension_scores.items():
            dimension_scores[name] = dim.score
        
        record = HealthHistoryRecord(
            date=datetime.now(),
            total_score=result.total_score,
            weighted_score=result.weighted_score,
            status=result.status,
            dimension_scores=dimension_scores,
            total_symbols=result.total_symbols
        )
        
        self._history.append(record)
        
        max_records = 365
        if len(self._history) > max_records:
            self._history = self._history[-max_records:]
        
        self._save_history()
    
    def get_history(self, days: int = 30) -> List[HealthHistoryRecord]:
        cutoff = datetime.now() - timedelta(days=days)
        return [r for r in self._history if r.date >= cutoff]
    
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
    
    def analyze_portfolio(
        self,
        symbols: List[str],
        weights: Optional[Dict[str, float]] = None,
        progress_callback: Optional[callable] = None
    ) -> PortfolioHealthResult:
        result = PortfolioHealthResult()
        result.total_symbols = len(symbols)
        
        if weights:
            original_weights = self._weights.copy()
            self.set_weights(weights)
        else:
            original_weights = None
        
        all_quotes = {}
        all_valuations = {}
        all_technicals = {}
        all_info = {}
        
        for idx, symbol in enumerate(symbols):
            if progress_callback:
                progress_callback(idx + 1, len(symbols), symbol)
            
            symbol = symbol.upper().strip()
            
            quote = self._data_provider.get_stock_quote(symbol)
            if quote:
                all_quotes[symbol] = quote
            
            info = self._data_provider.get_stock_info(symbol)
            if info:
                all_info[symbol] = info
            
            valuation = self._valuation_analyzer.get_valuation_metrics(symbol)
            if valuation:
                all_valuations[symbol] = valuation
            
            technical = self._technical_analyzer.analyze_all_indicators(symbol, period='6mo')
            if technical:
                all_technicals[symbol] = technical
        
        result.valid_symbols = len(all_quotes)
        result.raw_data = {
            'quotes': all_quotes,
            'valuations': all_valuations,
            'technicals': all_technicals,
            'info': all_info
        }
        
        result.individual_scores = self._calculate_individual_scores(
            all_quotes, all_valuations, all_technicals, all_info
        )
        
        liquidity_score = self._calculate_liquidity_score(all_quotes)
        result.dimension_scores[HealthDimension.LIQUIDITY.value] = liquidity_score
        
        valuation_score = self._calculate_valuation_score(all_valuations, all_quotes)
        result.dimension_scores[HealthDimension.VALUATION.value] = valuation_score
        
        diversification_score, industry_dist = self._calculate_diversification_score(all_info, all_quotes)
        result.dimension_scores[HealthDimension.DIVERSIFICATION.value] = diversification_score
        result.industry_distribution = industry_dist
        
        volatility_score = self._calculate_volatility_score(symbols)
        result.dimension_scores[HealthDimension.VOLATILITY.value] = volatility_score
        
        trend_score = self._calculate_trend_score(all_technicals, all_quotes)
        result.dimension_scores[HealthDimension.TREND.value] = trend_score
        
        total_score = 0.0
        weighted_score = 0.0
        count = 0
        
        for dim_name, dim_score in result.dimension_scores.items():
            if dim_score:
                weight = self._weights.get(dim_name, 0.2)
                dim_score.weight = weight
                total_score += dim_score.score
                weighted_score += dim_score.score * weight
                count += 1
        
        result.total_score = total_score / count if count > 0 else 0.0
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
        
        result.suggestions = self._generate_suggestions(result, all_quotes, all_info)
        
        if original_weights:
            self._weights = original_weights
        
        return result
    
    def _calculate_individual_scores(
        self,
        quotes: Dict[str, Dict[str, Any]],
        valuations: Dict[str, ValuationMetrics],
        technicals: Dict[str, Dict[str, Any]],
        info: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        individual = {}
        
        for symbol, quote in quotes.items():
            individual[symbol] = {
                'symbol': symbol,
                'name': quote.get('name', symbol),
                'current_price': quote.get('current_price', 0),
                'change_percent': quote.get('change_percent', 0),
                'volume': quote.get('volume', 0),
                'market_cap': quote.get('market_cap', 0),
                'liquidity_metric': 0.0,
                'valuation_metric': 0.0,
                'volatility_metric': 0.0,
                'trend_metric': 0.0,
                'industry': info.get(symbol, {}).get('industry', '未知'),
                'sector': info.get(symbol, {}).get('sector', '未知'),
            }
            
            volume = quote.get('volume', 0)
            market_cap = quote.get('market_cap', 0)
            if market_cap > 0 and volume > 0:
                turnover = (volume * quote.get('current_price', 0)) / market_cap
                individual[symbol]['liquidity_metric'] = turnover * 100
            
            valuation = valuations.get(symbol)
            if valuation:
                pe = valuation.pe_trailing or 0
                pb = valuation.pb_ratio or 0
                individual[symbol]['valuation_metric'] = (pe + pb * 10) / 2 if pe > 0 and pb > 0 else 0
            
            technical = technicals.get(symbol)
            if technical:
                latest = technical.get('latest', {})
                rsi = latest.get('rsi')
                macd_hist = latest.get('macd_histogram')
                
                trend_score = 0
                if rsi is not None and not np.isnan(rsi):
                    if 40 <= rsi <= 60:
                        trend_score += 50
                    elif 30 <= rsi < 40 or 60 < rsi <= 70:
                        trend_score += 30
                
                if macd_hist is not None and not np.isnan(macd_hist):
                    if macd_hist > 0:
                        trend_score += 50
                
                individual[symbol]['trend_metric'] = trend_score
        
        return individual
    
    def _calculate_liquidity_score(
        self,
        quotes: Dict[str, Dict[str, Any]]
    ) -> DimensionScore:
        score = DimensionScore(name=HealthDimension.LIQUIDITY.value)
        score.calculation_logic = "成交量/市值比值，反映股票流动性好坏。比值越高流动性越好。"
        
        if not quotes:
            score.score = 50.0
            score.current_value = "无数据"
            score.details = {'summary': '无可用行情数据'}
            return score
        
        total_turnover = 0.0
        valid_count = 0
        low_liquidity_symbols = []
        high_liquidity_symbols = []
        
        for symbol, quote in quotes.items():
            volume = quote.get('volume', 0)
            market_cap = quote.get('market_cap', 0)
            current_price = quote.get('current_price', 0)
            
            if market_cap > 0 and volume > 0 and current_price > 0:
                turnover_value = volume * current_price
                turnover_ratio = turnover_value / market_cap
                
                score.raw_metrics[symbol] = {
                    'volume': volume,
                    'market_cap': market_cap,
                    'turnover_value': turnover_value,
                    'turnover_ratio': turnover_ratio
                }
                
                total_turnover += turnover_ratio
                valid_count += 1
                
                if turnover_ratio < 0.001:
                    low_liquidity_symbols.append(symbol)
                elif turnover_ratio > 0.01:
                    high_liquidity_symbols.append(symbol)
        
        avg_turnover = total_turnover / valid_count if valid_count > 0 else 0
        
        if avg_turnover >= 0.01:
            score.score = 90.0
        elif avg_turnover >= 0.005:
            score.score = 75.0
        elif avg_turnover >= 0.002:
            score.score = 60.0
        elif avg_turnover >= 0.001:
            score.score = 45.0
        else:
            score.score = 30.0
        
        score.current_value = f"平均换手率: {avg_turnover*100:.3f}%"
        
        score.details = {
            'summary': f"组合平均换手率为 {avg_turnover*100:.3f}%",
            'avg_turnover': avg_turnover,
            'low_liquidity_symbols': low_liquidity_symbols,
            'high_liquidity_symbols': high_liquidity_symbols,
            'valid_count': valid_count
        }
        
        return score
    
    def _calculate_valuation_score(
        self,
        valuations: Dict[str, ValuationMetrics],
        quotes: Dict[str, Dict[str, Any]]
    ) -> DimensionScore:
        score = DimensionScore(name=HealthDimension.VALUATION.value)
        score.calculation_logic = "综合PE/PB估值水平与历史分位比较，评估组合估值合理性。PE<15、PB<2为合理估值区间。"
        
        if not valuations:
            score.score = 50.0
            score.current_value = "无数据"
            score.details = {'summary': '无可用估值数据'}
            return score
        
        total_pe_score = 0.0
        total_pb_score = 0.0
        valid_pe_count = 0
        valid_pb_count = 0
        
        high_pe_symbols = []
        high_pb_symbols = []
        low_valuation_symbols = []
        
        for symbol, valuation in valuations.items():
            pe = valuation.pe_trailing or 0
            pb = valuation.pb_ratio or 0
            
            score.raw_metrics[symbol] = {
                'pe_trailing': pe,
                'pe_forward': valuation.pe_forward,
                'pb_ratio': pb,
                'peg_ratio': valuation.peg_ratio,
                'margin_of_safety': valuation.margin_of_safety
            }
            
            if pe > 0:
                if pe < 10:
                    total_pe_score += 90.0
                elif pe < 15:
                    total_pe_score += 75.0
                elif pe < 20:
                    total_pe_score += 55.0
                elif pe < 30:
                    total_pe_score += 35.0
                else:
                    total_pe_score += 15.0
                    if pe > 30:
                        high_pe_symbols.append(symbol)
                valid_pe_count += 1
                
                if pe < 15:
                    if symbol not in low_valuation_symbols:
                        low_valuation_symbols.append(symbol)
            
            if pb > 0:
                if pb < 1:
                    total_pb_score += 90.0
                elif pb < 2:
                    total_pb_score += 75.0
                elif pb < 3:
                    total_pb_score += 55.0
                elif pb < 5:
                    total_pb_score += 35.0
                else:
                    total_pb_score += 15.0
                    if pb > 5:
                        high_pb_symbols.append(symbol)
                valid_pb_count += 1
                
                if pb < 2:
                    if symbol not in low_valuation_symbols:
                        low_valuation_symbols.append(symbol)
        
        avg_pe_score = total_pe_score / valid_pe_count if valid_pe_count > 0 else 50.0
        avg_pb_score = total_pb_score / valid_pb_count if valid_pb_count > 0 else 50.0
        
        score.score = (avg_pe_score + avg_pb_score) / 2
        
        score.current_value = f"PE评分: {avg_pe_score:.0f}分, PB评分: {avg_pb_score:.0f}分"
        
        score.details = {
            'summary': f"组合估值综合评分为 {score.score:.0f}分",
            'avg_pe_score': avg_pe_score,
            'avg_pb_score': avg_pb_score,
            'high_pe_symbols': high_pe_symbols,
            'high_pb_symbols': high_pb_symbols,
            'low_valuation_symbols': low_valuation_symbols
        }
        
        return score
    
    def _calculate_diversification_score(
        self,
        info: Dict[str, Dict[str, Any]],
        quotes: Dict[str, Dict[str, Any]]
    ) -> Tuple[DimensionScore, Dict[str, float]]:
        score = DimensionScore(name=HealthDimension.DIVERSIFICATION.value)
        score.calculation_logic = "基于行业分布计算集中度。使用HHI指数：HHI<1500为分散，1500-2500为适度集中，>2500为高度集中。"
        
        industry_distribution = {}
        total_market_cap = 0.0
        
        for symbol, quote in quotes.items():
            stock_info = info.get(symbol, {})
            industry = stock_info.get('industry', '未知')
            sector = stock_info.get('sector', '未知')
            
            if industry == '未知' and sector != '未知':
                industry = sector
            
            market_cap = quote.get('market_cap', 0)
            if market_cap <= 0:
                market_cap = 1.0
            
            if industry not in industry_distribution:
                industry_distribution[industry] = 0.0
            industry_distribution[industry] += market_cap
            total_market_cap += market_cap
            
            score.raw_metrics[symbol] = {
                'industry': industry,
                'sector': sector,
                'market_cap': market_cap
            }
        
        industry_weights = {}
        if total_market_cap > 0:
            for industry, cap in industry_distribution.items():
                industry_weights[industry] = cap / total_market_cap
        
        hhi = 0.0
        for weight in industry_weights.values():
            hhi += (weight * 100) ** 2
        
        num_industries = len(industry_distribution)
        max_hhi = 10000.0
        
        if num_industries == 0:
            score.score = 50.0
            score.current_value = "无数据"
            score.details = {'summary': '无可用行业数据'}
            return score, industry_weights
        
        if num_industries == 1:
            score.score = 10.0
        elif hhi < 1500:
            score.score = 85.0
        elif hhi < 2500:
            score.score = 60.0
        else:
            score.score = 35.0
        
        if num_industries >= 5:
            score.score += 10
        elif num_industries >= 3:
            score.score += 5
        
        score.score = min(100.0, max(0.0, score.score))
        
        hhi_category = "分散" if hhi < 1500 else ("适度集中" if hhi < 2500 else "高度集中")
        score.current_value = f"HHI指数: {hhi:.0f} ({hhi_category}), 行业数: {num_industries}"
        
        score.details = {
            'summary': f"组合包含 {num_industries} 个行业，HHI指数为 {hhi:.0f}",
            'hhi': hhi,
            'hhi_category': hhi_category,
            'num_industries': num_industries,
            'industry_weights': industry_weights
        }
        
        return score, industry_weights
    
    def _calculate_volatility_score(
        self,
        symbols: List[str]
    ) -> DimensionScore:
        score = DimensionScore(name=HealthDimension.VOLATILITY.value)
        score.calculation_logic = "基于股票历史波动率（年化）评估组合风险。年化波动<20%为低风险，20%-35%为中等风险，>35%为高风险。"
        
        if not symbols:
            score.score = 50.0
            score.current_value = "无数据"
            score.details = {'summary': '无股票数据'}
            return score
        
        total_volatility = 0.0
        valid_count = 0
        high_vol_symbols = []
        low_vol_symbols = []
        
        for symbol in symbols:
            try:
                metrics = self._volatility_analyzer.analyze_stock(symbol, period='3mo')
                
                if metrics and metrics.vol_20d_annualized and metrics.vol_20d_annualized > 0:
                    vol = metrics.vol_20d_annualized
                    total_volatility += vol
                    valid_count += 1
                    
                    score.raw_metrics[symbol] = {
                        'vol_20d_annualized': vol,
                        'vol_5d_annualized': metrics.vol_5d_annualized,
                        'vol_trend': metrics.vol_trend,
                        'alert_type': metrics.alert_type.value if metrics.alert_type else None
                    }
                    
                    if vol > 0.35:
                        high_vol_symbols.append(symbol)
                    elif vol < 0.20:
                        low_vol_symbols.append(symbol)
                        
            except Exception as e:
                print(f"计算 {symbol} 波动率失败: {e}")
                continue
        
        avg_volatility = total_volatility / valid_count if valid_count > 0 else 0.25
        
        if avg_volatility < 0.15:
            score.score = 90.0
        elif avg_volatility < 0.20:
            score.score = 80.0
        elif avg_volatility < 0.25:
            score.score = 70.0
        elif avg_volatility < 0.35:
            score.score = 50.0
        elif avg_volatility < 0.50:
            score.score = 30.0
        else:
            score.score = 15.0
        
        risk_level = "低风险" if avg_volatility < 0.20 else ("中等风险" if avg_volatility < 0.35 else "高风险")
        score.current_value = f"平均年化波动率: {avg_volatility*100:.1f}% ({risk_level})"
        
        score.details = {
            'summary': f"组合平均年化波动率为 {avg_volatility*100:.1f}%",
            'avg_volatility': avg_volatility,
            'risk_level': risk_level,
            'high_vol_symbols': high_vol_symbols,
            'low_vol_symbols': low_vol_symbols,
            'valid_count': valid_count
        }
        
        return score
    
    def _calculate_trend_score(
        self,
        technicals: Dict[str, Dict[str, Any]],
        quotes: Dict[str, Dict[str, Any]]
    ) -> DimensionScore:
        score = DimensionScore(name=HealthDimension.TREND.value)
        score.calculation_logic = "基于MA均线系统和价格位置评估趋势状态。价格在MA5/MA20/MA60上方为多头趋势，反之为空头趋势。"
        
        if not technicals:
            score.score = 50.0
            score.current_value = "无数据"
            score.details = {'summary': '无可用技术数据'}
            return score
        
        total_trend_score = 0.0
        valid_count = 0
        bullish_symbols = []
        bearish_symbols = []
        neutral_symbols = []
        
        for symbol, technical in technicals.items():
            try:
                ma = technical.get('ma', {})
                price_data = technical.get('price_data', {})
                closes = price_data.get('close', [])
                
                if not closes or len(closes) < 20:
                    continue
                
                last_close = closes[-1]
                
                ma_5 = ma.get(5, [])
                ma_20 = ma.get(20, [])
                ma_60 = ma.get(60, [])
                
                ma5_val = ma_5[-1] if ma_5 and len(ma_5) > 0 and not np.isnan(ma_5[-1]) else None
                ma20_val = ma_20[-1] if ma_20 and len(ma_20) > 0 and not np.isnan(ma_20[-1]) else None
                ma60_val = ma_60[-1] if ma_60 and len(ma_60) > 0 and not np.isnan(ma_60[-1]) else None
                
                trend_points = 0
                max_points = 6
                
                if ma5_val and last_close > ma5_val:
                    trend_points += 2
                if ma20_val and last_close > ma20_val:
                    trend_points += 2
                if ma60_val and last_close > ma60_val:
                    trend_points += 2
                
                if ma5_val and ma20_val:
                    if ma5_val > ma20_val:
                        trend_points += 1
                        max_points += 1
                
                if ma20_val and ma60_val:
                    if ma20_val > ma60_val:
                        trend_points += 1
                        max_points += 1
                
                normalized_score = (trend_points / max_points) * 100 if max_points > 0 else 50
                
                total_trend_score += normalized_score
                valid_count += 1
                
                score.raw_metrics[symbol] = {
                    'last_close': last_close,
                    'ma5': ma5_val,
                    'ma20': ma20_val,
                    'ma60': ma60_val,
                    'trend_score': normalized_score
                }
                
                if normalized_score >= 70:
                    bullish_symbols.append(symbol)
                elif normalized_score <= 30:
                    bearish_symbols.append(symbol)
                else:
                    neutral_symbols.append(symbol)
                    
            except Exception as e:
                print(f"计算 {symbol} 趋势评分失败: {e}")
                continue
        
        avg_trend_score = total_trend_score / valid_count if valid_count > 0 else 50.0
        score.score = avg_trend_score
        
        trend_status = "多头趋势" if avg_trend_score >= 60 else ("空头趋势" if avg_trend_score <= 40 else "震荡整理")
        score.current_value = f"平均趋势评分: {avg_trend_score:.0f}分 ({trend_status})"
        
        score.details = {
            'summary': f"组合平均趋势评分为 {avg_trend_score:.0f}分",
            'avg_trend_score': avg_trend_score,
            'trend_status': trend_status,
            'bullish_symbols': bullish_symbols,
            'bearish_symbols': bearish_symbols,
            'neutral_symbols': neutral_symbols,
            'valid_count': valid_count
        }
        
        return score
    
    def _generate_suggestions(
        self,
        result: PortfolioHealthResult,
        quotes: Dict[str, Dict[str, Any]],
        info: Dict[str, Dict[str, Any]]
    ) -> List[OptimizationSuggestion]:
        suggestions = []
        
        liquidity = result.dimension_scores.get(HealthDimension.LIQUIDITY.value)
        if liquidity:
            low_liquidity = liquidity.details.get('low_liquidity_symbols', [])
            if low_liquidity and liquidity.score < 50:
                suggestions.append(OptimizationSuggestion(
                    category="流动性",
                    severity="warning",
                    title="部分股票流动性不足",
                    description=f"以下股票换手率较低：{', '.join(low_liquidity)}。流动性不足可能导致买卖滑点增大。",
                    action="建议关注成交量，考虑逐步减仓或换入流动性更好的标的。",
                    related_symbols=low_liquidity
                ))
        
        valuation = result.dimension_scores.get(HealthDimension.VALUATION.value)
        if valuation:
            high_pe = valuation.details.get('high_pe_symbols', [])
            high_pb = valuation.details.get('high_pb_symbols', [])
            
            if high_pe or high_pb:
                all_high = list(set(high_pe + high_pb))
                if valuation.score < 50:
                    suggestions.append(OptimizationSuggestion(
                        category="估值",
                        severity="warning",
                        title="组合估值偏高",
                        description=f"以下股票估值较高：{', '.join(all_high)}。高估值往往意味着更大的回调风险。",
                        action="建议评估估值合理性，考虑逐步降低高估值标的仓位。",
                        related_symbols=all_high
                    ))
            
            low_valuation = valuation.details.get('low_valuation_symbols', [])
            if low_valuation and valuation.score >= 60:
                suggestions.append(OptimizationSuggestion(
                    category="估值",
                    severity="info",
                    title="部分标的估值具有吸引力",
                    description=f"以下股票估值处于合理区间：{', '.join(low_valuation)}。",
                    action="可考虑重点关注这些估值合理的标的。",
                    related_symbols=low_valuation
                ))
        
        diversification = result.dimension_scores.get(HealthDimension.DIVERSIFICATION.value)
        if diversification:
            hhi = diversification.details.get('hhi', 0)
            industry_weights = diversification.details.get('industry_weights', {})
            
            if hhi >= 2500:
                top_industry = max(industry_weights.items(), key=lambda x: x[1]) if industry_weights else None
                if top_industry:
                    industry_name, weight = top_industry
                    suggestions.append(OptimizationSuggestion(
                        category="分散度",
                        severity="danger",
                        title="持仓过度集中于单一行业",
                        description=f"组合高度集中于 '{industry_name}' 行业，占比 {weight*100:.1f}%。行业集中度风险较高。",
                        action="强烈建议增加其他行业标的，降低单一行业暴露。",
                        related_symbols=self._get_symbols_by_industry(industry_name, result.individual_scores)
                    ))
            elif hhi >= 1500:
                suggestions.append(OptimizationSuggestion(
                    category="分散度",
                    severity="warning",
                    title="行业分布有待优化",
                    description=f"组合HHI指数为 {hhi:.0f}，处于适度集中区间。",
                    action="可考虑适当增加不同行业的配置。",
                    related_symbols=[]
                ))
        
        volatility = result.dimension_scores.get(HealthDimension.VOLATILITY.value)
        if volatility:
            high_vol = volatility.details.get('high_vol_symbols', [])
            risk_level = volatility.details.get('risk_level', '')
            
            if high_vol and risk_level in ["中等风险", "高风险"]:
                suggestions.append(OptimizationSuggestion(
                    category="波动性",
                    severity="warning" if risk_level == "中等风险" else "danger",
                    title="部分标的波动风险较高",
                    description=f"以下股票年化波动率超过35%：{', '.join(high_vol)}。",
                    action="建议评估风险承受能力，考虑适当降低高波动标的仓位或使用对冲策略。",
                    related_symbols=high_vol
                ))
        
        trend = result.dimension_scores.get(HealthDimension.TREND.value)
        if trend:
            bearish = trend.details.get('bearish_symbols', [])
            bullish = trend.details.get('bullish_symbols', [])
            trend_status = trend.details.get('trend_status', '')
            
            if bearish and len(bearish) > len(bullish):
                suggestions.append(OptimizationSuggestion(
                    category="趋势",
                    severity="warning",
                    title="较多标的处于空头趋势",
                    description=f"以下股票技术趋势偏弱：{', '.join(bearish)}。",
                    action="建议关注技术面变化，考虑设置止损或逐步减仓走弱标的。",
                    related_symbols=bearish
                ))
            
            if bullish and len(bullish) > len(bearish):
                suggestions.append(OptimizationSuggestion(
                    category="趋势",
                    severity="info",
                    title="较多标的处于多头趋势",
                    description=f"以下股票技术趋势偏强：{', '.join(bullish)}。",
                    action="可考虑重点关注这些趋势向好的标的。",
                    related_symbols=bullish
                ))
        
        if result.weighted_score >= 70:
            suggestions.append(OptimizationSuggestion(
                category="综合",
                severity="info",
                title="组合整体健康度良好",
                description=f"组合综合评分为 {result.weighted_score:.0f}分，状态为'{result.status}'。",
                action="继续保持当前配置，定期复查健康度。",
                related_symbols=[]
            ))
        elif result.weighted_score < 40:
            suggestions.append(OptimizationSuggestion(
                category="综合",
                severity="danger",
                title="组合健康度需要关注",
                description=f"组合综合评分为 {result.weighted_score:.0f}分，状态为'{result.status}'。",
                action="建议认真审视组合配置，参考上述建议进行优化。",
                related_symbols=[]
            ))
        
        return suggestions
    
    def _get_symbols_by_industry(
        self,
        industry: str,
        individual_scores: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        symbols = []
        for symbol, data in individual_scores.items():
            if data.get('industry') == industry:
                symbols.append(symbol)
        return symbols
