import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf
from dataclasses import dataclass
from enum import Enum


class VolatilityAlertType(Enum):
    NO_ALERT = "无预警"
    BREAKOUT_HIGH = "突破上轨 (高于均值+2σ)"
    BREAKOUT_LOW = "突破下轨 (低于均值-2σ)"


@dataclass
class VolatilityMetrics:
    symbol: str = ""
    latest_price: float = 0.0
    latest_date: datetime = None
    
    vol_5d: float = 0.0
    vol_10d: float = 0.0
    vol_20d: float = 0.0
    vol_60d: float = 0.0
    
    vol_5d_annualized: float = 0.0
    vol_10d_annualized: float = 0.0
    vol_20d_annualized: float = 0.0
    vol_60d_annualized: float = 0.0
    
    historical_vol_mean: float = 0.0
    historical_vol_std: float = 0.0
    current_vol: float = 0.0
    
    alert_type: VolatilityAlertType = VolatilityAlertType.NO_ALERT
    upper_band: float = 0.0
    lower_band: float = 0.0
    
    volatility_return_correlation: float = 0.0
    correlation_significance: str = ""
    
    vol_trend: str = ""
    vol_ratio_20_60: float = 0.0
    vol_ratio_5_20: float = 0.0


@dataclass
class PortfolioVolatilityResult:
    total_symbols: int = 0
    valid_symbols: int = 0
    portfolio_volatility: float = 0.0
    avg_volatility: float = 0.0
    highest_vol_symbol: str = ""
    highest_volatility: float = 0.0
    lowest_vol_symbol: str = ""
    lowest_volatility: float = 0.0
    alert_count: int = 0
    high_vol_count: int = 0
    low_vol_count: int = 0
    individual_metrics: List[VolatilityMetrics] = None


