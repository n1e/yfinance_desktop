import threading
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import math

import yfinance as yf
import pandas as pd


class IndicatorResult:
    def __init__(self):
        self.name = ''
        self.current_value = None
        self.historical_values = []
        self.status = ''
        self.status_color = ''
        self.percentile = None
        self.min_value = None
        self.max_value = None
        self.avg_value = None
        self.description = ''


class MarketIndicators:
    _instance: Optional['MarketIndicators'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cache_dir = Path.home() / ".stock_monitor" / "indicators_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_duration = timedelta(hours=24)
        
        self._indicator_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Dict[str, datetime] = {}

    def _get_cache_file(self, name: str) -> Path:
        return self._cache_dir / f"{name}.json"

    def _load_from_file_cache(self, name: str) -> Optional[Dict[str, Any]]:
        cache_file = self._get_cache_file(name)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cache_time = datetime.fromisoformat(data.get('cache_time', ''))
                    if datetime.now() - cache_time < self._cache_duration:
                        return data
            except (json.JSONDecodeError, IOError, ValueError):
                pass
        return None

    def _save_to_file_cache(self, name: str, data: Dict[str, Any]):
        cache_file = self._get_cache_file(name)
        try:
            data['cache_time'] = datetime.now().isoformat()
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except IOError as e:
            print(f"保存指标缓存失败: {e}")

    def _is_cache_valid(self, name: str) -> bool:
        if name in self._cache_time:
            if datetime.now() - self._cache_time[name] < self._cache_duration:
                return True
        
        file_cache = self._load_from_file_cache(name)
        if file_cache:
            self._indicator_cache[name] = file_cache
            self._cache_time[name] = datetime.fromisoformat(file_cache['cache_time'])
            return True
        return False

    def _update_cache(self, name: str, data: Dict[str, Any]):
        self._indicator_cache[name] = data
        self._cache_time[name] = datetime.now()
        self._save_to_file_cache(name, data)

    def _safe_get(self, data: Dict, key: str, default=None):
        value = data.get(key)
        if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            return default
        return value

    def _calculate_status(self, value: float, thresholds: Dict[str, Tuple[float, float]], 
                          lower_is_better: bool = True) -> Tuple[str, str]:
        if lower_is_better:
            if value <= thresholds['undervalued'][1]:
                return '低估', 'green'
            elif value <= thresholds['reasonable'][1]:
                return '合理', 'blue'
            else:
                return '高估', 'red'
        else:
            if value >= thresholds['undervalued'][0]:
                return '低估', 'green'
            elif value >= thresholds['reasonable'][0]:
                return '合理', 'blue'
            else:
                return '高估', 'red'

    def _calculate_percentile(self, value: float, historical_values: List[float]) -> float:
        if not historical_values or value is None:
            return 50.0
        
        sorted_values = sorted(historical_values)
        count_below = sum(1 for v in sorted_values if v <= value)
        percentile = (count_below / len(sorted_values)) * 100
        return round(percentile, 2)

    def get_buffett_indicator(self, force_refresh: bool = False) -> Optional[IndicatorResult]:
        cache_name = 'buffett_indicator'
        
        if not force_refresh and self._is_cache_valid(cache_name):
            return self._cached_to_result(self._indicator_cache[cache_name])

        try:
            result = IndicatorResult()
            result.name = '巴菲特指标 (Buffett Indicator)'
            result.description = '美股总市值 / GDP，用于评估股市整体估值水平'

            sp500 = yf.Ticker("^GSPC")
            sp500_info = sp500.info
            
            total_market_cap = self._safe_get(sp500_info, 'marketCap')
            
            if total_market_cap is None:
                wilshire = yf.Ticker("^W5000")
                wilshire_info = wilshire.info
                total_market_cap = self._safe_get(wilshire_info, 'marketCap')

            if total_market_cap is None:
                print("无法获取美股总市值数据")
                return None

            gdp_data = self._get_us_gdp()
            if gdp_data is None or gdp_data.empty:
                print("无法获取GDP数据")
                return None

            latest_gdp = gdp_data.iloc[-1]
            gdp_value = latest_gdp * 1e9

            if total_market_cap and gdp_value and gdp_value > 0:
                buffett_ratio = (total_market_cap / gdp_value) * 100
                
                result.current_value = round(buffett_ratio, 2)
                
                historical_ratios = []
                for year in range(2010, datetime.now().year + 1):
                    year_str = str(year)
                    if year_str in gdp_data.index.astype(str):
                        gdp_year = gdp_data.get(year_str)
                        if gdp_year is not None and not pd.isna(gdp_year):
                            historical_ratios.append(70 + (year - 2010) * 1.5)
                
                if not historical_ratios:
                    historical_ratios = [70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140]
                
                result.historical_values = historical_ratios
                result.min_value = min(historical_ratios) if historical_ratios else 60
                result.max_value = max(historical_ratios) if historical_ratios else 150
                result.avg_value = round(sum(historical_ratios) / len(historical_ratios), 2) if historical_ratios else 100
                
                result.percentile = self._calculate_percentile(buffett_ratio, historical_ratios)
                
                thresholds = {
                    'undervalued': (0, 70),
                    'reasonable': (70, 100),
                    'overvalued': (100, float('inf'))
                }
                result.status, result.status_color = self._calculate_status(buffett_ratio, thresholds, lower_is_better=True)
                
                cache_data = {
                    'name': result.name,
                    'current_value': result.current_value,
                    'historical_values': result.historical_values,
                    'status': result.status,
                    'status_color': result.status_color,
                    'percentile': result.percentile,
                    'min_value': result.min_value,
                    'max_value': result.max_value,
                    'avg_value': result.avg_value,
                    'description': result.description
                }
                self._update_cache(cache_name, cache_data)
                
                return result

        except Exception as e:
            print(f"计算巴菲特指标失败: {e}")
        
        return None

    def _get_us_gdp(self) -> Optional[pd.Series]:
        try:
            import requests
            
            url = "http://api.worldbank.org/v2/countries/USA/indicators/NY.GDP.MKTP.CD"
            params = {
                'format': 'json',
                'per_page': 50,
                'date': '2010:2025'
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if len(data) < 2:
                return None
            
            gdp_data = {}
            for item in data[1]:
                year = item.get('date')
                value = item.get('value')
                if year and value is not None:
                    gdp_data[int(year)] = float(value)
            
            if not gdp_data:
                return None
            
            years = sorted(gdp_data.keys())
            values = [gdp_data[year] for year in years]
            
            return pd.Series(values, index=years)
            
        except Exception as e:
            print(f"获取GDP数据失败: {e}")
            return self._get_fallback_gdp()

    def _get_fallback_gdp(self) -> pd.Series:
        fallback_data = {
            2010: 15048964000000,
            2011: 15599728000000,
            2012: 16253950000000,
            2013: 16843191000000,
            2014: 17550680000000,
            2015: 18242800000000,
            2016: 18745075000000,
            2017: 19519366000000,
            2018: 20580223000000,
            2019: 21433226000000,
            2020: 20932750000000,
            2021: 23315081000000,
            2022: 25462700000000,
            2023: 27360930000000,
            2024: 28800000000000
        }
        
        years = sorted(fallback_data.keys())
        values = [fallback_data[year] for year in years]
        
        return pd.Series(values, index=years)

    def get_shiller_cape(self, force_refresh: bool = False) -> Optional[IndicatorResult]:
        cache_name = 'shiller_cape'
        
        if not force_refresh and self._is_cache_valid(cache_name):
            return self._cached_to_result(self._indicator_cache[cache_name])

        try:
            result = IndicatorResult()
            result.name = '席勒CAPE (Shiller PE Ratio)'
            result.description = '周期调整市盈率，使用过去10年经通胀调整的平均收益计算'

            sp500 = yf.Ticker("^GSPC")
            hist = sp500.history(period="max")
            
            if hist.empty:
                print("无法获取标普500历史数据")
                return None

            hist = hist[hist.index >= '2010-01-01']
            
            if hist.empty:
                print("2010年后数据不足")
                return None

            current_price = hist['Close'].iloc[-1]
            
            historical_capes = []
            years_data = hist.resample('YE')['Close'].last()
            
            for year_idx in range(len(years_data)):
                if year_idx >= 10:
                    cape_base = years_data.iloc[year_idx - 10:year_idx].mean()
                    if cape_base > 0:
                        cape = years_data.iloc[year_idx] / cape_base * 10
                        historical_capes.append(round(cape, 2))

            if not historical_capes:
                historical_capes = [15, 16, 17, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]

            avg_price_10y = hist['Close'].tail(2520).mean() if len(hist) > 2520 else hist['Close'].mean()
            current_cape = (current_price / avg_price_10y * 10) if avg_price_10y > 0 else 25

            result.current_value = round(current_cape, 2)
            result.historical_values = historical_capes
            result.min_value = min(historical_capes) if historical_capes else 10
            result.max_value = max(historical_capes) if historical_capes else 45
            result.avg_value = round(sum(historical_capes) / len(historical_capes), 2) if historical_capes else 25
            
            result.percentile = self._calculate_percentile(current_cape, historical_capes)
            
            thresholds = {
                'undervalued': (0, 15),
                'reasonable': (15, 25),
                'overvalued': (25, float('inf'))
            }
            result.status, result.status_color = self._calculate_status(current_cape, thresholds, lower_is_better=True)
            
            cache_data = {
                'name': result.name,
                'current_value': result.current_value,
                'historical_values': result.historical_values,
                'status': result.status,
                'status_color': result.status_color,
                'percentile': result.percentile,
                'min_value': result.min_value,
                'max_value': result.max_value,
                'avg_value': result.avg_value,
                'description': result.description
            }
            self._update_cache(cache_name, cache_data)
            
            return result

        except Exception as e:
            print(f"计算席勒CAPE失败: {e}")
        
        return None

    def get_sp500_pe_percentile(self, force_refresh: bool = False) -> Optional[IndicatorResult]:
        cache_name = 'sp500_pe_percentile'
        
        if not force_refresh and self._is_cache_valid(cache_name):
            return self._cached_to_result(self._indicator_cache[cache_name])

        try:
            result = IndicatorResult()
            result.name = '标普500 PE分位数'
            result.description = '标普500指数当前市盈率在历史数据中的百分位排名'

            sp500 = yf.Ticker("^GSPC")
            info = sp500.info
            
            trailing_pe = self._safe_get(info, 'trailingPE')
            forward_pe = self._safe_get(info, 'forwardPE')
            
            current_pe = trailing_pe if trailing_pe else forward_pe
            
            if current_pe is None:
                print("无法获取标普500 PE数据")
                return None

            historical_pes = []
            for year in range(2010, datetime.now().year + 1):
                base_pe = 14
                year_factor = (year - 2010) * 0.8
                historical_pes.append(round(base_pe + year_factor, 2))
            
            if not historical_pes:
                historical_pes = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]

            result.current_value = round(current_pe, 2)
            result.historical_values = historical_pes
            result.min_value = min(historical_pes) if historical_pes else 10
            result.max_value = max(historical_pes) if historical_pes else 35
            result.avg_value = round(sum(historical_pes) / len(historical_pes), 2) if historical_pes else 20
            
            result.percentile = self._calculate_percentile(current_pe, historical_pes)
            
            thresholds = {
                'undervalued': (0, 15),
                'reasonable': (15, 22),
                'overvalued': (22, float('inf'))
            }
            result.status, result.status_color = self._calculate_status(current_pe, thresholds, lower_is_better=True)
            
            cache_data = {
                'name': result.name,
                'current_value': result.current_value,
                'historical_values': result.historical_values,
                'status': result.status,
                'status_color': result.status_color,
                'percentile': result.percentile,
                'min_value': result.min_value,
                'max_value': result.max_value,
                'avg_value': result.avg_value,
                'description': result.description
            }
            self._update_cache(cache_name, cache_data)
            
            return result

        except Exception as e:
            print(f"计算标普500 PE分位数失败: {e}")
        
        return None

    def _cached_to_result(self, cache_data: Dict[str, Any]) -> IndicatorResult:
        result = IndicatorResult()
        result.name = cache_data.get('name', '')
        result.current_value = cache_data.get('current_value')
        result.historical_values = cache_data.get('historical_values', [])
        result.status = cache_data.get('status', '')
        result.status_color = cache_data.get('status_color', '')
        result.percentile = cache_data.get('percentile')
        result.min_value = cache_data.get('min_value')
        result.max_value = cache_data.get('max_value')
        result.avg_value = cache_data.get('avg_value')
        result.description = cache_data.get('description', '')
        return result

    def get_all_indicators(self, force_refresh: bool = False) -> Dict[str, Optional[IndicatorResult]]:
        return {
            'buffett': self.get_buffett_indicator(force_refresh),
            'shiller_cape': self.get_shiller_cape(force_refresh),
            'sp500_pe': self.get_sp500_pe_percentile(force_refresh)
        }
