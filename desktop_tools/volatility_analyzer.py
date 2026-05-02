import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf


class VolatilityAlert:
    def __init__(self):
        self.symbol = ''
        self.type = ''
        self.message = ''
        self.current_vol = None
        self.mean_vol = None
        self.std_vol = None
        self.z_score = None
        self.threshold = None
        self.timestamp = None


class VolatilityAnalyzer:
    def __init__(self):
        self._annualization_factor = {
            '1d': 252,
            '1h': 252 * 6.5,
            '1m': 252 * 6.5 * 60
        }

    def get_price_data(
        self,
        symbol: str,
        period: str = '2y',
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

    def calculate_log_returns(self, data: pd.DataFrame) -> pd.Series:
        if data is None or data.empty:
            return pd.Series()

        returns = np.log(data['Close'] / data['Close'].shift(1))
        return returns.dropna()

    def calculate_returns(self, data: pd.DataFrame) -> pd.Series:
        if data is None or data.empty:
            return pd.Series()

        returns = data['Close'].pct_change()
        return returns.dropna()

    def calculate_historical_volatility(
        self,
        data: pd.DataFrame,
        window: int = 20,
        annualize: bool = True,
        interval: str = '1d'
    ) -> pd.Series:
        if data is None or data.empty:
            return pd.Series()

        returns = self.calculate_log_returns(data)

        if len(returns) < window:
            return pd.Series([np.nan] * len(data), index=data.index)

        rolling_std = returns.rolling(window=window).std()

        if annualize:
            ann_factor = self._annualization_factor.get(interval, 252)
            rolling_std = rolling_std * np.sqrt(ann_factor)

        result = pd.Series([np.nan] * len(data), index=data.index)
        result.loc[rolling_std.index] = rolling_std
        return result

    def calculate_all_volatility_windows(
        self,
        data: pd.DataFrame,
        windows: List[int] = None,
        annualize: bool = True,
        interval: str = '1d'
    ) -> Dict[int, pd.Series]:
        if windows is None:
            windows = [5, 10, 20, 60]

        vol_dict = {}
        for window in windows:
            vol_dict[window] = self.calculate_historical_volatility(
                data, window, annualize, interval
            )
        return vol_dict

    def calculate_volatility_measures(
        self,
        data: pd.DataFrame,
        lookback_period: int = 252
    ) -> Dict[str, Any]:
        if data is None or data.empty:
            return {}

        returns = self.calculate_log_returns(data)

        if len(returns) < 2:
            return {}

        recent_returns = returns.tail(lookback_period) if len(returns) > lookback_period else returns

        ann_factor = self._annualization_factor.get('1d', 252)
        annualized_vol = recent_returns.std() * np.sqrt(ann_factor)

        mean_vol = recent_returns.rolling(window=20).std().mean() * np.sqrt(ann_factor)
        std_of_vol = recent_returns.rolling(window=20).std().std() * np.sqrt(ann_factor)

        high_idx = recent_returns.rolling(window=20).std().idxmax()
        low_idx = recent_returns.rolling(window=20).std().idxmin()

        high_vol = recent_returns.rolling(window=20).std().loc[high_idx] * np.sqrt(ann_factor) if not pd.isna(high_idx) else None
        low_vol = recent_returns.rolling(window=20).std().loc[low_idx] * np.sqrt(ann_factor) if not pd.isna(low_idx) else None

        current_vol_series = recent_returns.tail(20).std() * np.sqrt(ann_factor)
        current_vol = current_vol_series if not pd.isna(current_vol_series) else None

        current_log_return = returns.iloc[-1] if len(returns) > 0 else None
        current_simple_return = data['Close'].pct_change().iloc[-1] if len(data) > 1 else None

        return {
            'current_volatility': current_vol,
            'mean_volatility': mean_vol,
            'std_of_volatility': std_of_vol,
            'high_volatility': high_vol,
            'low_volatility': low_vol,
            'current_log_return': current_log_return,
            'current_simple_return': current_simple_return,
            'annualized_volatility': annualized_vol,
            'lookback_days': len(recent_returns)
        }

    def calculate_volatility_zscore(
        self,
        data: pd.DataFrame,
        vol_window: int = 20,
        lookback_period: int = 252
    ) -> Tuple[Optional[float], pd.Series]:
        if data is None or data.empty:
            return None, pd.Series()

        returns = self.calculate_log_returns(data)

        if len(returns) < vol_window:
            return None, pd.Series()

        rolling_vol = returns.rolling(window=vol_window).std()

        recent_vol = rolling_vol.tail(lookback_period) if len(rolling_vol) > lookback_period else rolling_vol
        recent_vol = recent_vol.dropna()

        if len(recent_vol) < 2:
            return None, pd.Series()

        mean_vol = recent_vol.mean()
        std_vol = recent_vol.std()

        if std_vol == 0:
            return 0, pd.Series()

        current_vol = rolling_vol.iloc[-1]
        z_score = (current_vol - mean_vol) / std_vol

        z_scores = (rolling_vol - mean_vol) / std_vol

        return z_score, z_scores

    def check_volatility_alert(
        self,
        symbol: str,
        data: pd.DataFrame = None,
        z_threshold: float = 2.0,
        vol_window: int = 20,
        lookback_period: int = 252
    ) -> Optional[VolatilityAlert]:
        if data is None or data.empty:
            data = self.get_price_data(symbol, period='2y')

        if data is None or data.empty:
            return None

        z_score, _ = self.calculate_volatility_zscore(
            data, vol_window, lookback_period
        )

        if z_score is None:
            return None

        vol_measures = self.calculate_volatility_measures(data, lookback_period)

        alert = VolatilityAlert()
        alert.symbol = symbol.upper()
        alert.z_score = z_score
        alert.current_vol = vol_measures.get('current_volatility')
        alert.mean_vol = vol_measures.get('mean_volatility')
        alert.std_vol = vol_measures.get('std_of_volatility')
        alert.threshold = z_threshold
        alert.timestamp = datetime.now()

        if z_score > z_threshold:
            alert.type = 'HIGH_VOLATILITY'
            alert.message = (
                f"波动率异常升高！当前波动率: {alert.current_vol:.2%}, "
                f"Z分数: {z_score:.2f} (> {z_threshold}σ)"
            )
        elif z_score < -z_threshold:
            alert.type = 'LOW_VOLATILITY'
            alert.message = (
                f"波动率异常降低！当前波动率: {alert.current_vol:.2%}, "
                f"Z分数: {z_score:.2f} (< -{z_threshold}σ)"
            )
        else:
            return None

        return alert

    def calculate_volatility_return_correlation(
        self,
        data: pd.DataFrame,
        vol_window: int = 20,
        lookback_period: int = 252
    ) -> Dict[str, Any]:
        if data is None or data.empty:
            return {}

        returns = self.calculate_log_returns(data)
        simple_returns = self.calculate_returns(data)

        if len(returns) < vol_window + 1:
            return {}

        rolling_vol = returns.rolling(window=vol_window).std()

        vol_shifted = rolling_vol.shift(1)
        aligned_returns = returns.loc[vol_shifted.dropna().index]
        aligned_vol = vol_shifted.dropna()

        if len(aligned_returns) < 10 or len(aligned_vol) < 10:
            return {}

        recent_returns = aligned_returns.tail(lookback_period) if len(aligned_returns) > lookback_period else aligned_returns
        recent_vol = aligned_vol.tail(lookback_period) if len(aligned_vol) > lookback_period else aligned_vol

        corr_series = pd.concat([recent_vol, recent_returns], axis=1).dropna()
        if len(corr_series) < 10:
            return {}

        correlation = corr_series.iloc[:, 0].corr(corr_series.iloc[:, 1])

        positive_returns = recent_returns[recent_returns > 0]
        negative_returns = recent_returns[recent_returns < 0]

        pos_corr = None
        neg_corr = None

        if len(positive_returns) >= 10:
            pos_vol = recent_vol.loc[positive_returns.index]
            pos_data = pd.concat([pos_vol, positive_returns], axis=1).dropna()
            if len(pos_data) >= 10:
                pos_corr = pos_data.iloc[:, 0].corr(pos_data.iloc[:, 1])

        if len(negative_returns) >= 10:
            neg_vol = recent_vol.loc[negative_returns.index]
            neg_data = pd.concat([neg_vol, negative_returns], axis=1).dropna()
            if len(neg_data) >= 10:
                neg_corr = neg_data.iloc[:, 0].corr(neg_data.iloc[:, 1])

        abs_returns = recent_returns.abs()
        abs_corr_series = pd.concat([recent_vol, abs_returns], axis=1).dropna()
        abs_correlation = abs_corr_series.iloc[:, 0].corr(abs_corr_series.iloc[:, 1]) if len(abs_corr_series) >= 10 else None

        return {
            'overall_correlation': correlation,
            'positive_return_correlation': pos_corr,
            'negative_return_correlation': neg_corr,
            'absolute_return_correlation': abs_correlation,
            'sample_size': len(corr_series),
            'volatility_window': vol_window,
            'lookback_period': lookback_period
        }

    def calculate_portfolio_volatility(
        self,
        symbols: List[str],
        weights: List[float] = None,
        period: str = '1y',
        lookback_days: int = 252
    ) -> Dict[str, Any]:
        if not symbols:
            return {}

        n = len(symbols)
        if weights is None:
            weights = [1.0 / n] * n
        elif len(weights) != n:
            return {}

        weights = np.array(weights)
        weights = weights / weights.sum()

        all_data = {}
        for symbol in symbols:
            data = self.get_price_data(symbol, period=period)
            if data is None or data.empty:
                print(f"无法获取 {symbol} 的数据")
                continue
            all_data[symbol] = data['Close']

        if not all_data:
            return {}

        prices_df = pd.DataFrame(all_data)
        prices_df = prices_df.dropna()

        if prices_df.empty or len(prices_df.columns) < 1:
            return {}

        returns_df = np.log(prices_df / prices_df.shift(1)).dropna()

        if returns_df.empty:
            return {}

        recent_returns = returns_df.tail(lookback_days) if len(returns_df) > lookback_days else returns_df

        ann_factor = self._annualization_factor.get('1d', 252)
        cov_matrix = recent_returns.cov() * ann_factor

        portfolio_variance = weights.T @ cov_matrix @ weights
        portfolio_volatility = np.sqrt(portfolio_variance)

        individual_vols = {}
        for col in recent_returns.columns:
            ind_vol = recent_returns[col].std() * np.sqrt(ann_factor)
            individual_vols[col] = ind_vol

        weighted_vol = sum(w * individual_vols[s] for w, s in zip(weights, individual_vols.keys()))

        diversification_ratio = portfolio_volatility / weighted_vol if weighted_vol > 0 else None

        contributions = {}
        for i, symbol in enumerate(individual_vols.keys()):
            if i < len(weights):
                marginal_contribution = weights[i] * (cov_matrix.iloc[i] @ weights) / portfolio_variance
                contributions[symbol] = {
                    'weight': weights[i],
                    'individual_vol': individual_vols[symbol],
                    'contribution_pct': marginal_contribution * 100,
                    'weighted_vol': weights[i] * individual_vols[symbol]
                }

        corr_matrix = recent_returns.corr()

        return {
            'portfolio_volatility': portfolio_volatility,
            'portfolio_variance': portfolio_variance,
            'weighted_average_vol': weighted_vol,
            'diversification_ratio': diversification_ratio,
            'diversification_benefit': (weighted_vol - portfolio_volatility) if weighted_vol else None,
            'individual_volatilities': individual_vols,
            'contributions': contributions,
            'correlation_matrix': corr_matrix.to_dict(),
            'covariance_matrix': cov_matrix.to_dict(),
            'weights': dict(zip(individual_vols.keys(), weights[:len(individual_vols)])),
            'lookback_days': len(recent_returns),
            'symbols': list(individual_vols.keys())
        }

    def analyze_single_stock(
        self,
        symbol: str,
        period: str = '2y',
        vol_windows: List[int] = None,
        z_threshold: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        if vol_windows is None:
            vol_windows = [5, 10, 20, 60]

        data = self.get_price_data(symbol, period=period)

        if data is None or data.empty:
            return None

        vol_dict = self.calculate_all_volatility_windows(data, vol_windows)

        vol_measures = self.calculate_volatility_measures(data)

        z_score, z_scores = self.calculate_volatility_zscore(data)

        alert = self.check_volatility_alert(symbol, data, z_threshold=z_threshold)

        corr_analysis = self.calculate_volatility_return_correlation(data)

        latest_idx = data.index[-1]
        latest_price = data['Close'].iloc[-1]

        latest_vols = {}
        for window in vol_windows:
            if window in vol_dict:
                vol_series = vol_dict[window]
                if not vol_series.empty and not pd.isna(vol_series.iloc[-1]):
                    latest_vols[window] = vol_series.iloc[-1]
                else:
                    latest_vols[window] = None

        return {
            'symbol': symbol.upper(),
            'latest_price': latest_price,
            'latest_date': latest_idx,
            'volatility_windows': latest_vols,
            'volatility_measures': vol_measures,
            'z_score': z_score,
            'alert': {
                'type': alert.type if alert else None,
                'message': alert.message if alert else None,
                'threshold': z_threshold
            } if alert else None,
            'return_correlation': corr_analysis,
            'price_data': {
                'dates': data.index.tolist(),
                'close': data['Close'].tolist(),
                'volume': data['Volume'].tolist()
            },
            'volatility_series': {
                str(w): v.tolist() if isinstance(v, pd.Series) else v
                for w, v in vol_dict.items()
            },
            'z_scores_series': z_scores.tolist() if isinstance(z_scores, pd.Series) else []
        }

    def analyze_portfolio(
        self,
        symbols: List[str],
        weights: List[float] = None,
        period: str = '1y',
        z_threshold: float = 2.0
    ) -> Dict[str, Any]:
        portfolio_vol = self.calculate_portfolio_volatility(symbols, weights, period)

        individual_analyses = {}
        alerts = []

        for symbol in symbols:
            analysis = self.analyze_single_stock(symbol, period, z_threshold=z_threshold)
            if analysis:
                individual_analyses[symbol] = analysis
                if analysis.get('alert'):
                    alerts.append({
                        'symbol': symbol,
                        'alert': analysis['alert']
                    })

        avg_zscore = None
        valid_zscores = [
            a['z_score'] for a in individual_analyses.values()
            if a.get('z_score') is not None
        ]
        if valid_zscores:
            avg_zscore = np.mean(valid_zscores)

        risk_assessment = self._assess_portfolio_risk(portfolio_vol, avg_zscore, alerts)

        return {
            'portfolio_analysis': portfolio_vol,
            'individual_analyses': individual_analyses,
            'alerts': alerts,
            'average_zscore': avg_zscore,
            'risk_assessment': risk_assessment,
            'analysis_time': datetime.now().isoformat()
        }

    def _assess_portfolio_risk(
        self,
        portfolio_vol: Dict,
        avg_zscore: Optional[float],
        alerts: List[Dict]
    ) -> Dict[str, Any]:
        port_vol = portfolio_vol.get('portfolio_volatility')
        risk_level = 'MEDIUM'
        risk_score = 50
        warnings = []

        if port_vol is not None:
            if port_vol > 0.4:
                risk_level = 'HIGH'
                risk_score = 80
                warnings.append(f"组合波动率较高 ({port_vol:.2%})")
            elif port_vol > 0.25:
                risk_level = 'MEDIUM_HIGH'
                risk_score = 65
            elif port_vol < 0.10:
                risk_level = 'LOW'
                risk_score = 25
                warnings.append(f"组合波动率较低 ({port_vol:.2%})")

        div_ratio = portfolio_vol.get('diversification_ratio')
        if div_ratio is not None:
            if div_ratio < 0.7:
                risk_score -= 10
            elif div_ratio > 0.9:
                risk_score += 10
                warnings.append("分散化效果较弱")

        high_vol_alerts = sum(1 for a in alerts if a['alert'].get('type') == 'HIGH_VOLATILITY')
        low_vol_alerts = sum(1 for a in alerts if a['alert'].get('type') == 'LOW_VOLATILITY')

        if high_vol_alerts > 0:
            risk_score += high_vol_alerts * 5
            warnings.append(f"有 {high_vol_alerts} 只股票波动率异常升高")

        if avg_zscore is not None:
            if avg_zscore > 1.5:
                risk_level = 'HIGH' if risk_score > 70 else 'MEDIUM_HIGH'
                warnings.append(f"平均波动率Z分数偏高 ({avg_zscore:.2f})")
            elif avg_zscore < -1.5:
                warnings.append(f"平均波动率Z分数偏低 ({avg_zscore:.2f})，可能预示变盘")

        risk_score = max(0, min(100, risk_score))

        if risk_score >= 75:
            risk_level = 'HIGH'
        elif risk_score >= 55:
            risk_level = 'MEDIUM_HIGH'
        elif risk_score >= 35:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'warnings': warnings,
            'high_volatility_alerts': high_vol_alerts,
            'low_volatility_alerts': low_vol_alerts
        }