class VolatilityAnalyzer:
    TRADING_DAYS_PER_YEAR = 252
    
    def __init__(self):
        pass
    
    def get_price_data(
        self,
        symbol: str,
        period: str = '1y',
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        try:
            ticker = yf.Ticker(symbol.upper())
            data = ticker.history(period=period, interval=interval)
            
            if data is None or data.empty:
                return None
            
            data = data.dropna()
            return data
            
        except Exception as e:
            print(f"获取股票 {symbol} 历史数据失败: {e}")
            return None
    
    def calculate_log_returns(self, prices: pd.Series) -> pd.Series:
        return np.log(prices / prices.shift(1)).dropna()
    
    def calculate_volatility(
        self,
        returns: pd.Series,
        window: int,
        annualize: bool = True
    ) -> pd.Series:
        if len(returns) < window:
            return pd.Series([np.nan] * len(returns), index=returns.index)
        
        rolling_std = returns.rolling(window=window).std()
        
        if annualize:
            rolling_std = rolling_std * np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        return rolling_std
    
    def calculate_all_volatilities(
        self,
        prices: pd.Series,
        windows: List[int] = [5, 10, 20, 60]
    ) -> Dict[int, pd.Series]:
        returns = self.calculate_log_returns(prices)
        
        volatilities = {}
        for window in windows:
            volatilities[window] = self.calculate_volatility(returns, window, annualize=True)
        
        return volatilities
    
    def detect_volatility_alert(
        self,
        volatility_series: pd.Series,
        lookback_days: int = 60,
        std_threshold: float = 2.0
    ) -> Dict[str, Any]:
        if len(volatility_series) < lookback_days:
            return {
                'alert_type': VolatilityAlertType.NO_ALERT,
                'current_vol': np.nan,
                'mean': np.nan,
                'std': np.nan,
                'upper_band': np.nan,
                'lower_band': np.nan
            }
        
        historical_data = volatility_series.dropna()
        if len(historical_data) < lookback_days:
            lookback_days = len(historical_data)
        
        historical_vols = historical_data.iloc[-lookback_days:-1]
        current_vol = historical_data.iloc[-1] if len(historical_data) > 0 else np.nan
        
        if len(historical_vols) == 0 or pd.isna(current_vol):
            return {
                'alert_type': VolatilityAlertType.NO_ALERT,
                'current_vol': current_vol,
                'mean': np.nan,
                'std': np.nan,
                'upper_band': np.nan,
                'lower_band': np.nan
            }
        
        mean_vol = historical_vols.mean()
        std_vol = historical_vols.std()
        
        upper_band = mean_vol + std_threshold * std_vol
        lower_band = mean_vol - std_threshold * std_vol
        
        if current_vol > upper_band:
            alert_type = VolatilityAlertType.BREAKOUT_HIGH
        elif current_vol < lower_band:
            alert_type = VolatilityAlertType.BREAKOUT_LOW
        else:
            alert_type = VolatilityAlertType.NO_ALERT
        
        return {
            'alert_type': alert_type,
            'current_vol': current_vol,
            'mean': mean_vol,
            'std': std_vol,
            'upper_band': upper_band,
            'lower_band': lower_band
        }
    
    def calculate_volatility_return_correlation(
        self,
        prices: pd.Series,
        volatility_window: int = 20,
        min_data_points: int = 30
    ) -> Dict[str, Any]:
        returns = self.calculate_log_returns(prices)
        
        if len(returns) < min_data_points:
            return {
                'correlation': np.nan,
                'significance': '数据不足',
                'observations': len(returns)
            }
        
        volatility = self.calculate_volatility(returns, volatility_window, annualize=False)
        
        volatility_changes = volatility.pct_change().dropna()
        forward_returns = returns.shift(-1).dropna()
        
        aligned_vol_changes = volatility_changes.reindex(forward_returns.index)
        aligned_returns = forward_returns.reindex(aligned_vol_changes.index)
        
        valid_mask = ~(aligned_vol_changes.isna() | aligned_returns.isna())
        aligned_vol_changes = aligned_vol_changes[valid_mask]
        aligned_returns = aligned_returns[valid_mask]
        
        if len(aligned_vol_changes) < 10:
            return {
                'correlation': np.nan,
                'significance': '有效数据点不足',
                'observations': len(aligned_vol_changes)
            }
        
        correlation = aligned_vol_changes.corr(aligned_returns)
        
        if pd.isna(correlation):
            return {
                'correlation': np.nan,
                'significance': '无法计算相关性',
                'observations': len(aligned_vol_changes)
            }
        
        n = len(aligned_vol_changes)
        if n > 2:
            t_stat = correlation * np.sqrt((n - 2) / (1 - correlation**2)) if abs(correlation) < 1 else float('inf')
        else:
            t_stat = 0
        
        if abs(correlation) > 0.5:
            significance = '强相关'
        elif abs(correlation) > 0.3:
            significance = '中等相关'
        elif abs(correlation) > 0.1:
            significance = '弱相关'
        else:
            significance = '几乎无相关'
        
        if correlation > 0:
            significance += ' (波动率上升时收益倾向上涨)'
        else:
            significance += ' (波动率上升时收益倾向下跌)'
        
        return {
            'correlation': correlation,
            'significance': significance,
            'observations': n,
            't_statistic': t_stat
        }
    
    def analyze_stock(
        self,
        symbol: str,
        period: str = '1y'
    ) -> Optional[VolatilityMetrics]:
        prices = self.get_price_data(symbol, period=period)
        
        if prices is None or prices.empty:
            return None
        
        metrics = VolatilityMetrics()
        metrics.symbol = symbol.upper()
        metrics.latest_price = prices['Close'].iloc[-1]
        metrics.latest_date = prices.index[-1]
        
        windows = [5, 10, 20, 60]
        volatilities = self.calculate_all_volatilities(prices['Close'], windows)
        
        if 5 in volatilities and len(volatilities[5].dropna()) > 0:
            metrics.vol_5d_annualized = volatilities[5].dropna().iloc[-1]
            metrics.vol_5d = metrics.vol_5d_annualized / np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        if 10 in volatilities and len(volatilities[10].dropna()) > 0:
            metrics.vol_10d_annualized = volatilities[10].dropna().iloc[-1]
            metrics.vol_10d = metrics.vol_10d_annualized / np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        if 20 in volatilities and len(volatilities[20].dropna()) > 0:
            metrics.vol_20d_annualized = volatilities[20].dropna().iloc[-1]
            metrics.vol_20d = metrics.vol_20d_annualized / np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        if 60 in volatilities and len(volatilities[60].dropna()) > 0:
            metrics.vol_60d_annualized = volatilities[60].dropna().iloc[-1]
            metrics.vol_60d = metrics.vol_60d_annualized / np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        if metrics.vol_20d_annualized > 0 and metrics.vol_60d_annualized > 0:
            metrics.vol_ratio_20_60 = metrics.vol_20d_annualized / metrics.vol_60d_annualized
        
        if metrics.vol_5d_annualized > 0 and metrics.vol_20d_annualized > 0:
            metrics.vol_ratio_5_20 = metrics.vol_5d_annualized / metrics.vol_20d_annualized
        
        if metrics.vol_ratio_20_60 > 1.2:
            metrics.vol_trend = "波动率上升 (短期 > 长期)"
        elif metrics.vol_ratio_20_60 < 0.8:
            metrics.vol_trend = "波动率下降 (短期 < 长期)"
        else:
            metrics.vol_trend = "波动率稳定"
        
        if 20 in volatilities:
            alert_info = self.detect_volatility_alert(volatilities[20])
            metrics.alert_type = alert_info['alert_type']
            metrics.current_vol = alert_info['current_vol']
            metrics.historical_vol_mean = alert_info['mean']
            metrics.historical_vol_std = alert_info['std']
            metrics.upper_band = alert_info['upper_band']
            metrics.lower_band = alert_info['lower_band']
        
        corr_info = self.calculate_volatility_return_correlation(prices['Close'])
        metrics.volatility_return_correlation = corr_info['correlation']
        metrics.correlation_significance = corr_info['significance']
        
        return metrics
    
    def analyze_portfolio(
        self,
        symbols: List[str],
        period: str = '1y'
    ) -> PortfolioVolatilityResult:
        result = PortfolioVolatilityResult()
        result.total_symbols = len(symbols)
        result.individual_metrics = []
        
        all_vols = []
        highest_vol = -1
        lowest_vol = float('inf')
        alert_count = 0
        high_vol_count = 0
        low_vol_count = 0
        
        for symbol in symbols:
            try:
                metrics = self.analyze_stock(symbol, period)
                if metrics:
                    result.individual_metrics.append(metrics)
                    result.valid_symbols += 1
                    
                    if not pd.isna(metrics.vol_20d_annualized) and metrics.vol_20d_annualized > 0:
                        all_vols.append(metrics.vol_20d_annualized)
                        
                        if metrics.vol_20d_annualized > highest_vol:
                            highest_vol = metrics.vol_20d_annualized
                            result.highest_vol_symbol = symbol
                            result.highest_volatility = metrics.vol_20d_annualized
                        
                        if metrics.vol_20d_annualized < lowest_vol:
                            lowest_vol = metrics.vol_20d_annualized
                            result.lowest_vol_symbol = symbol
                            result.lowest_volatility = metrics.vol_20d_annualized
                    
                    if metrics.alert_type != VolatilityAlertType.NO_ALERT:
                        alert_count += 1
                    
                    if metrics.alert_type == VolatilityAlertType.BREAKOUT_HIGH:
                        high_vol_count += 1
                    elif metrics.alert_type == VolatilityAlertType.BREAKOUT_LOW:
                        low_vol_count += 1
                        
            except Exception as e:
                print(f"分析股票 {symbol} 波动率失败: {e}")
                continue
        
        if all_vols:
            result.avg_volatility = np.mean(all_vols)
            result.portfolio_volatility = np.std(all_vols)
        
        result.alert_count = alert_count
        result.high_vol_count = high_vol_count
        result.low_vol_count = low_vol_count
        
        return result
    
    def get_volatility_chart_data(
        self,
        symbol: str,
        period: str = '1y',
        window: int = 20
    ) -> Optional[Dict[str, Any]]:
        prices = self.get_price_data(symbol, period=period)
        
        if prices is None or prices.empty:
            return None
        
        returns = self.calculate_log_returns(prices['Close'])
        volatility = self.calculate_volatility(returns, window, annualize=True)
        
        volatility = volatility.dropna()
        if len(volatility) == 0:
            return None
        
        mean_vol = volatility.mean()
        std_vol = volatility.std()
        upper_band = mean_vol + 2 * std_vol
        lower_band = mean_vol - 2 * std_vol
        
        return {
            'symbol': symbol.upper(),
            'dates': volatility.index.tolist(),
            'volatility': volatility.tolist(),
            'mean': mean_vol,
            'std': std_vol,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'latest_vol': volatility.iloc[-1],
            'window': window
        }
