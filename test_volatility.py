#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试波动率分析器模块
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desktop_tools.volatility_analyzer import VolatilityAnalyzer, VolatilityAlert
import pandas as pd
import numpy as np


def test_basic_import():
    """测试基本导入和实例化"""
    print("=" * 50)
    print("测试1: 基本导入和实例化")
    print("=" * 50)

    analyzer = VolatilityAnalyzer()
    assert analyzer is not None, "VolatilityAnalyzer 实例化失败"
    print("✓ VolatilityAnalyzer 实例化成功")

    alert = VolatilityAlert()
    assert alert is not None, "VolatilityAlert 实例化失败"
    print("✓ VolatilityAlert 实例化成功")

    methods = [
        'get_price_data',
        'calculate_log_returns',
        'calculate_returns',
        'calculate_historical_volatility',
        'calculate_all_volatility_windows',
        'calculate_volatility_measures',
        'calculate_volatility_zscore',
        'check_volatility_alert',
        'calculate_volatility_return_correlation',
        'calculate_portfolio_volatility',
        'analyze_single_stock',
        'analyze_portfolio'
    ]

    for method in methods:
        assert hasattr(analyzer, method), f"方法 {method} 缺失"
        print(f"✓ 方法 {method} 存在")

    print("\n✓ 测试1通过: 所有方法都已实现\n")


def test_volatility_calculation():
    """测试波动率计算逻辑"""
    print("=" * 50)
    print("测试2: 波动率计算逻辑")
    print("=" * 50)

    analyzer = VolatilityAnalyzer()

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * np.cumprod(1 + returns)

    test_data = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    log_returns = analyzer.calculate_log_returns(test_data)
    assert len(log_returns) == 99, f"对数收益率长度错误: {len(log_returns)}"
    print(f"✓ 对数收益率计算正确，共 {len(log_returns)} 个数据点")

    simple_returns = analyzer.calculate_returns(test_data)
    assert len(simple_returns) == 99, f"简单收益率长度错误: {len(simple_returns)}"
    print("✓ 简单收益率计算正确")

    vol_20 = analyzer.calculate_historical_volatility(test_data, window=20, annualize=True)
    assert len(vol_20) == 100, f"波动率序列长度错误: {len(vol_20)}"
    print(f"✓ 20日滚动波动率计算正确")

    vol_dict = analyzer.calculate_all_volatility_windows(
        test_data, windows=[5, 10, 20, 60]
    )
    assert 5 in vol_dict, "5日波动率缺失"
    assert 10 in vol_dict, "10日波动率缺失"
    assert 20 in vol_dict, "20日波动率缺失"
    assert 60 in vol_dict, "60日波动率缺失"
    print("✓ 多窗口波动率计算正确")

    vol_measures = analyzer.calculate_volatility_measures(test_data, lookback_period=100)
    assert 'current_volatility' in vol_measures, "当前波动率缺失"
    assert 'mean_volatility' in vol_measures, "平均波动率缺失"
    print(f"✓ 波动率指标计算正确: 当前波动率={vol_measures.get('current_volatility'):.2%}")

    print("\n✓ 测试2通过: 波动率计算逻辑正确\n")


def test_zscore_and_alerts():
    """测试Z分数和预警机制"""
    print("=" * 50)
    print("测试3: Z分数和预警机制")
    print("=" * 50)

    analyzer = VolatilityAnalyzer()

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    base_price = 100

    returns = np.random.normal(0.001, 0.015, 300)
    returns[-20:] = np.random.normal(0.001, 0.04, 20)

    prices = base_price * np.cumprod(1 + returns)

    test_data = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 300)
    }, index=dates)

    z_score, z_scores = analyzer.calculate_volatility_zscore(
        test_data, vol_window=20, lookback_period=252
    )

    assert z_score is not None, "Z分数计算失败"
    print(f"✓ Z分数计算正确: {z_score:.2f}")
    print(f"✓ Z分数序列长度: {len(z_scores)}")

    alert = analyzer.check_volatility_alert(
        'TEST', test_data, z_threshold=1.0, vol_window=20
    )

    if z_score > 1.0:
        assert alert is not None, "应该触发高波动率预警"
        assert alert.type == 'HIGH_VOLATILITY', "预警类型错误"
        print(f"✓ 高波动率预警正确触发: {alert.message}")
    elif z_score < -1.0:
        assert alert is not None, "应该触发低波动率预警"
        assert alert.type == 'LOW_VOLATILITY', "预警类型错误"
        print(f"✓ 低波动率预警正确触发: {alert.message}")
    else:
        print(f"✓ Z分数 {z_score:.2f} 在正常范围内，无预警")

    print("\n✓ 测试3通过: Z分数和预警机制工作正常\n")


