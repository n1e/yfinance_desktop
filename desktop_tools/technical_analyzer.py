import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf


class TechnicalAnalyzer:
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

    def calculate_ma(
        self, 
        data: pd.DataFrame, 
        periods: List[int] = [5, 20, 50, 200]
    ) -> Dict[int, pd.Series]:
        ma_dict = {}
        for period in periods:
            if len(data) >= period:
                ma_dict[period] = data['Close'].rolling(window=period).mean()
            else:
                ma_dict[period] = pd.Series([np.nan] * len(data), index=data.index)
        return ma_dict

    def calculate_macd(
        self, 
        data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        if len(data) < slow_period + signal_period:
            return {
                'macd_line': pd.Series([np.nan] * len(data), index=data.index),
                'signal_line': pd.Series([np.nan] * len(data), index=data.index),
                'histogram': pd.Series([np.nan] * len(data), index=data.index)
            }

        ema_fast = data['Close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = data['Close'].ewm(span=slow_period, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        }

    def calculate_rsi(
        self, 
        data: pd.DataFrame,
        period: int = 14
    ) -> pd.Series:
        if len(data) < period + 1:
            return pd.Series([np.nan] * len(data), index=data.index)

        delta = data['Close'].diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_bollinger_bands(
        self, 
        data: pd.DataFrame,
        period: int = 20,
        num_std: float = 2.0
    ) -> Dict[str, pd.Series]:
        if len(data) < period:
            return {
                'middle_band': pd.Series([np.nan] * len(data), index=data.index),
                'upper_band': pd.Series([np.nan] * len(data), index=data.index),
                'lower_band': pd.Series([np.nan] * len(data), index=data.index),
                'bandwidth': pd.Series([np.nan] * len(data), index=data.index),
                'percent_b': pd.Series([np.nan] * len(data), index=data.index)
            }

        middle_band = data['Close'].rolling(window=period).mean()
        std = data['Close'].rolling(window=period).std()
        
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        bandwidth = (upper_band - lower_band) / middle_band * 100
        
        percent_b = (data['Close'] - lower_band) / (upper_band - lower_band) * 100
        percent_b = percent_b.fillna(50)

        return {
            'middle_band': middle_band,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'bandwidth': bandwidth,
            'percent_b': percent_b
        }

    def calculate_kdj(
        self, 
        data: pd.DataFrame,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Dict[str, pd.Series]:
        if len(data) < n:
            return {
                'k': pd.Series([np.nan] * len(data), index=data.index),
                'd': pd.Series([np.nan] * len(data), index=data.index),
                'j': pd.Series([np.nan] * len(data), index=data.index)
            }

        low_min = data['Low'].rolling(window=n).min()
        high_max = data['High'].rolling(window=n).max()
        
        rsv = (data['Close'] - low_min) / (high_max - low_min + 1e-10) * 100
        
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d

        return {
            'k': k,
            'd': d,
            'j': j
        }

    def calculate_volume_analysis(
        self, 
        data: pd.DataFrame,
        ma_periods: List[int] = [5, 20]
    ) -> Dict[str, pd.Series]:
        result = {}
        
        for period in ma_periods:
            result[f'volume_ma_{period}'] = data['Volume'].rolling(window=period).mean()
        
        result['volume_change'] = data['Volume'].pct_change() * 100
        
        price_change = data['Close'].pct_change()
        result['volume_price_trend'] = np.where(
            (price_change > 0) & (data['Volume'] > result['volume_ma_20']), 1,
            np.where(
                (price_change < 0) & (data['Volume'] > result['volume_ma_20']), -1,
                0
            )
        )

        return result

    def analyze_all_indicators(
        self, 
        symbol: str,
        period: str = '1y',
        interval: str = '1d'
    ) -> Optional[Dict[str, Any]]:
        data = self.get_price_data(symbol, period, interval)
        
        if data is None or data.empty:
            return None

        ma = self.calculate_ma(data)
        macd = self.calculate_macd(data)
        rsi = self.calculate_rsi(data)
        bollinger = self.calculate_bollinger_bands(data)
        kdj = self.calculate_kdj(data)
        volume = self.calculate_volume_analysis(data)

        latest_idx = data.index[-1]
        latest_price = data['Close'].iloc[-1]

        signals = self._generate_signals(
            data, ma, macd, rsi, bollinger, kdj, volume
        )

        return {
            'symbol': symbol.upper(),
            'data': data,
            'price_data': {
                'dates': data.index.tolist(),
                'open': data['Open'].tolist(),
                'high': data['High'].tolist(),
                'low': data['Low'].tolist(),
                'close': data['Close'].tolist(),
                'volume': data['Volume'].tolist()
            },
            'ma': {p: ma[p].tolist() for p in ma},
            'macd': {k: v.tolist() for k, v in macd.items()},
            'rsi': rsi.tolist(),
            'bollinger': {k: v.tolist() for k, v in bollinger.items()},
            'kdj': {k: v.tolist() for k, v in kdj.items()},
            'volume': {k: v.tolist() if isinstance(v, pd.Series) else list(v) for k, v in volume.items()},
            'latest': {
                'price': latest_price,
                'date': latest_idx,
                'rsi': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None,
                'macd': macd['macd_line'].iloc[-1] if not pd.isna(macd['macd_line'].iloc[-1]) else None,
                'macd_signal': macd['signal_line'].iloc[-1] if not pd.isna(macd['signal_line'].iloc[-1]) else None,
                'macd_histogram': macd['histogram'].iloc[-1] if not pd.isna(macd['histogram'].iloc[-1]) else None,
                'k': kdj['k'].iloc[-1] if not pd.isna(kdj['k'].iloc[-1]) else None,
                'd': kdj['d'].iloc[-1] if not pd.isna(kdj['d'].iloc[-1]) else None,
                'j': kdj['j'].iloc[-1] if not pd.isna(kdj['j'].iloc[-1]) else None,
                'bollinger_upper': bollinger['upper_band'].iloc[-1] if not pd.isna(bollinger['upper_band'].iloc[-1]) else None,
                'bollinger_middle': bollinger['middle_band'].iloc[-1] if not pd.isna(bollinger['middle_band'].iloc[-1]) else None,
                'bollinger_lower': bollinger['lower_band'].iloc[-1] if not pd.isna(bollinger['lower_band'].iloc[-1]) else None,
                'percent_b': bollinger['percent_b'].iloc[-1] if not pd.isna(bollinger['percent_b'].iloc[-1]) else None
            },
            'signals': signals
        }

    def _generate_signals(
        self,
        data: pd.DataFrame,
        ma: Dict[int, pd.Series],
        macd: Dict[str, pd.Series],
        rsi: pd.Series,
        bollinger: Dict[str, pd.Series],
        kdj: Dict[str, pd.Series],
        volume: Dict[str, pd.Series]
    ) -> Dict[str, Any]:
        buy_signals = []
        sell_signals = []
        neutral_signals = []

        if len(data) >= 2:
            last_close = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2]
            
            ma_5 = ma.get(5, pd.Series())
            ma_20 = ma.get(20, pd.Series())
            ma_50 = ma.get(50, pd.Series())
            ma_200 = ma.get(200, pd.Series())

            if len(ma_5) >= 2 and len(ma_20) >= 2:
                if not pd.isna(ma_5.iloc[-1]) and not pd.isna(ma_20.iloc[-1]):
                    if ma_5.iloc[-1] > ma_20.iloc[-1] and ma_5.iloc[-2] <= ma_20.iloc[-2]:
                        buy_signals.append("MA5上穿MA20 (金叉)")
                    elif ma_5.iloc[-1] < ma_20.iloc[-1] and ma_5.iloc[-2] >= ma_20.iloc[-2]:
                        sell_signals.append("MA5下穿MA20 (死叉)")

            if len(ma_50) >= 2 and len(ma_200) >= 2:
                if not pd.isna(ma_50.iloc[-1]) and not pd.isna(ma_200.iloc[-1]):
                    if ma_50.iloc[-1] > ma_200.iloc[-1] and ma_50.iloc[-2] <= ma_200.iloc[-2]:
                        buy_signals.append("MA50上穿MA200 (黄金交叉)")
                    elif ma_50.iloc[-1] < ma_200.iloc[-1] and ma_50.iloc[-2] >= ma_200.iloc[-2]:
                        sell_signals.append("MA50下穿MA200 (死亡交叉)")

            if not pd.isna(ma_200.iloc[-1]) if len(ma_200) > 0 else True:
                if len(ma_200) > 0 and not pd.isna(ma_200.iloc[-1]):
                    if last_close > ma_200.iloc[-1]:
                        neutral_signals.append("价格位于MA200上方 (多头趋势)")
                    else:
                        neutral_signals.append("价格位于MA200下方 (空头趋势)")

        macd_line = macd.get('macd_line', pd.Series())
        signal_line = macd.get('signal_line', pd.Series())
        histogram = macd.get('histogram', pd.Series())

        if len(macd_line) >= 2 and len(signal_line) >= 2:
            if not pd.isna(macd_line.iloc[-1]) and not pd.isna(signal_line.iloc[-1]):
                if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
                    buy_signals.append("MACD上穿信号线 (金叉)")
                elif macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
                    sell_signals.append("MACD下穿信号线 (死叉)")

        if len(histogram) >= 2:
            if not pd.isna(histogram.iloc[-1]) and not pd.isna(histogram.iloc[-2]):
                if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
                    buy_signals.append("MACD柱状图由负转正")
                elif histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0:
                    sell_signals.append("MACD柱状图由正转负")

        if len(rsi) >= 1:
            latest_rsi = rsi.iloc[-1]
            if not pd.isna(latest_rsi):
                if latest_rsi < 30:
                    buy_signals.append(f"RSI超卖 ({latest_rsi:.1f})")
                elif latest_rsi > 70:
                    sell_signals.append(f"RSI超买 ({latest_rsi:.1f})")
                elif latest_rsi < 50:
                    neutral_signals.append(f"RSI偏弱 ({latest_rsi:.1f})")
                else:
                    neutral_signals.append(f"RSI偏强 ({latest_rsi:.1f})")

            if len(rsi) >= 2:
                prev_rsi = rsi.iloc[-2]
                if not pd.isna(latest_rsi) and not pd.isna(prev_rsi):
                    if prev_rsi < 30 and latest_rsi >= 30:
                        buy_signals.append("RSI从超卖区回升")
                    elif prev_rsi > 70 and latest_rsi <= 70:
                        sell_signals.append("RSI从超买区回落")

        percent_b = bollinger.get('percent_b', pd.Series())
        upper_band = bollinger.get('upper_band', pd.Series())
        lower_band = bollinger.get('lower_band', pd.Series())

        if len(data) >= 1 and len(upper_band) >= 1 and len(lower_band) >= 1:
            last_close = data['Close'].iloc[-1]
            last_upper = upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else None
            last_lower = lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else None

            if last_upper and last_lower:
                if last_close <= last_lower:
                    buy_signals.append("价格触及布林带下轨")
                elif last_close >= last_upper:
                    sell_signals.append("价格触及布林带上轨")

            if len(percent_b) >= 1:
                last_pb = percent_b.iloc[-1]
                if not pd.isna(last_pb):
                    if last_pb < 20:
                        buy_signals.append(f"布林带%b超卖 ({last_pb:.1f})")
                    elif last_pb > 80:
                        sell_signals.append(f"布林带%b超买 ({last_pb:.1f})")

        k = kdj.get('k', pd.Series())
        d = kdj.get('d', pd.Series())
        j = kdj.get('j', pd.Series())

        if len(k) >= 2 and len(d) >= 2:
            if not pd.isna(k.iloc[-1]) and not pd.isna(d.iloc[-1]):
                if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]:
                    buy_signals.append("KDJ K线上穿D线 (金叉)")
                elif k.iloc[-1] < d.iloc[-1] and k.iloc[-2] >= d.iloc[-2]:
                    sell_signals.append("KDJ K线下穿D线 (死叉)")

        if len(k) >= 1:
            latest_k = k.iloc[-1]
            latest_d = d.iloc[-1] if len(d) >= 1 else None
            if not pd.isna(latest_k):
                if latest_k < 20:
                    buy_signals.append(f"KDJ K值超卖 ({latest_k:.1f})")
                elif latest_k > 80:
                    sell_signals.append(f"KDJ K值超买 ({latest_k:.1f})")

                if latest_d is not None and not pd.isna(latest_d):
                    if latest_d < 20:
                        neutral_signals.append(f"KDJ D值超卖区 ({latest_d:.1f})")
                    elif latest_d > 80:
                        neutral_signals.append(f"KDJ D值超买区 ({latest_d:.1f})")

        volume_ma_5 = volume.get('volume_ma_5', pd.Series())
        volume_ma_20 = volume.get('volume_ma_20', pd.Series())
        volume_price_trend = volume.get('volume_price_trend', [])

        if len(data) >= 1 and len(volume_ma_20) >= 1:
            last_volume = data['Volume'].iloc[-1]
            last_vol_ma20 = volume_ma_20.iloc[-1] if not pd.isna(volume_ma_20.iloc[-1]) else None
            
            if last_vol_ma20 and last_vol_ma20 > 0:
                volume_ratio = last_volume / last_vol_ma20
                
                if volume_ratio > 2:
                    if len(volume_price_trend) >= 1:
                        if volume_price_trend[-1] == 1:
                            buy_signals.append(f"放量上涨 (量比: {volume_ratio:.1f})")
                        elif volume_price_trend[-1] == -1:
                            sell_signals.append(f"放量下跌 (量比: {volume_ratio:.1f})")
                        else:
                            neutral_signals.append(f"放量 (量比: {volume_ratio:.1f})")
                elif volume_ratio < 0.5:
                    neutral_signals.append(f"缩量 (量比: {volume_ratio:.1f})")

        buy_score = len(buy_signals)
        sell_score = len(sell_signals)
        total_score = buy_score - sell_score

        if total_score >= 3:
            overall_signal = "强烈买入"
            signal_color = "green"
        elif total_score >= 1:
            overall_signal = "买入"
            signal_color = "green"
        elif total_score <= -3:
            overall_signal = "强烈卖出"
            signal_color = "red"
        elif total_score <= -1:
            overall_signal = "卖出"
            signal_color = "red"
        else:
            overall_signal = "观望"
            signal_color = "yellow"

        return {
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'neutral_signals': neutral_signals,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'total_score': total_score,
            'overall_signal': overall_signal,
            'signal_color': signal_color
        }