def test_correlation_analysis():
    """测试波动率与收益相关性分析"""
    print("=" * 50)
    print("测试4: 波动率与收益相关性分析")
    print("=" * 50)

    analyzer = VolatilityAnalyzer()

    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 200)
    prices = base_price * np.cumprod(1 + returns)

    test_data = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 200)
    }, index=dates)

    corr_analysis = analyzer.calculate_volatility_return_correlation(
        test_data, vol_window=20, lookback_period=180
    )

    assert 'overall_correlation' in corr_analysis, "整体相关性缺失"
    assert 'sample_size' in corr_analysis, "样本大小缺失"

    print(f"✓ 相关性分析结果:")
    print(f"  - 整体相关性: {corr_analysis.get('overall_correlation'):.4f}")
    print(f"  - 样本大小: {corr_analysis.get('sample_size')}")

    pos_corr = corr_analysis.get('positive_return_correlation')
    neg_corr = corr_analysis.get('negative_return_correlation')

    if pos_corr is not None:
        print(f"  - 上涨时相关性: {pos_corr:.4f}")
    if neg_corr is not None:
        print(f"  - 下跌时相关性: {neg_corr:.4f}")

    print("\n✓ 测试4通过: 相关性分析工作正常\n")


def test_portfolio_analysis():
    """测试投资组合分析"""
    print("=" * 50)
    print("测试5: 投资组合波动率分析")
    print("=" * 50)

    analyzer = VolatilityAnalyzer()

    np.random.seed(42)
    n_days = 252

    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')

    returns_1 = np.random.normal(0.0005, 0.015, n_days)
    returns_2 = np.random.normal(0.0008, 0.025, n_days)
    returns_3 = np.random.normal(0.0003, 0.010, n_days)

    prices_1 = 100 * np.cumprod(1 + returns_1)
    prices_2 = 50 * np.cumprod(1 + returns_2)
    prices_3 = 200 * np.cumprod(1 + returns_3)

    test_data_dict = {
        'AAPL': pd.DataFrame({'Close': prices_1}, index=dates),
        'MSFT': pd.DataFrame({'Close': prices_2}, index=dates),
        'GOOG': pd.DataFrame({'Close': prices_3}, index=dates)
    }

    original_get_price_data = analyzer.get_price_data

    def mock_get_price_data(symbol, period='1y', interval='1d'):
        return test_data_dict.get(symbol.upper())

    analyzer.get_price_data = mock_get_price_data

    symbols = ['AAPL', 'MSFT', 'GOOG']
    weights = [0.4, 0.35, 0.25]

    port_analysis = analyzer.calculate_portfolio_volatility(symbols, weights, period='1y')

    assert 'portfolio_volatility' in port_analysis, "组合波动率缺失"
    assert 'individual_volatilities' in port_analysis, "个体波动率缺失"
    assert 'diversification_ratio' in port_analysis, "分散化比率缺失"

    print(f"✓ 投资组合分析结果:")
    print(f"  - 组合波动率: {port_analysis.get('portfolio_volatility'):.2%}")
    print(f"  - 加权平均波动率: {port_analysis.get('weighted_average_vol'):.2%}")
    print(f"  - 分散化比率: {port_analysis.get('diversification_ratio'):.4f}")

    div_benefit = port_analysis.get('diversification_benefit')
    if div_benefit:
        print(f"  - 分散化收益: {div_benefit:.2%}")

    individual_vols = port_analysis.get('individual_volatilities', {})
    print(f"\n  个股波动率:")
    for symbol, vol in individual_vols.items():
        print(f"    - {symbol}: {vol:.2%}")

    contributions = port_analysis.get('contributions', {})
    print(f"\n  风险贡献度:")
    for symbol, data in contributions.items():
        print(f"    - {symbol}: 权重={data['weight']:.2%}, 风险贡献={data['contribution_pct']:.1f}%")

    analyzer.get_price_data = original_get_price_data

    print("\n✓ 测试5通过: 投资组合分析工作正常\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始运行波动率分析器测试套件")
    print("=" * 60 + "\n")

    try:
        test_basic_import()
        test_volatility_calculation()
        test_zscore_and_alerts()
        test_correlation_analysis()
        test_portfolio_analysis()

        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 测试发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
