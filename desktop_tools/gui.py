from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QGroupBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QProgressBar, QTextEdit,
    QSplitter, QMessageBox, QStatusBar, QToolBar, QAction,
    QMenu, QMenuBar, QFrame, QSizePolicy, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl
from PyQt5.QtGui import QFont, QColor, QDesktopServices, QIcon
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import ConfigManager
from .watchlist import WatchlistManager
from .data_provider import DataProvider
from .news_manager import NewsManager
from .screener import StockScreener
from .valuation_analyzer import ValuationAnalyzer
from .radar_chart import RadarChartWidget, DimensionScoreBar, TotalScoreDisplay
from .market_indicators import MarketIndicators, IndicatorResult
from .technical_analyzer import TechnicalAnalyzer
from .technical_charts import PriceChartWidget, SignalDisplayWidget


class ValuationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._watchlist_manager = WatchlistManager()
        self._data_provider = DataProvider()
        self._valuation_analyzer = ValuationAnalyzer()
        self._analysis_thread = None
        self._current_metrics = None
        self._init_ui()
        self._load_watchlist()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("选择股票:"))
        
        self._stock_combo = QComboBox()
        self._stock_combo.setEditable(True)
        self._stock_combo.setMinimumWidth(200)
        control_layout.addWidget(self._stock_combo)

        self._analyze_btn = QPushButton("开始分析")
        self._analyze_btn.setMinimumHeight(35)
        self._analyze_btn.clicked.connect(self._analyze_current_stock)
        control_layout.addWidget(self._analyze_btn)

        self._analyze_all_btn = QPushButton("分析所有自选股")
        self._analyze_all_btn.setMinimumHeight(35)
        self._analyze_all_btn.clicked.connect(self._analyze_all_watchlist)
        control_layout.addWidget(self._analyze_all_btn)

        self._refresh_btn = QPushButton("刷新自选股列表")
        self._refresh_btn.setMinimumHeight(35)
        self._refresh_btn.clicked.connect(self._load_watchlist)
        control_layout.addWidget(self._refresh_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("请选择股票并开始分析")
        self._status_label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self._status_label)

        main_splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        info_group = QGroupBox("股票基本信息")
        info_layout = QVBoxLayout(info_group)
        
        self._info_table = QTableWidget()
        self._info_table.setColumnCount(2)
        self._info_table.setHorizontalHeaderLabels(["项目", "数值"])
        self._info_table.horizontalHeader().setStretchLastSection(True)
        self._info_table.setMinimumHeight(150)
        self._info_table.setMaximumHeight(200)
        info_layout.addWidget(self._info_table)

        left_layout.addWidget(info_group)

        metrics_group = QGroupBox("估值指标")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self._metrics_table = QTableWidget()
        self._metrics_table.setColumnCount(3)
        self._metrics_table.setHorizontalHeaderLabels(["指标", "当前值", "行业平均"])
        self._metrics_table.horizontalHeader().setStretchLastSection(True)
        self._metrics_table.setMinimumHeight(200)
        metrics_layout.addWidget(self._metrics_table)

        left_layout.addWidget(metrics_group)

        dcf_group = QGroupBox("DCF估值分析")
        dcf_layout = QVBoxLayout(dcf_group)
        
        self._dcf_table = QTableWidget()
        self._dcf_table.setColumnCount(2)
        self._dcf_table.setHorizontalHeaderLabels(["项目", "数值"])
        self._dcf_table.horizontalHeader().setStretchLastSection(True)
        self._dcf_table.setMinimumHeight(150)
        self._dcf_table.setMaximumHeight(200)
        dcf_layout.addWidget(self._dcf_table)

        left_layout.addWidget(dcf_group)
        left_layout.addStretch()

        main_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        radar_group = QGroupBox("综合评分雷达图")
        radar_layout = QVBoxLayout(radar_group)
        
        self._radar_chart = RadarChartWidget()
        self._radar_chart.setMinimumHeight(350)
        radar_layout.addWidget(self._radar_chart)

        right_layout.addWidget(radar_group)

        score_group = QGroupBox("综合评分")
        score_layout = QHBoxLayout(score_group)

        self._total_score_display = TotalScoreDisplay()
        self._total_score_display.setMinimumWidth(180)
        score_layout.addWidget(self._total_score_display)

        dimensions_layout = QVBoxLayout()
        self._dimensions = {
            '价格合理性': DimensionScoreBar('价格合理性', 0.40),
            '成长性': DimensionScoreBar('成长性', 0.35),
            '安全性': DimensionScoreBar('安全性', 0.25),
        }
        for name, bar in self._dimensions.items():
            dimensions_layout.addWidget(bar)
        dimensions_layout.addStretch()
        
        score_layout.addLayout(dimensions_layout, 1)

        right_layout.addWidget(score_group)

        summary_group = QGroupBox("估值总结")
        summary_layout = QVBoxLayout(summary_group)
        
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setMinimumHeight(100)
        self._summary_text.setMaximumHeight(150)
        summary_layout.addWidget(self._summary_text)

        right_layout.addWidget(summary_group)
        right_layout.addStretch()

        main_splitter.addWidget(right_widget)

        main_splitter.setSizes([500, 500])

        layout.addWidget(main_splitter, 1)

    def _load_watchlist(self):
        self._stock_combo.clear()
        symbols = self._watchlist_manager.watchlist
        quotes = self._watchlist_manager.get_sorted_quotes()
        
        for quote in quotes:
            symbol = quote.get('symbol', '')
            name = quote.get('name', '')
            if symbol:
                display_text = f"{symbol}"
                if name:
                    display_text += f" - {name}"
                self._stock_combo.addItem(display_text, symbol)
        
        for symbol in symbols:
            exists = False
            for i in range(self._stock_combo.count()):
                if self._stock_combo.itemData(i) == symbol:
                    exists = True
                    break
            if not exists:
                self._stock_combo.addItem(symbol, symbol)
        
        self._status_label.setText(f"已加载 {len(symbols)} 只自选股")

    def _get_selected_symbol(self) -> str:
        index = self._stock_combo.currentIndex()
        if index >= 0:
            symbol = self._stock_combo.itemData(index)
            if symbol:
                return symbol
        
        text = self._stock_combo.currentText().strip()
        if text:
            if ' - ' in text:
                return text.split(' - ')[0].strip()
            return text
        return ''

    def _analyze_current_stock(self):
        symbol = self._get_selected_symbol()
        if not symbol:
            QMessageBox.warning(self, "提示", "请选择或输入股票代码")
            return
        
        self._analyze_stocks([symbol])

    def _analyze_all_watchlist(self):
        symbols = self._watchlist_manager.watchlist
        if not symbols:
            QMessageBox.warning(self, "提示", "自选股列表为空")
            return
        
        self._analyze_stocks(symbols)

    def _analyze_stocks(self, symbols: List[str]):
        if self._analysis_thread and self._analysis_thread.isRunning():
            QMessageBox.information(self, "提示", "分析正在进行中，请稍候...")
            return

        self._analyze_btn.setEnabled(False)
        self._analyze_all_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setMaximum(len(symbols))
        self._progress_bar.setValue(0)
        self._status_label.setText(f"开始分析 {len(symbols)} 只股票...")

        self._analysis_thread = ValuationAnalysisThread(
            self._valuation_analyzer, symbols
        )
        self._analysis_thread.progress_signal.connect(self._on_analysis_progress)
        self._analysis_thread.finished_signal.connect(self._on_analysis_finished)
        self._analysis_thread.error_signal.connect(self._on_analysis_error)
        self._analysis_thread.start()

    def _on_analysis_progress(self, index: int, total: int, symbol: str):
        self._progress_bar.setValue(index + 1)
        self._status_label.setText(f"正在分析: {symbol} ({index + 1}/{total})")

    def _on_analysis_finished(self, results: List[Dict[str, Any]]):
        self._analyze_btn.setEnabled(True)
        self._analyze_all_btn.setEnabled(True)
        self._progress_bar.setVisible(False)

        if not results:
            self._status_label.setText("分析完成，但没有有效结果")
            return

        valid_results = [r for r in results if r.get('success')]
        
        if len(valid_results) == 1:
            self._display_result(valid_results[0])
            self._status_label.setText(f"分析完成: {valid_results[0]['symbol']}")
        else:
            self._display_batch_results(valid_results)
            self._status_label.setText(f"分析完成: 共 {len(valid_results)} 只股票")

    def _on_analysis_error(self, error_msg: str):
        self._analyze_btn.setEnabled(True)
        self._analyze_all_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"分析出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"分析过程中出错:\n{error_msg}")

    def _display_result(self, result: Dict[str, Any]):
        self._current_metrics = result.get('metrics')
        if not self._current_metrics:
            return

        self._display_info_table(result)
        self._display_metrics_table(result)
        self._display_dcf_table(result)
        self._display_scores(result)
        self._display_summary(result)

    def _display_batch_results(self, results: List[Dict[str, Any]]):
        if not results:
            return

        sorted_results = sorted(
            results,
            key=lambda x: x.get('metrics').total_score if x.get('metrics') and hasattr(x.get('metrics'), 'total_score') else 0,
            reverse=True
        )

        best_result = sorted_results[0]
        self._display_result(best_result)

        summary_text = "批量分析完成，按综合评分排序:\n\n"
        for i, result in enumerate(sorted_results[:10]):
            metrics = result.get('metrics')
            if metrics:
                symbol = result['symbol']
                score = metrics.total_score if hasattr(metrics, 'total_score') else 0
                status = metrics.valuation_status if hasattr(metrics, 'valuation_status') else '-'
                summary_text += f"{i+1}. {symbol}: {int(score)}分 - {status}\n"

        if len(sorted_results) > 10:
            summary_text += f"\n... 还有 {len(sorted_results) - 10} 只股票"

        self._summary_text.setText(summary_text)

    def _display_info_table(self, result: Dict[str, Any]):
        metrics = result.get('metrics')
        if not metrics:
            return

        self._info_table.setRowCount(0)
        
        info_items = [
            ("股票代码", result.get('symbol', '')),
            ("公司名称", metrics.name if hasattr(metrics, 'name') else ''),
            ("当前价格", f"${metrics.current_price:.2f}" if hasattr(metrics, 'current_price') and metrics.current_price else '-'),
            ("所属行业", metrics.industry if hasattr(metrics, 'industry') else ''),
            ("所属板块", metrics.sector if hasattr(metrics, 'sector') else ''),
            ("市值", self._format_market_cap(metrics.market_cap) if hasattr(metrics, 'market_cap') and metrics.market_cap else '-'),
        ]

        self._info_table.setRowCount(len(info_items))
        for i, (label, value) in enumerate(info_items):
            self._info_table.setItem(i, 0, QTableWidgetItem(label))
            self._info_table.setItem(i, 1, QTableWidgetItem(str(value)))

    def _display_metrics_table(self, result: Dict[str, Any]):
        metrics = result.get('metrics')
        if not metrics:
            return

        self._metrics_table.setRowCount(0)
        
        metric_items = [
            ("滚动市盈率 (PE TTM)", metrics.pe_trailing, metrics.industry_avg_pe),
            ("预期市盈率 (PE Forward)", metrics.pe_forward, None),
            ("市净率 (PB)", metrics.pb_ratio, metrics.industry_avg_pb),
            ("市盈增长比 (PEG)", metrics.peg_ratio, None),
            ("市销率 (PS)", metrics.price_to_sales, metrics.industry_avg_ps),
            ("企业价值倍数 (EV/EBITDA)", metrics.ev_to_ebitda, None),
            ("股息率", metrics.dividend_yield, None),
            ("每股自由现金流", metrics.fcf_per_share, None),
        ]

        self._metrics_table.setRowCount(len(metric_items))
        for i, (label, value, industry_avg) in enumerate(metric_items):
            self._metrics_table.setItem(i, 0, QTableWidgetItem(label))
            
            value_str = f"{value:.2f}" if value is not None else '-'
            value_item = QTableWidgetItem(value_str)
            self._metrics_table.setItem(i, 1, value_item)
            
            avg_str = f"{industry_avg:.2f}" if industry_avg is not None else '-'
            avg_item = QTableWidgetItem(avg_str)
            self._metrics_table.setItem(i, 2, avg_item)

            self._style_metric_cell(value_item, label, value, industry_avg)

    def _style_metric_cell(self, item, label: str, value: Optional[float], industry_avg: Optional[float]):
        if value is None:
            return

        green = QColor(34, 197, 94)
        yellow = QColor(251, 191, 36)
        red = QColor(239, 68, 68)
        blue = QColor(59, 130, 246)

        if 'PE' in label or 'PEG' in label:
            if value < 10:
                item.setForeground(green)
            elif value < 20:
                item.setForeground(blue)
            elif value < 30:
                item.setForeground(yellow)
            else:
                item.setForeground(red)
        elif 'PB' in label:
            if value < 1:
                item.setForeground(green)
            elif value < 2:
                item.setForeground(blue)
            elif value < 3:
                item.setForeground(yellow)
            else:
                item.setForeground(red)
        elif 'PS' in label:
            if value < 1:
                item.setForeground(green)
            elif value < 3:
                item.setForeground(blue)
            elif value < 5:
                item.setForeground(yellow)
            else:
                item.setForeground(red)
        elif 'EV/EBITDA' in label:
            if value < 8:
                item.setForeground(green)
            elif value < 12:
                item.setForeground(blue)
            elif value < 15:
                item.setForeground(yellow)
            else:
                item.setForeground(red)
        elif '股息率' in label:
            if value > 0.05:
                item.setForeground(green)
            elif value > 0.03:
                item.setForeground(blue)
            elif value > 0.01:
                item.setForeground(yellow)
            else:
                item.setForeground(red)

    def _display_dcf_table(self, result: Dict[str, Any]):
        metrics = result.get('metrics')
        if not metrics:
            return

        self._dcf_table.setRowCount(0)
        
        dcf_items = []
        
        if hasattr(metrics, 'current_price') and metrics.current_price:
            dcf_items.append(("当前价格", f"${metrics.current_price:.2f}"))
        
        if hasattr(metrics, 'dcf_intrinsic_value') and metrics.dcf_intrinsic_value:
            dcf_items.append(("DCF内在价值", f"${metrics.dcf_intrinsic_value:.2f}"))
        
        if hasattr(metrics, 'safe_price') and metrics.safe_price:
            dcf_items.append(("安全价格 (25%安全边际)", f"${metrics.safe_price:.2f}"))
        
        if hasattr(metrics, 'margin_of_safety') and metrics.margin_of_safety is not None:
            dcf_items.append(("安全边际", f"{metrics.margin_of_safety:.1f}%"))
        
        if hasattr(metrics, 'reasonable_price_low') and metrics.reasonable_price_low:
            if hasattr(metrics, 'reasonable_price_high') and metrics.reasonable_price_high:
                dcf_items.append((
                    "合理价格区间", 
                    f"${metrics.reasonable_price_low:.2f} - ${metrics.reasonable_price_high:.2f}"
                ))

        if hasattr(metrics, 'growth_rate_5y') and metrics.growth_rate_5y:
            dcf_items.append(("预期5年增长率", f"{metrics.growth_rate_5y:.1%}"))

        self._dcf_table.setRowCount(len(dcf_items))
        for i, (label, value) in enumerate(dcf_items):
            self._dcf_table.setItem(i, 0, QTableWidgetItem(label))
            value_item = QTableWidgetItem(str(value))
            
            if '安全边际' in label:
                try:
                    margin = float(value.strip('%'))
                    if margin > 25:
                        value_item.setForeground(QColor(34, 197, 94))
                    elif margin > 0:
                        value_item.setForeground(QColor(59, 130, 246))
                    else:
                        value_item.setForeground(QColor(239, 68, 68))
                except:
                    pass
            
            self._dcf_table.setItem(i, 1, value_item)

    def _display_scores(self, result: Dict[str, Any]):
        metrics = result.get('metrics')
        scores = result.get('scores', {})
        
        if not metrics and not scores:
            return

        total_score = 0
        status = ''
        
        if metrics:
            if hasattr(metrics, 'total_score'):
                total_score = metrics.total_score
            if hasattr(metrics, 'valuation_status'):
                status = metrics.valuation_status
            
            if hasattr(metrics, 'price_reasonableness_score'):
                self._dimensions['价格合理性'].set_score(metrics.price_reasonableness_score)
            if hasattr(metrics, 'growth_score'):
                self._dimensions['成长性'].set_score(metrics.growth_score)
            if hasattr(metrics, 'safety_score'):
                self._dimensions['安全性'].set_score(metrics.safety_score)

        if total_score > 0:
            self._total_score_display.set_score(total_score, status)

        if scores:
            self._radar_chart.set_scores(scores, total_score, status)

    def _display_summary(self, result: Dict[str, Any]):
        metrics = result.get('metrics')
        if not metrics:
            return

        summary = ""

        if hasattr(metrics, 'valuation_status') and metrics.valuation_status:
            summary += f"估值状态: {metrics.valuation_status}\n\n"

        if hasattr(metrics, 'total_score'):
            summary += f"综合评分: {int(metrics.total_score)}分\n"
            
            if hasattr(metrics, 'price_reasonableness_score'):
                summary += f"  - 价格合理性: {int(metrics.price_reasonableness_score)}分 (40%)\n"
            if hasattr(metrics, 'growth_score'):
                summary += f"  - 成长性: {int(metrics.growth_score)}分 (35%)\n"
            if hasattr(metrics, 'safety_score'):
                summary += f"  - 安全性: {int(metrics.safety_score)}分 (25%)\n"

        if hasattr(metrics, 'reasonable_price_low') and metrics.reasonable_price_low:
            if hasattr(metrics, 'reasonable_price_high') and metrics.reasonable_price_high:
                summary += f"\n合理价格区间: ${metrics.reasonable_price_low:.2f} - ${metrics.reasonable_price_high:.2f}\n"

        if hasattr(metrics, 'margin_of_safety') and metrics.margin_of_safety is not None:
            summary += f"安全边际: {metrics.margin_of_safety:.1f}%"
            if metrics.margin_of_safety > 25:
                summary += " (具有较高安全边际)"
            elif metrics.margin_of_safety > 0:
                summary += " (有一定安全边际)"
            else:
                summary += " (安全边际不足)"

        self._summary_text.setText(summary)

    def _format_market_cap(self, cap: float) -> str:
        if cap is None:
            return '-'
        if cap >= 1e12:
            return f"${cap/1e12:.2f}万亿"
        elif cap >= 1e9:
            return f"${cap/1e9:.2f}千亿"
        elif cap >= 1e6:
            return f"${cap/1e6:.2f}百万"
        else:
            return f"${cap:.0f}"

    def refresh(self):
        self._load_watchlist()


class ValuationAnalysisThread(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, analyzer: ValuationAnalyzer, symbols: List[str]):
        super().__init__()
        self._analyzer = analyzer
        self._symbols = symbols

    def run(self):
        results = []
        total = len(self._symbols)
        
        try:
            for i, symbol in enumerate(self._symbols):
                try:
                    self.progress_signal.emit(i, total, symbol)
                    
                    metrics = self._analyzer.analyze_stock(symbol)
                    
                    if metrics:
                        scores = self._extract_scores(metrics)
                        
                        result = {
                            'symbol': symbol,
                            'success': True,
                            'metrics': metrics,
                            'scores': scores,
                        }
                        results.append(result)
                    else:
                        results.append({
                            'symbol': symbol,
                            'success': False,
                            'error': '无法获取估值数据'
                        })
                        
                except Exception as e:
                    results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
                    
            self.finished_signal.emit(results)
            
        except Exception as e:
            self.error_signal.emit(str(e))

    def _extract_scores(self, metrics) -> Dict[str, float]:
        scores = {}
        
        if hasattr(metrics, 'total_score'):
            total = metrics.total_score
            
            if hasattr(metrics, 'price_reasonableness_score'):
                scores['pe_score'] = metrics.price_reasonableness_score * 0.5
                scores['pb_score'] = metrics.price_reasonableness_score * 0.3
                scores['margin_score'] = metrics.price_reasonableness_score * 0.5
            else:
                scores['pe_score'] = total * 0.3
                scores['pb_score'] = total * 0.3
                scores['margin_score'] = total * 0.4
            
            if hasattr(metrics, 'growth_score'):
                scores['growth_score'] = metrics.growth_score * 0.7
                scores['profit_score'] = metrics.growth_score * 0.5
                scores['fcf_score'] = metrics.growth_score * 0.4
            else:
                scores['growth_score'] = total * 0.6
                scores['profit_score'] = total * 0.5
                scores['fcf_score'] = total * 0.4
            
            if hasattr(metrics, 'safety_score'):
                scores['dividend_score'] = metrics.safety_score * 0.5
                scores['financial_health_score'] = metrics.safety_score * 0.6
            else:
                scores['dividend_score'] = total * 0.4
                scores['financial_health_score'] = total * 0.5
            
            scores['peg_score'] = total * 0.5
            scores['quality_score'] = total * 0.6
            
            for key in scores:
                scores[key] = min(100.0, max(0.0, scores[key]))
        
        return scores


class WatchlistTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager()
        self._watchlist_manager = WatchlistManager()
        self._data_provider = DataProvider()
        self._init_ui()
        self._init_connections()
        self._refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        control_group = QGroupBox("操作")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("添加股票:"))
        self._symbol_input = QLineEdit()
        self._symbol_input.setPlaceholderText("输入股票代码，如 AAPL")
        self._symbol_input.setMaximumWidth(150)
        control_layout.addWidget(self._symbol_input)

        self._add_btn = QPushButton("添加")
        control_layout.addWidget(self._add_btn)

        control_layout.addSpacing(20)

        self._remove_btn = QPushButton("移除选中")
        control_layout.addWidget(self._remove_btn)

        self._refresh_btn = QPushButton("刷新数据")
        control_layout.addWidget(self._refresh_btn)

        control_layout.addSpacing(20)

        control_layout.addWidget(QLabel("排序:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems([
            "股票代码", "名称", "当前价格", "涨跌幅",
            "成交量", "市值", "持仓数量", "盈亏金额", "盈亏百分比", "持仓市值"
        ])
        control_layout.addWidget(self._sort_combo)

        self._sort_order_check = QCheckBox("降序")
        self._sort_order_check.setChecked(False)
        control_layout.addWidget(self._sort_order_check)

        control_layout.addStretch()

        layout.addWidget(control_group)

        portfolio_group = QGroupBox("账户总览")
        portfolio_layout = QHBoxLayout(portfolio_group)

        self._portfolio_total_value_label = QLabel("总市值: $0.00")
        self._portfolio_total_value_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        portfolio_layout.addWidget(self._portfolio_total_value_label)

        portfolio_layout.addSpacing(15)

        self._portfolio_total_cost_label = QLabel("总投入: $0.00")
        self._portfolio_total_cost_label.setStyleSheet("font-size: 14px;")
        portfolio_layout.addWidget(self._portfolio_total_cost_label)

        portfolio_layout.addSpacing(15)

        self._portfolio_total_pnl_label = QLabel("总盈亏: $0.00 (0.00%)")
        self._portfolio_total_pnl_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        portfolio_layout.addWidget(self._portfolio_total_pnl_label)

        portfolio_layout.addSpacing(15)

        self._portfolio_stocks_label = QLabel("持仓股票: 0")
        portfolio_layout.addWidget(self._portfolio_stocks_label)

        portfolio_layout.addStretch()

        self._last_update_label = QLabel("最后更新: --")
        portfolio_layout.addWidget(self._last_update_label)

        layout.addWidget(portfolio_group)

        stats_group = QGroupBox("行情统计")
        stats_layout = QHBoxLayout(stats_group)

        self._total_label = QLabel("股票总数: 0")
        stats_layout.addWidget(self._total_label)

        stats_layout.addSpacing(20)

        self._up_label = QLabel("上涨: 0")
        self._up_label.setStyleSheet("color: green; font-weight: bold;")
        stats_layout.addWidget(self._up_label)

        self._down_label = QLabel("下跌: 0")
        self._down_label.setStyleSheet("color: red; font-weight: bold;")
        stats_layout.addWidget(self._down_label)

        stats_layout.addSpacing(20)

        self._avg_change_label = QLabel("平均涨跌幅: 0.00%")
        stats_layout.addWidget(self._avg_change_label)

        stats_layout.addStretch()

        layout.addWidget(stats_group)

        self._table = QTableWidget()
        self._table.setColumnCount(16)
        self._table.setHorizontalHeaderLabels([
            "股票代码", "名称", "当前价格", "涨跌", "涨跌幅",
            "持仓数量", "成本价", "持仓市值", "盈亏金额", "盈亏百分比",
            "开盘价", "最高价", "最低价", "成交量", "市值", "货币"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)

        layout.addWidget(self._table)

    def _init_connections(self):
        self._add_btn.clicked.connect(self._add_stock)
        self._symbol_input.returnPressed.connect(self._add_stock)
        self._remove_btn.clicked.connect(self._remove_selected)
        self._refresh_btn.clicked.connect(self._refresh_data)
        self._sort_combo.currentIndexChanged.connect(self._sort_table)
        self._sort_order_check.stateChanged.connect(self._sort_table)
        self._watchlist_manager.add_update_callback(self._on_data_updated)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

    def _add_stock(self):
        symbol = self._symbol_input.text().strip().upper()
        if not symbol:
            QMessageBox.warning(self, "提示", "请输入股票代码")
            return

        if self._watchlist_manager.is_in_watchlist(symbol):
            QMessageBox.warning(self, "提示", f"股票 {symbol} 已在自选股中")
            return

        if self._watchlist_manager.add_stock(symbol):
            self._symbol_input.clear()
            QMessageBox.information(self, "成功", f"已添加股票 {symbol}")
        else:
            QMessageBox.warning(self, "失败", f"添加股票 {symbol} 失败")

    def _remove_selected(self):
        selected = self._table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要移除的股票")
            return

        rows = set(item.row() for item in selected)
        symbols_to_remove = []
        for row in rows:
            symbol_item = self._table.item(row, 0)
            if symbol_item:
                symbols_to_remove.append(symbol_item.text())

        if symbols_to_remove:
            reply = QMessageBox.question(
                self, "确认",
                f"确定要移除以下股票吗？\n{', '.join(symbols_to_remove)}",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                for symbol in symbols_to_remove:
                    self._watchlist_manager.remove_stock(symbol)

    def _refresh_data(self):
        self._watchlist_manager.refresh_all()

    def _on_data_updated(self):
        self._update_table()
        self._update_stats()

    def _update_table(self):
        sort_field_map = {
            "股票代码": "symbol",
            "名称": "name",
            "当前价格": "current_price",
            "涨跌幅": "change_percent",
            "成交量": "volume",
            "市值": "market_cap",
            "持仓数量": "quantity",
            "盈亏金额": "pnl_amount",
            "盈亏百分比": "pnl_percent",
            "持仓市值": "current_value"
        }
        sort_by = sort_field_map.get(self._sort_combo.currentText(), "symbol")
        ascending = not self._sort_order_check.isChecked()

        quotes = self._watchlist_manager.get_sorted_quotes(sort_by=sort_by, ascending=ascending)

        self._table.setRowCount(len(quotes))

        green_color = QColor(34, 197, 94)
        red_color = QColor(239, 68, 68)
        black_color = QColor(0, 0, 0)

        for row, quote in enumerate(quotes):
            self._table.setItem(row, 0, QTableWidgetItem(quote.get('symbol', '')))
            self._table.setItem(row, 1, QTableWidgetItem(quote.get('name', '')))

            current_price = quote.get('current_price', 0)
            current_item = QTableWidgetItem(f"{current_price:.2f}" if current_price else "--")
            self._table.setItem(row, 2, current_item)

            change = quote.get('change', 0)
            change_pct = quote.get('change_percent', 0)

            change_item = QTableWidgetItem(f"{change:+.2f}" if change else "--")
            change_pct_item = QTableWidgetItem(f"{change_pct:+.2f}%" if change_pct else "--")

            if change_pct > 0:
                change_color = green_color
            elif change_pct < 0:
                change_color = red_color
            else:
                change_color = black_color

            change_item.setForeground(change_color)
            change_pct_item.setForeground(change_color)
            current_item.setForeground(change_color)

            self._table.setItem(row, 3, change_item)
            self._table.setItem(row, 4, change_pct_item)

            position = quote.get('position', {})
            pnl = quote.get('pnl', {})

            quantity = position.get('quantity', 0)
            cost_price = position.get('cost_price', 0)
            current_value = pnl.get('current_value', 0)
            pnl_amount = pnl.get('pnl_amount', 0)
            pnl_percent = pnl.get('pnl_percent', 0)

            quantity_item = QTableWidgetItem(f"{quantity}" if quantity > 0 else "--")
            cost_price_item = QTableWidgetItem(f"${cost_price:.2f}" if cost_price > 0 else "--")
            current_value_item = QTableWidgetItem(f"${current_value:,.2f}" if current_value > 0 else "--")
            pnl_amount_item = QTableWidgetItem(f"${pnl_amount:+,.2f}" if quantity > 0 else "--")
            pnl_percent_item = QTableWidgetItem(f"{pnl_percent:+.2f}%" if quantity > 0 else "--")

            if quantity > 0 and current_value > 0:
                if pnl_amount > 0:
                    pnl_color = green_color
                elif pnl_amount < 0:
                    pnl_color = red_color
                else:
                    pnl_color = black_color

                current_value_item.setForeground(pnl_color)
                pnl_amount_item.setForeground(pnl_color)
                pnl_percent_item.setForeground(pnl_color)

            self._table.setItem(row, 5, quantity_item)
            self._table.setItem(row, 6, cost_price_item)
            self._table.setItem(row, 7, current_value_item)
            self._table.setItem(row, 8, pnl_amount_item)
            self._table.setItem(row, 9, pnl_percent_item)

            open_price = quote.get('open', 0)
            high = quote.get('high', 0)
            low = quote.get('low', 0)
            volume = quote.get('volume', 0)
            market_cap = quote.get('market_cap', 0)

            self._table.setItem(row, 10, QTableWidgetItem(f"{open_price:.2f}" if open_price else "--"))
            self._table.setItem(row, 11, QTableWidgetItem(f"{high:.2f}" if high else "--"))
            self._table.setItem(row, 12, QTableWidgetItem(f"{low:.2f}" if low else "--"))
            self._table.setItem(row, 13, QTableWidgetItem(self._format_number(volume)))
            self._table.setItem(row, 14, QTableWidgetItem(self._format_market_cap(market_cap)))
            self._table.setItem(row, 15, QTableWidgetItem(quote.get('currency', '')))

    def _update_stats(self):
        stats = self._watchlist_manager.get_total_value()

        self._total_label.setText(f"股票总数: {stats['total_stocks']}")
        self._up_label.setText(f"上涨: {stats['up_count']}")
        self._down_label.setText(f"下跌: {stats['down_count']}")

        avg_change = stats['avg_change_percent']
        self._avg_change_label.setText(f"平均涨跌幅: {avg_change:+.2f}%")

        portfolio = stats.get('portfolio', {})
        total_value = portfolio.get('total_value', 0)
        total_cost = portfolio.get('total_cost', 0)
        total_pnl = portfolio.get('total_pnl', 0)
        pnl_percent = portfolio.get('pnl_percent', 0)
        portfolio_stocks = portfolio.get('total_stocks', 0)

        self._portfolio_total_value_label.setText(f"总市值: ${total_value:,.2f}")
        self._portfolio_total_cost_label.setText(f"总投入: ${total_cost:,.2f}")
        
        pnl_text = f"总盈亏: ${total_pnl:+,.2f} ({pnl_percent:+.2f}%)"
        self._portfolio_total_pnl_label.setText(pnl_text)
        
        if total_pnl > 0:
            self._portfolio_total_pnl_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #22c55e;")
        elif total_pnl < 0:
            self._portfolio_total_pnl_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        else:
            self._portfolio_total_pnl_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        self._portfolio_stocks_label.setText(f"持仓股票: {portfolio_stocks}")

        last_update = self._watchlist_manager.last_update
        if last_update:
            self._last_update_label.setText(f"最后更新: {last_update.strftime('%H:%M:%S')}")

    def _sort_table(self):
        self._update_table()

    def _format_number(self, num: float) -> str:
        if num >= 1_000_000:
            return f"{num/1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num/1_000:.2f}K"
        return f"{num:.0f}" if num else "--"

    def _format_market_cap(self, cap: float) -> str:
        if cap >= 1_000_000_000_000:
            return f"{cap/1_000_000_000_000:.2f}T"
        elif cap >= 1_000_000_000:
            return f"{cap/1_000_000_000:.2f}B"
        elif cap >= 1_000_000:
            return f"{cap/1_000_000:.2f}M"
        return f"{cap:.0f}" if cap else "--"

    def _show_context_menu(self, pos):
        row = self._table.rowAt(pos.y())
        if row < 0:
            return

        symbol_item = self._table.item(row, 0)
        if not symbol_item:
            return

        symbol = symbol_item.text()

        menu = QMenu(self)
        edit_action = menu.addAction("编辑持仓")
        remove_action = menu.addAction("从自选股移除")

        action = menu.exec_(self._table.viewport().mapToGlobal(pos))

        if action == edit_action:
            self._edit_position(symbol)
        elif action == remove_action:
            self._remove_single_stock(symbol)

    def _edit_position(self, symbol: str):
        position = self._watchlist_manager.get_position(symbol)
        dialog = PositionEditDialog(symbol, position, self)
        if dialog.exec_() == QDialog.Accepted:
            quantity, cost_price = dialog.get_position_data()
            self._watchlist_manager.set_position(symbol, quantity, cost_price)

    def _remove_single_stock(self, symbol: str):
        reply = QMessageBox.question(
            self, "确认",
            f"确定要移除股票 {symbol} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._watchlist_manager.remove_stock(symbol)

    def refresh(self):
        self._refresh_data()


class PositionEditDialog(QDialog):
    def __init__(self, symbol: str, position=None, parent=None):
        super().__init__(parent)
        self._symbol = symbol
        self._position = position
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(f"编辑持仓 - {self._symbol}")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setRange(0, 1000000)
        self._quantity_spin.setSingleStep(1)
        self._quantity_spin.setSuffix(" 股")
        if self._position:
            self._quantity_spin.setValue(self._position.quantity)
        form_layout.addRow("持仓数量:", self._quantity_spin)

        self._cost_price_spin = QDoubleSpinBox()
        self._cost_price_spin.setRange(0.01, 1000000.0)
        self._cost_price_spin.setSingleStep(0.01)
        self._cost_price_spin.setDecimals(2)
        self._cost_price_spin.setPrefix("$")
        if self._position:
            self._cost_price_spin.setValue(self._position.cost_price if self._position.cost_price > 0 else 1.0)
        form_layout.addRow("买入成本价:", self._cost_price_spin)

        layout.addLayout(form_layout)

        if self._position and self._position.quantity > 0:
            total_cost = self._position.quantity * self._position.cost_price
            info_label = QLabel(f"当前持仓市值: {self._position.quantity} 股 x ${self._position.cost_price:.2f} = ${total_cost:,.2f}")
            info_label.setStyleSheet("color: #666; font-size: 12px;")
            layout.addWidget(info_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_position_data(self):
        return self._quantity_spin.value(), self._cost_price_spin.value()


class NewsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager()
        self._news_manager = NewsManager()
        self._watchlist_manager = WatchlistManager()
        self._init_ui()
        self._init_connections()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        control_group = QGroupBox("新闻设置")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("查看股票:"))
        self._symbol_combo = QComboBox()
        self._symbol_combo.setEditable(True)
        self._symbol_combo.setMaximumWidth(150)
        control_layout.addWidget(self._symbol_combo)

        control_layout.addWidget(QLabel("新闻数量:"))
        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 50)
        self._count_spin.setValue(self._config.news_count)
        control_layout.addWidget(self._count_spin)

        self._fetch_btn = QPushButton("获取新闻")
        control_layout.addWidget(self._fetch_btn)

        self._fetch_all_btn = QPushButton("获取所有自选股新闻")
        control_layout.addWidget(self._fetch_all_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._news_table = QTableWidget()
        self._news_table.setColumnCount(4)
        self._news_table.setHorizontalHeaderLabels([
            "股票代码", "标题", "发布时间", "来源"
        ])
        self._news_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._news_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._news_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._news_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._news_table.setColumnWidth(0, 80)
        self._news_table.setColumnWidth(2, 150)
        self._news_table.setColumnWidth(3, 100)
        self._news_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._news_table.setAlternatingRowColors(True)
        self._news_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._news_table.setSelectionMode(QTableWidget.SingleSelection)

        layout.addWidget(self._news_table)

        detail_group = QGroupBox("新闻详情")
        detail_layout = QVBoxLayout(detail_group)

        self._title_label = QLabel("标题: --")
        self._title_label.setWordWrap(True)
        self._title_label.setFont(QFont("", 10, QFont.Bold))
        detail_layout.addWidget(self._title_label)

        self._publisher_label = QLabel("来源: --")
        detail_layout.addWidget(self._publisher_label)

        self._date_label = QLabel("发布时间: --")
        detail_layout.addWidget(self._date_label)

        link_layout = QHBoxLayout()
        self._link_label = QLabel("链接: --")
        self._link_label.setOpenExternalLinks(True)
        link_layout.addWidget(self._link_label)

        self._open_link_btn = QPushButton("在浏览器中打开")
        self._open_link_btn.setEnabled(False)
        link_layout.addWidget(self._open_link_btn)

        detail_layout.addLayout(link_layout)
        layout.addWidget(detail_group)

        self._update_symbol_combo()

    def _init_connections(self):
        self._fetch_btn.clicked.connect(self._fetch_news)
        self._fetch_all_btn.clicked.connect(self._fetch_all_news)
        self._news_table.itemSelectionChanged.connect(self._on_news_selected)
        self._open_link_btn.clicked.connect(self._open_news_link)
        self._watchlist_manager.add_update_callback(self._update_symbol_combo)

    def _update_symbol_combo(self):
        current_text = self._symbol_combo.currentText()
        self._symbol_combo.clear()
        self._symbol_combo.addItems(self._watchlist_manager.watchlist)
        if current_text:
            index = self._symbol_combo.findText(current_text)
            if index >= 0:
                self._symbol_combo.setCurrentIndex(index)

    def _fetch_news(self):
        symbol = self._symbol_combo.currentText().strip().upper()
        if not symbol:
            QMessageBox.warning(self, "提示", "请输入或选择股票代码")
            return

        count = self._count_spin.value()
        news_list = self._news_manager.get_news_for_symbol(symbol, count, force_refresh=True)
        self._display_news(news_list)

    def _fetch_all_news(self):
        watchlist = self._watchlist_manager.watchlist
        if not watchlist:
            QMessageBox.warning(self, "提示", "自选股列表为空，请先添加股票")
            return

        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(watchlist))
        self._progress_bar.setValue(0)

        def progress_callback(current, total, symbol):
            self._progress_bar.setValue(current)

        news_list = self._news_manager.get_all_watchlist_news(
            self._count_spin.value(),
            progress_callback
        )

        self._progress_bar.setVisible(False)
        self._display_news(news_list)

    def _display_news(self, news_list: List[Dict[str, Any]]):
        self._news_table.setRowCount(len(news_list))

        for row, news in enumerate(news_list):
            self._news_table.setItem(row, 0, QTableWidgetItem(news.get('symbol', '')))

            title_item = QTableWidgetItem(news.get('title', ''))
            title_item.setData(Qt.UserRole, news)
            self._news_table.setItem(row, 1, title_item)

            self._news_table.setItem(row, 2, QTableWidgetItem(news.get('formatted_date', '')))
            self._news_table.setItem(row, 3, QTableWidgetItem(news.get('publisher', '')))

        self._current_news = None
        self._open_link_btn.setEnabled(False)

    def _on_news_selected(self):
        selected = self._news_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        title_item = self._news_table.item(row, 1)
        if not title_item:
            return

        news = title_item.data(Qt.UserRole)
        if not news:
            return

        self._current_news = news

        self._title_label.setText(f"标题: {news.get('title', '--')}")
        self._publisher_label.setText(f"来源: {news.get('publisher', '--')}")
        self._date_label.setText(f"发布时间: {news.get('formatted_date', '--')}")

        link = news.get('link', '')
        if link:
            self._link_label.setText(f'链接: <a href="{link}">{link}</a>')
            self._open_link_btn.setEnabled(True)
        else:
            self._link_label.setText("链接: --")
            self._open_link_btn.setEnabled(False)

    def _open_news_link(self):
        if self._current_news and 'link' in self._current_news:
            QDesktopServices.openUrl(QUrl(self._current_news['link']))

    def refresh(self):
        pass


class ScreenerThread(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(list)

    def __init__(self, screener_type: str, params: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._screener_type = screener_type
        self._params = params
        self._screener = StockScreener()

    def run(self):
        results = []

        def progress_callback(current, total, symbol):
            self.progress_signal.emit(current, total, symbol)

        try:
            if self._screener_type == 'recommendation':
                min_buy_ratio = self._params.get('min_buy_ratio', 0.5)
                limit = self._params.get('limit', 50)
                results = self._screener.screen_by_recommendation(
                    min_buy_ratio=min_buy_ratio,
                    progress_callback=progress_callback,
                    limit=limit
                )
            elif self._screener_type == 'price_target':
                min_upside = self._params.get('min_upside', 10.0)
                limit = self._params.get('limit', 50)
                results = self._screener.screen_by_price_target(
                    min_upside=min_upside,
                    progress_callback=progress_callback,
                    limit=limit
                )
            elif self._screener_type == 'insider':
                days = self._params.get('days', 30)
                limit = self._params.get('limit', 50)
                results = self._screener.screen_by_insider_buys(
                    days=days,
                    progress_callback=progress_callback,
                    limit=limit
                )
            elif self._screener_type == 'piotroski':
                min_fscore = self._params.get('min_fscore', 7)
                limit = self._params.get('limit', 50)
                results = self._screener.screen_by_piotroski_fscore(
                    min_fscore=min_fscore,
                    progress_callback=progress_callback,
                    limit=limit
                )
            elif self._screener_type == 'altman_zscore':
                min_zscore = self._params.get('min_zscore', 2.99)
                limit = self._params.get('limit', 50)
                results = self._screener.screen_by_altman_zscore(
                    min_zscore=min_zscore,
                    progress_callback=progress_callback,
                    limit=limit
                )
        except Exception as e:
            print(f"选股出错: {e}")

        self.finished_signal.emit(results)


class ScreenerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._screener = StockScreener()
        self._watchlist_manager = WatchlistManager()
        self._data_provider = DataProvider()
        self._screener_thread: Optional[ScreenerThread] = None
        self._init_ui()
        self._init_connections()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        screener_group = QGroupBox("选股工具")
        screener_layout = QVBoxLayout(screener_group)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("选股类型:"))

        self._screener_combo = QComboBox()
        self._screener_combo.addItems([
            "推荐评级选股",
            "目标价选股",
            "内部人买卖选股",
            "皮奥特罗斯基选股",
            "Altman Z-Score财务预警选股"
        ])
        self._screener_combo.setMaximumWidth(200)
        type_layout.addWidget(self._screener_combo)
        type_layout.addStretch()

        screener_layout.addLayout(type_layout)

        self._param_widgets = QWidget()
        param_layout = QVBoxLayout(self._param_widgets)
        param_layout.setContentsMargins(0, 0, 0, 0)

        self._rec_widget = self._create_rec_params()
        self._target_widget = self._create_target_params()
        self._insider_widget = self._create_insider_params()
        self._piotroski_widget = self._create_piotroski_params()
        self._altman_zscore_widget = self._create_altman_zscore_params()

        param_layout.addWidget(self._rec_widget)
        param_layout.addWidget(self._target_widget)
        param_layout.addWidget(self._insider_widget)
        param_layout.addWidget(self._piotroski_widget)
        param_layout.addWidget(self._altman_zscore_widget)

        screener_layout.addWidget(self._param_widgets)

        self._update_param_widgets()

        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("开始选股")
        self._run_btn.setMinimumHeight(40)
        btn_layout.addWidget(self._run_btn)

        self._add_to_watchlist_btn = QPushButton("添加选中到自选股")
        self._add_to_watchlist_btn.setEnabled(False)
        btn_layout.addWidget(self._add_to_watchlist_btn)

        btn_layout.addStretch()
        screener_layout.addLayout(btn_layout)

        layout.addWidget(screener_group)

        self._progress_label = QLabel("进度: 等待开始...")
        layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        layout.addWidget(self._progress_bar)

        self._result_table = QTableWidget()
        self._result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self._result_table)

    def _create_rec_params(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QLabel("最低买入比例:"))
        self._min_buy_ratio_spin = QSpinBox()
        self._min_buy_ratio_spin.setRange(10, 100)
        self._min_buy_ratio_spin.setValue(50)
        self._min_buy_ratio_spin.setSuffix("%")
        layout.addWidget(self._min_buy_ratio_spin)

        layout.addSpacing(20)
        layout.addWidget(QLabel("返回数量:"))
        self._rec_limit_spin = QSpinBox()
        self._rec_limit_spin.setRange(1, 250)
        self._rec_limit_spin.setValue(50)
        layout.addWidget(self._rec_limit_spin)

        layout.addStretch()
        return widget

    def _create_target_params(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QLabel("最低上涨空间:"))
        self._min_upside_spin = QSpinBox()
        self._min_upside_spin.setRange(1, 200)
        self._min_upside_spin.setValue(10)
        self._min_upside_spin.setSuffix("%")
        layout.addWidget(self._min_upside_spin)

        layout.addSpacing(20)
        layout.addWidget(QLabel("返回数量:"))
        self._target_limit_spin = QSpinBox()
        self._target_limit_spin.setRange(1, 250)
        self._target_limit_spin.setValue(50)
        layout.addWidget(self._target_limit_spin)

        layout.addStretch()
        return widget

    def _create_insider_params(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QLabel("检查天数:"))
        self._insider_days_spin = QSpinBox()
        self._insider_days_spin.setRange(1, 365)
        self._insider_days_spin.setValue(30)
        self._insider_days_spin.setSuffix(" 天")
        layout.addWidget(self._insider_days_spin)

        layout.addSpacing(20)
        layout.addWidget(QLabel("返回数量:"))
        self._insider_limit_spin = QSpinBox()
        self._insider_limit_spin.setRange(1, 250)
        self._insider_limit_spin.setValue(50)
        layout.addWidget(self._insider_limit_spin)

        layout.addStretch()
        return widget

    def _create_piotroski_params(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QLabel("最低F-Score:"))
        self._min_fscore_spin = QSpinBox()
        self._min_fscore_spin.setRange(1, 9)
        self._min_fscore_spin.setValue(7)
        layout.addWidget(self._min_fscore_spin)

        layout.addSpacing(20)
        layout.addWidget(QLabel("返回数量:"))
        self._piotroski_limit_spin = QSpinBox()
        self._piotroski_limit_spin.setRange(1, 250)
        self._piotroski_limit_spin.setValue(50)
        layout.addWidget(self._piotroski_limit_spin)

        layout.addStretch()
        return widget

    def _create_altman_zscore_params(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QLabel("最低Z-Score:"))
        from PyQt5.QtWidgets import QDoubleSpinBox
        self._min_zscore_spin = QDoubleSpinBox()
        self._min_zscore_spin.setRange(-10.0, 10.0)
        self._min_zscore_spin.setSingleStep(0.01)
        self._min_zscore_spin.setValue(2.99)
        self._min_zscore_spin.setDecimals(2)
        layout.addWidget(self._min_zscore_spin)

        layout.addSpacing(20)
        layout.addWidget(QLabel("返回数量:"))
        self._altman_zscore_limit_spin = QSpinBox()
        self._altman_zscore_limit_spin.setRange(1, 250)
        self._altman_zscore_limit_spin.setValue(50)
        layout.addWidget(self._altman_zscore_limit_spin)

        layout.addStretch()
        return widget

    def _update_param_widgets(self):
        index = self._screener_combo.currentIndex()
        self._rec_widget.setVisible(index == 0)
        self._target_widget.setVisible(index == 1)
        self._insider_widget.setVisible(index == 2)
        self._piotroski_widget.setVisible(index == 3)
        self._altman_zscore_widget.setVisible(index == 4)

    def _init_connections(self):
        self._screener_combo.currentIndexChanged.connect(self._update_param_widgets)
        self._run_btn.clicked.connect(self._run_screener)
        self._add_to_watchlist_btn.clicked.connect(self._add_selected_to_watchlist)

    def _run_screener(self):
        if self._screener_thread and self._screener_thread.isRunning():
            QMessageBox.warning(self, "提示", "选股正在进行中，请稍候")
            return

        index = self._screener_combo.currentIndex()
        screener_type = ''
        params = {}

        if index == 0:
            screener_type = 'recommendation'
            params = {
                'min_buy_ratio': self._min_buy_ratio_spin.value() / 100.0,
                'limit': self._rec_limit_spin.value()
            }
        elif index == 1:
            screener_type = 'price_target'
            params = {
                'min_upside': float(self._min_upside_spin.value()),
                'limit': self._target_limit_spin.value()
            }
        elif index == 2:
            screener_type = 'insider'
            params = {
                'days': self._insider_days_spin.value(),
                'limit': self._insider_limit_spin.value()
            }
        elif index == 3:
            screener_type = 'piotroski'
            params = {
                'min_fscore': self._min_fscore_spin.value(),
                'limit': self._piotroski_limit_spin.value()
            }
        elif index == 4:
            screener_type = 'altman_zscore'
            params = {
                'min_zscore': self._min_zscore_spin.value(),
                'limit': self._altman_zscore_limit_spin.value()
            }

        self._run_btn.setEnabled(False)
        self._progress_bar.setRange(0, 0)

        self._screener_thread = ScreenerThread(screener_type, params)
        self._screener_thread.progress_signal.connect(self._on_progress)
        self._screener_thread.finished_signal.connect(self._on_screener_finished)
        self._screener_thread.start()

    def _on_progress(self, current: int, total: int, symbol: str):
        self._progress_label.setText(f"进度: 正在检查 {symbol} ({current}/{total})")
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)

    def _on_screener_finished(self, results: List[Dict[str, Any]]):
        self._run_btn.setEnabled(True)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_label.setText(f"进度: 完成，找到 {len(results)} 只股票")

        index = self._screener_combo.currentIndex()
        if index == 0:
            self._display_rec_results(results)
        elif index == 1:
            self._display_target_results(results)
        elif index == 2:
            self._display_insider_results(results)
        elif index == 3:
            self._display_piotroski_results(results)
        elif index == 4:
            self._display_altman_zscore_results(results)

        self._add_to_watchlist_btn.setEnabled(len(results) > 0)

    def _display_rec_results(self, results: List[Dict[str, Any]]):
        self._result_table.clear()
        self._result_table.setColumnCount(11)
        self._result_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "StrongBuy", "Buy", "Hold", "Sell",
            "StrongSell", "买入比例", "当前价格", "涨跌幅", "在自选股"
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._result_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self._result_table.setItem(row, 0, QTableWidgetItem(item.get('symbol', '')))
            self._result_table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))
            self._result_table.setItem(row, 2, QTableWidgetItem(str(item.get('strongBuy', 0))))
            self._result_table.setItem(row, 3, QTableWidgetItem(str(item.get('buy', 0))))
            self._result_table.setItem(row, 4, QTableWidgetItem(str(item.get('hold', 0))))
            self._result_table.setItem(row, 5, QTableWidgetItem(str(item.get('sell', 0))))
            self._result_table.setItem(row, 6, QTableWidgetItem(str(item.get('strongSell', 0))))
            self._result_table.setItem(row, 7, QTableWidgetItem(f"{item.get('buy_ratio', 0):.1f}%"))

            current_price = item.get('current_price', 0)
            change_pct = item.get('change_percent', 0)

            price_item = QTableWidgetItem(f"{current_price:.2f}" if current_price else "--")
            change_item = QTableWidgetItem(f"{change_pct:+.2f}%" if change_pct else "--")

            if change_pct > 0:
                color = QColor(0, 150, 0)
            elif change_pct < 0:
                color = QColor(200, 0, 0)
            else:
                color = QColor(0, 0, 0)

            price_item.setForeground(color)
            change_item.setForeground(color)

            self._result_table.setItem(row, 8, price_item)
            self._result_table.setItem(row, 9, change_item)

            in_watchlist = self._watchlist_manager.is_in_watchlist(item.get('symbol', ''))
            watchlist_item = QTableWidgetItem("是" if in_watchlist else "否")
            if in_watchlist:
                watchlist_item.setForeground(QColor(0, 150, 0))
            self._result_table.setItem(row, 10, watchlist_item)

    def _display_target_results(self, results: List[Dict[str, Any]]):
        self._result_table.clear()
        self._result_table.setColumnCount(9)
        self._result_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "当前价格", "目标均价", "上涨空间",
            "目标最高", "目标最低", "涨跌幅", "在自选股"
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._result_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self._result_table.setItem(row, 0, QTableWidgetItem(item.get('symbol', '')))
            self._result_table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))

            current_price = item.get('current_price', 0)
            change_pct = item.get('change_percent', 0)

            price_item = QTableWidgetItem(f"{current_price:.2f}" if current_price else "--")
            change_item = QTableWidgetItem(f"{change_pct:+.2f}%" if change_pct else "--")

            if change_pct > 0:
                color = QColor(0, 150, 0)
            elif change_pct < 0:
                color = QColor(200, 0, 0)
            else:
                color = QColor(0, 0, 0)

            price_item.setForeground(color)
            change_item.setForeground(color)

            self._result_table.setItem(row, 2, price_item)
            self._result_table.setItem(row, 3, QTableWidgetItem(f"{item.get('target_mean', 0):.2f}"))

            upside = item.get('upside_potential', 0)
            upside_item = QTableWidgetItem(f"{upside:+.2f}%")
            upside_item.setForeground(QColor(0, 150, 0))
            self._result_table.setItem(row, 4, upside_item)

            self._result_table.setItem(row, 5, QTableWidgetItem(f"{item.get('target_high', 0):.2f}"))
            self._result_table.setItem(row, 6, QTableWidgetItem(f"{item.get('target_low', 0):.2f}"))
            self._result_table.setItem(row, 7, change_item)

            in_watchlist = self._watchlist_manager.is_in_watchlist(item.get('symbol', ''))
            watchlist_item = QTableWidgetItem("是" if in_watchlist else "否")
            if in_watchlist:
                watchlist_item.setForeground(QColor(0, 150, 0))
            self._result_table.setItem(row, 8, watchlist_item)

    def _display_insider_results(self, results: List[Dict[str, Any]]):
        self._result_table.clear()
        self._result_table.setColumnCount(10)
        self._result_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "当前价格", "涨跌幅", "交易次数",
            "总股数", "总金额", "最新日期", "内部人", "在自选股"
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._result_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self._result_table.setItem(row, 0, QTableWidgetItem(item.get('symbol', '')))
            self._result_table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))

            current_price = item.get('current_price', 0)
            change_pct = item.get('change_percent', 0)

            price_item = QTableWidgetItem(f"{current_price:.2f}" if current_price else "--")
            change_item = QTableWidgetItem(f"{change_pct:+.2f}%" if change_pct else "--")

            if change_pct > 0:
                color = QColor(0, 150, 0)
            elif change_pct < 0:
                color = QColor(200, 0, 0)
            else:
                color = QColor(0, 0, 0)

            price_item.setForeground(color)
            change_item.setForeground(color)

            self._result_table.setItem(row, 2, price_item)
            self._result_table.setItem(row, 3, change_item)

            self._result_table.setItem(row, 4, QTableWidgetItem(str(item.get('transaction_count', 0))))
            self._result_table.setItem(row, 5, QTableWidgetItem(self._format_number(item.get('total_shares', 0))))
            self._result_table.setItem(row, 6, QTableWidgetItem(self._format_market_cap(item.get('total_value', 0))))
            self._result_table.setItem(row, 7, QTableWidgetItem(item.get('latest_date', '')))
            self._result_table.setItem(row, 8, QTableWidgetItem(item.get('latest_insider', '')))

            in_watchlist = self._watchlist_manager.is_in_watchlist(item.get('symbol', ''))
            watchlist_item = QTableWidgetItem("是" if in_watchlist else "否")
            if in_watchlist:
                watchlist_item.setForeground(QColor(0, 150, 0))
            self._result_table.setItem(row, 9, watchlist_item)

    def _display_piotroski_results(self, results: List[Dict[str, Any]]):
        self._result_table.clear()
        self._result_table.setColumnCount(12)
        self._result_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "F-Score总分", "ROA", "经营现金流",
            "杠杆变化", "流动比率变化", "毛利率变化", "资产周转率变化",
            "当前价格", "涨跌幅", "在自选股"
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._result_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self._result_table.setItem(row, 0, QTableWidgetItem(item.get('symbol', '')))
            self._result_table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))

            fscore_total = item.get('fscore_total', 0)
            fscore_item = QTableWidgetItem(str(fscore_total))
            if fscore_total >= 8:
                fscore_item.setForeground(QColor(0, 150, 0))
            elif fscore_total >= 6:
                fscore_item.setForeground(QColor(0, 100, 200))
            else:
                fscore_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 2, fscore_item)

            current_roa = item.get('current_roa', None)
            if current_roa is not None:
                roa_item = QTableWidgetItem(f"{current_roa*100:.2f}%")
                if current_roa > 0:
                    roa_item.setForeground(QColor(0, 150, 0))
                else:
                    roa_item.setForeground(QColor(200, 0, 0))
                self._result_table.setItem(row, 3, roa_item)
            else:
                self._result_table.setItem(row, 3, QTableWidgetItem("--"))

            current_cfo = item.get('current_cfo', None)
            if current_cfo is not None:
                self._result_table.setItem(row, 4, QTableWidgetItem(self._format_market_cap(current_cfo)))
            else:
                self._result_table.setItem(row, 4, QTableWidgetItem("--"))

            leverage_change = item.get('leverage_change', '未知')
            leverage_item = QTableWidgetItem(leverage_change)
            if leverage_change == '下降':
                leverage_item.setForeground(QColor(0, 150, 0))
            elif leverage_change == '上升':
                leverage_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 5, leverage_item)

            current_ratio_change = item.get('current_ratio_change', '未知')
            cr_item = QTableWidgetItem(current_ratio_change)
            if current_ratio_change == '上升':
                cr_item.setForeground(QColor(0, 150, 0))
            elif current_ratio_change == '下降':
                cr_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 6, cr_item)

            gross_margin_change = item.get('gross_margin_change', '未知')
            gm_item = QTableWidgetItem(gross_margin_change)
            if gross_margin_change == '上升':
                gm_item.setForeground(QColor(0, 150, 0))
            elif gross_margin_change == '下降':
                gm_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 7, gm_item)

            asset_turnover_change = item.get('asset_turnover_change', '未知')
            at_item = QTableWidgetItem(asset_turnover_change)
            if asset_turnover_change == '上升':
                at_item.setForeground(QColor(0, 150, 0))
            elif asset_turnover_change == '下降':
                at_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 8, at_item)

            current_price = item.get('current_price', 0)
            change_pct = item.get('change_percent', 0)

            price_item = QTableWidgetItem(f"{current_price:.2f}" if current_price else "--")
            change_item = QTableWidgetItem(f"{change_pct:+.2f}%" if change_pct else "--")

            if change_pct > 0:
                color = QColor(0, 150, 0)
            elif change_pct < 0:
                color = QColor(200, 0, 0)
            else:
                color = QColor(0, 0, 0)

            price_item.setForeground(color)
            change_item.setForeground(color)

            self._result_table.setItem(row, 9, price_item)
            self._result_table.setItem(row, 10, change_item)

            in_watchlist = self._watchlist_manager.is_in_watchlist(item.get('symbol', ''))
            watchlist_item = QTableWidgetItem("是" if in_watchlist else "否")
            if in_watchlist:
                watchlist_item.setForeground(QColor(0, 150, 0))
            self._result_table.setItem(row, 11, watchlist_item)

    def _display_altman_zscore_results(self, results: List[Dict[str, Any]]):
        self._result_table.clear()
        self._result_table.setColumnCount(12)
        self._result_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "Z值", "X1营运资金比", "X2留存收益比",
            "X3EBIT比", "X4市值负债比", "X5资产周转率", "财务区域",
            "当前价格", "涨跌幅", "在自选股"
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._result_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self._result_table.setItem(row, 0, QTableWidgetItem(item.get('symbol', '')))
            self._result_table.setItem(row, 1, QTableWidgetItem(item.get('name', '')))

            zscore = item.get('zscore', 0)
            zscore_item = QTableWidgetItem(f"{zscore:.4f}")
            
            zone_code = item.get('zone_code', '')
            if zone_code == 'safe':
                zscore_item.setForeground(QColor(0, 150, 0))
            elif zone_code == 'grey':
                zscore_item.setForeground(QColor(0, 100, 200))
            else:
                zscore_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 2, zscore_item)

            x1 = item.get('x1', 0)
            x1_item = QTableWidgetItem(f"{x1:.4f}")
            self._result_table.setItem(row, 3, x1_item)

            x2 = item.get('x2', 0)
            x2_item = QTableWidgetItem(f"{x2:.4f}")
            self._result_table.setItem(row, 4, x2_item)

            x3 = item.get('x3', 0)
            x3_item = QTableWidgetItem(f"{x3:.4f}")
            self._result_table.setItem(row, 5, x3_item)

            x4 = item.get('x4', 0)
            x4_item = QTableWidgetItem(f"{x4:.4f}")
            self._result_table.setItem(row, 6, x4_item)

            x5 = item.get('x5', 0)
            x5_item = QTableWidgetItem(f"{x5:.4f}")
            self._result_table.setItem(row, 7, x5_item)

            zone = item.get('zone', '未知')
            zone_item = QTableWidgetItem(zone)
            if zone_code == 'safe':
                zone_item.setForeground(QColor(0, 150, 0))
            elif zone_code == 'grey':
                zone_item.setForeground(QColor(0, 100, 200))
            else:
                zone_item.setForeground(QColor(200, 0, 0))
            self._result_table.setItem(row, 8, zone_item)

            current_price = item.get('current_price', 0)
            change_pct = item.get('change_percent', 0)

            price_item = QTableWidgetItem(f"{current_price:.2f}" if current_price else "--")
            change_item = QTableWidgetItem(f"{change_pct:+.2f}%" if change_pct else "--")

            if change_pct > 0:
                color = QColor(0, 150, 0)
            elif change_pct < 0:
                color = QColor(200, 0, 0)
            else:
                color = QColor(0, 0, 0)

            price_item.setForeground(color)
            change_item.setForeground(color)

            self._result_table.setItem(row, 9, price_item)
            self._result_table.setItem(row, 10, change_item)

            in_watchlist = self._watchlist_manager.is_in_watchlist(item.get('symbol', ''))
            watchlist_item = QTableWidgetItem("是" if in_watchlist else "否")
            if in_watchlist:
                watchlist_item.setForeground(QColor(0, 150, 0))
            self._result_table.setItem(row, 11, watchlist_item)

    def _format_number(self, num: float) -> str:
        if num >= 1_000_000:
            return f"{num/1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num/1_000:.2f}K"
        return f"{num:.0f}" if num else "--"

    def _format_market_cap(self, cap: float) -> str:
        if cap >= 1_000_000_000_000:
            return f"{cap/1_000_000_000_000:.2f}T"
        elif cap >= 1_000_000_000:
            return f"{cap/1_000_000_000:.2f}B"
        elif cap >= 1_000_000:
            return f"{cap/1_000_000:.2f}M"
        return f"{cap:.0f}" if cap else "--"

    def _add_selected_to_watchlist(self):
        selected = self._result_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要添加的股票")
            return

        rows = set(item.row() for item in selected)
        added = []
        already_in = []

        for row in rows:
            symbol_item = self._result_table.item(row, 0)
            if symbol_item:
                symbol = symbol_item.text()
                if self._watchlist_manager.is_in_watchlist(symbol):
                    already_in.append(symbol)
                else:
                    if self._watchlist_manager.add_stock(symbol):
                        added.append(symbol)

        messages = []
        if added:
            messages.append(f"已添加: {', '.join(added)}")
        if already_in:
            messages.append(f"已在自选股中: {', '.join(already_in)}")

        if messages:
            QMessageBox.information(self, "结果", "\n".join(messages))

    def refresh(self):
        pass


class SettingsTab(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager()
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        general_group = QGroupBox("常规设置")
        general_layout = QVBoxLayout(general_group)

        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(QLabel("数据刷新间隔 (秒):"))
        self._refresh_interval_spin = QSpinBox()
        self._refresh_interval_spin.setRange(10, 3600)
        self._refresh_interval_spin.setValue(60)
        self._refresh_interval_spin.setSuffix(" 秒")
        refresh_layout.addWidget(self._refresh_interval_spin)
        refresh_layout.addStretch()
        general_layout.addLayout(refresh_layout)

        auto_layout = QHBoxLayout()
        self._auto_refresh_check = QCheckBox("启用自动刷新")
        auto_layout.addWidget(self._auto_refresh_check)
        auto_layout.addStretch()
        general_layout.addLayout(auto_layout)

        layout.addWidget(general_group)

        news_group = QGroupBox("新闻设置")
        news_layout = QVBoxLayout(news_group)

        news_count_layout = QHBoxLayout()
        news_count_layout.addWidget(QLabel("默认获取新闻数量:"))
        self._news_count_spin = QSpinBox()
        self._news_count_spin.setRange(1, 50)
        self._news_count_spin.setValue(10)
        news_count_layout.addWidget(self._news_count_spin)
        news_count_layout.addStretch()
        news_layout.addLayout(news_count_layout)

        layout.addWidget(news_group)

        screener_group = QGroupBox("选股设置")
        screener_layout = QVBoxLayout(screener_group)

        screener_limit_layout = QHBoxLayout()
        screener_limit_layout.addWidget(QLabel("默认选股返回数量:"))
        self._screener_limit_spin = QSpinBox()
        self._screener_limit_spin.setRange(1, 250)
        self._screener_limit_spin.setValue(50)
        screener_limit_layout.addWidget(self._screener_limit_spin)
        screener_limit_layout.addStretch()
        screener_layout.addLayout(screener_limit_layout)

        layout.addWidget(screener_group)

        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton("保存设置")
        self._save_btn.setMinimumHeight(40)
        btn_layout.addWidget(self._save_btn)

        self._reset_btn = QPushButton("恢复默认")
        self._reset_btn.setMinimumHeight(40)
        btn_layout.addWidget(self._reset_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        self._save_btn.clicked.connect(self._save_settings)
        self._reset_btn.clicked.connect(self._reset_settings)

    def _load_settings(self):
        self._refresh_interval_spin.setValue(self._config.refresh_interval)
        self._auto_refresh_check.setChecked(self._config.auto_refresh)
        self._news_count_spin.setValue(self._config.news_count)
        self._screener_limit_spin.setValue(self._config.screener_limit)

    def _save_settings(self):
        self._config.refresh_interval = self._refresh_interval_spin.value()
        self._config.auto_refresh = self._auto_refresh_check.isChecked()
        self._config.news_count = self._news_count_spin.value()
        self._config.screener_limit = self._screener_limit_spin.value()

        self.settings_changed.emit()
        QMessageBox.information(self, "成功", "设置已保存")

    def _reset_settings(self):
        reply = QMessageBox.question(
            self, "确认",
            "确定要恢复默认设置吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._config.refresh_interval = 60
            self._config.auto_refresh = True
            self._config.news_count = 10
            self._config.screener_limit = 25
            self._load_settings()
            self.settings_changed.emit()
            QMessageBox.information(self, "成功", "已恢复默认设置")

    def refresh(self):
        self._load_settings()


class MarketIndicatorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._market_indicators = MarketIndicators()
        self._refresh_thread = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        control_group = QGroupBox("操作")
        control_layout = QHBoxLayout(control_group)

        self._refresh_btn = QPushButton("刷新指标数据")
        self._refresh_btn.setMinimumHeight(35)
        self._refresh_btn.clicked.connect(self._refresh_indicators)
        control_layout.addWidget(self._refresh_btn)

        self._force_refresh_btn = QPushButton("强制刷新 (忽略缓存)")
        self._force_refresh_btn.setMinimumHeight(35)
        self._force_refresh_btn.clicked.connect(lambda: self._refresh_indicators(force=True))
        control_layout.addWidget(self._force_refresh_btn)

        self._cache_info_label = QLabel("缓存有效期: 24小时")
        self._cache_info_label.setStyleSheet("color: #666; font-size: 12px;")
        control_layout.addSpacing(20)
        control_layout.addWidget(self._cache_info_label)

        control_layout.addStretch()

        layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("点击刷新按钮获取最新指标数据")
        self._status_label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self._status_label)

        indicators_layout = QVBoxLayout()
        
        self._buffett_group = self._create_indicator_group("巴菲特指标 (Buffett Indicator)")
        indicators_layout.addWidget(self._buffett_group)

        self._shiller_cape_group = self._create_indicator_group("席勒CAPE (Shiller PE Ratio)")
        indicators_layout.addWidget(self._shiller_cape_group)

        self._sp500_pe_group = self._create_indicator_group("标普500 PE分位数")
        indicators_layout.addWidget(self._sp500_pe_group)

        layout.addLayout(indicators_layout, 1)

    def _create_indicator_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        info_layout = QHBoxLayout()
        
        current_layout = QVBoxLayout()
        current_label = QLabel("当前值:")
        current_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        current_layout.addWidget(current_label)
        
        self._create_value_widget(current_layout, f"{title}_current")
        info_layout.addLayout(current_layout)

        info_layout.addSpacing(20)

        status_layout = QVBoxLayout()
        status_label = QLabel("估值状态:")
        status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        status_layout.addWidget(status_label)
        
        self._create_value_widget(status_layout, f"{title}_status")
        info_layout.addLayout(status_layout)

        info_layout.addSpacing(20)

        percentile_layout = QVBoxLayout()
        percentile_label = QLabel("历史百分位:")
        percentile_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        percentile_layout.addWidget(percentile_label)
        
        self._create_value_widget(percentile_layout, f"{title}_percentile")
        info_layout.addLayout(percentile_layout)

        info_layout.addStretch()

        layout.addLayout(info_layout)

        stats_layout = QHBoxLayout()
        
        min_layout = QVBoxLayout()
        min_label = QLabel("历史最低:")
        min_label.setStyleSheet("font-size: 11px; color: #666;")
        min_layout.addWidget(min_label)
        self._create_value_widget(min_layout, f"{title}_min", small=True)
        stats_layout.addLayout(min_layout)

        stats_layout.addSpacing(15)

        avg_layout = QVBoxLayout()
        avg_label = QLabel("历史平均:")
        avg_label.setStyleSheet("font-size: 11px; color: #666;")
        avg_layout.addWidget(avg_label)
        self._create_value_widget(avg_layout, f"{title}_avg", small=True)
        stats_layout.addLayout(avg_layout)

        stats_layout.addSpacing(15)

        max_layout = QVBoxLayout()
        max_label = QLabel("历史最高:")
        max_label.setStyleSheet("font-size: 11px; color: #666;")
        max_layout.addWidget(max_label)
        self._create_value_widget(max_layout, f"{title}_max", small=True)
        stats_layout.addLayout(max_layout)

        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        desc_label = QLabel("")
        desc_label.setStyleSheet("font-size: 11px; color: #888; font-style: italic;")
        desc_label.setWordWrap(True)
        desc_label.setObjectName(f"{title}_desc")
        layout.addWidget(desc_label)

        return group

    def _create_value_widget(self, layout: QVBoxLayout, name: str, small: bool = False):
        value_label = QLabel("--")
        if small:
            value_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        else:
            value_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        value_label.setObjectName(name)
        layout.addWidget(value_label)

    def _refresh_indicators(self, force: bool = False):
        if self._refresh_thread and self._refresh_thread.isRunning():
            QMessageBox.warning(self, "提示", "指标刷新正在进行中，请稍候...")
            return

        self._refresh_btn.setEnabled(False)
        self._force_refresh_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        
        if force:
            self._status_label.setText("正在强制刷新指标数据 (忽略缓存)...")
        else:
            self._status_label.setText("正在获取指标数据...")

        self._refresh_thread = MarketIndicatorRefreshThread(
            self._market_indicators, force
        )
        self._refresh_thread.finished_signal.connect(self._on_refresh_finished)
        self._refresh_thread.error_signal.connect(self._on_refresh_error)
        self._refresh_thread.start()

    def _on_refresh_finished(self, results: Dict[str, Any]):
        self._refresh_btn.setEnabled(True)
        self._force_refresh_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"指标数据刷新完成 - {datetime.now().strftime('%H:%M:%S')}")

        if results.get('buffett'):
            self._display_indicator(self._buffett_group, results['buffett'])
        
        if results.get('shiller_cape'):
            self._display_indicator(self._shiller_cape_group, results['shiller_cape'])
        
        if results.get('sp500_pe'):
            self._display_indicator(self._sp500_pe_group, results['sp500_pe'])

    def _on_refresh_error(self, error_msg: str):
        self._refresh_btn.setEnabled(True)
        self._force_refresh_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"刷新出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"刷新指标数据时出错:\n{error_msg}")

    def _display_indicator(self, group: QGroupBox, result: Dict[str, Any]):
        title = group.title()
        
        current_widget = group.findChild(QLabel, f"{title}_current")
        if current_widget and result.get('current_value') is not None:
            current_widget.setText(f"{result['current_value']:.2f}")

        status_widget = group.findChild(QLabel, f"{title}_status")
        if status_widget and result.get('status'):
            status_widget.setText(result['status'])
            
            color = result.get('status_color', '')
            if color == 'green':
                status_widget.setStyleSheet("font-size: 18px; font-weight: bold; color: #22c55e;")
            elif color == 'blue':
                status_widget.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
            elif color == 'red':
                status_widget.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef4444;")
            else:
                status_widget.setStyleSheet("font-size: 18px; font-weight: bold;")

        percentile_widget = group.findChild(QLabel, f"{title}_percentile")
        if percentile_widget and result.get('percentile') is not None:
            percentile_widget.setText(f"{result['percentile']:.1f}%")

        min_widget = group.findChild(QLabel, f"{title}_min")
        if min_widget and result.get('min_value') is not None:
            min_widget.setText(f"{result['min_value']:.2f}")

        avg_widget = group.findChild(QLabel, f"{title}_avg")
        if avg_widget and result.get('avg_value') is not None:
            avg_widget.setText(f"{result['avg_value']:.2f}")

        max_widget = group.findChild(QLabel, f"{title}_max")
        if max_widget and result.get('max_value') is not None:
            max_widget.setText(f"{result['max_value']:.2f}")

        desc_widget = group.findChild(QLabel, f"{title}_desc")
        if desc_widget and result.get('description'):
            desc_widget.setText(result['description'])

    def refresh(self):
        self._refresh_indicators(force=False)


class MarketIndicatorRefreshThread(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, indicators: MarketIndicators, force_refresh: bool = False):
        super().__init__()
        self._indicators = indicators
        self._force_refresh = force_refresh

    def run(self):
        try:
            results = self._indicators.get_all_indicators(force_refresh=self._force_refresh)
            
            formatted_results = {}
            for key, result in results.items():
                if result:
                    formatted_results[key] = {
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
            
            self.finished_signal.emit(formatted_results)
            
        except Exception as e:
            self.error_signal.emit(str(e))


class TechnicalAnalysisTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._watchlist_manager = WatchlistManager()
        self._technical_analyzer = TechnicalAnalyzer()
        self._analysis_thread: Optional[TechnicalAnalysisThread] = None
        self._current_data: Optional[Dict[str, Any]] = None
        self._init_ui()
        self._load_watchlist()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("选择股票:"))
        self._stock_combo = QComboBox()
        self._stock_combo.setEditable(True)
        self._stock_combo.setMinimumWidth(200)
        control_layout.addWidget(self._stock_combo)

        control_layout.addWidget(QLabel("时间周期:"))
        self._period_combo = QComboBox()
        self._period_combo.addItems(["1个月", "3个月", "6个月", "1年", "2年", "5年"])
        self._period_combo.setCurrentIndex(3)
        control_layout.addWidget(self._period_combo)

        control_layout.addWidget(QLabel("数据频率:"))
        self._interval_combo = QComboBox()
        self._interval_combo.addItems(["日线", "周线", "月线"])
        self._interval_combo.setCurrentIndex(0)
        control_layout.addWidget(self._interval_combo)

        self._analyze_btn = QPushButton("开始分析")
        self._analyze_btn.setMinimumHeight(35)
        self._analyze_btn.clicked.connect(self._analyze_current_stock)
        control_layout.addWidget(self._analyze_btn)

        self._refresh_btn = QPushButton("刷新自选股列表")
        self._refresh_btn.setMinimumHeight(35)
        self._refresh_btn.clicked.connect(self._load_watchlist)
        control_layout.addWidget(self._refresh_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("请选择股票并开始分析")
        self._status_label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self._status_label)

        main_splitter = QSplitter(Qt.Vertical)

        top_splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        self._price_chart = PriceChartWidget()
        self._price_chart.set_title("价格走势与均线")
        left_layout.addWidget(self._price_chart, 1)

        top_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        self._signal_display = SignalDisplayWidget()
        right_layout.addWidget(self._signal_display, 1)

        top_splitter.addWidget(right_widget)

        top_splitter.setSizes([700, 300])

        main_splitter.addWidget(top_splitter)

        indicator_group = QGroupBox("技术指标")
        indicator_layout = QVBoxLayout(indicator_group)
        indicator_layout.setContentsMargins(5, 5, 5, 5)
        indicator_layout.setSpacing(5)

        indicator_control_layout = QHBoxLayout()
        indicator_control_layout.addWidget(QLabel("选择指标:"))
        
        self._indicator_combo = QComboBox()
        self._indicator_combo.addItems([
            "MACD", "RSI", "布林带", "KDJ", "成交量"
        ])
        self._indicator_combo.currentIndexChanged.connect(self._on_indicator_changed)
        indicator_control_layout.addWidget(self._indicator_combo)
        indicator_control_layout.addStretch()
        indicator_layout.addLayout(indicator_control_layout)

        self._indicator_chart = PriceChartWidget()
        self._indicator_chart.set_title("MACD")
        indicator_layout.addWidget(self._indicator_chart, 1)

        main_splitter.addWidget(indicator_group)

        main_splitter.setSizes([500, 400])

        layout.addWidget(main_splitter, 1)

        self._latest_group = QGroupBox("最新指标值")
        latest_layout = QHBoxLayout(self._latest_group)
        latest_layout.setSpacing(20)

        self._latest_labels = {}
        indicators = [
            ("RSI", "rsi"),
            ("MACD", "macd"),
            ("信号线", "macd_signal"),
            ("柱状图", "macd_histogram"),
            ("K值", "k"),
            ("D值", "d"),
            ("J值", "j"),
            ("%b", "percent_b")
        ]

        for label_text, key in indicators:
            group = QVBoxLayout()
            label = QLabel(label_text + ":")
            label.setStyleSheet("font-weight: bold; color: #666;")
            group.addWidget(label)
            
            value_label = QLabel("--")
            value_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            value_label.setAlignment(Qt.AlignCenter)
            group.addWidget(value_label)
            
            latest_layout.addLayout(group)
            self._latest_labels[key] = value_label

        latest_layout.addStretch()
        layout.addWidget(self._latest_group)

    def _load_watchlist(self):
        self._stock_combo.clear()
        symbols = self._watchlist_manager.watchlist
        quotes = self._watchlist_manager.get_sorted_quotes()
        
        for quote in quotes:
            symbol = quote.get('symbol', '')
            name = quote.get('name', '')
            if symbol:
                display_text = f"{symbol}"
                if name:
                    display_text += f" - {name}"
                self._stock_combo.addItem(display_text, symbol)
        
        for symbol in symbols:
            exists = False
            for i in range(self._stock_combo.count()):
                if self._stock_combo.itemData(i) == symbol:
                    exists = True
                    break
            if not exists:
                self._stock_combo.addItem(symbol, symbol)
        
        self._status_label.setText(f"已加载 {len(symbols)} 只自选股")

    def _get_selected_symbol(self) -> str:
        index = self._stock_combo.currentIndex()
        if index >= 0:
            symbol = self._stock_combo.itemData(index)
            if symbol:
                return symbol
        
        text = self._stock_combo.currentText().strip()
        if text:
            if ' - ' in text:
                return text.split(' - ')[0].strip()
            return text
        return ''

    def _get_period_param(self) -> str:
        period_map = {
            0: '1mo',
            1: '3mo',
            2: '6mo',
            3: '1y',
            4: '2y',
            5: '5y'
        }
        return period_map.get(self._period_combo.currentIndex(), '1y')

    def _get_interval_param(self) -> str:
        interval_map = {
            0: '1d',
            1: '1wk',
            2: '1mo'
        }
        return interval_map.get(self._interval_combo.currentIndex(), '1d')

    def _analyze_current_stock(self):
        symbol = self._get_selected_symbol()
        if not symbol:
            QMessageBox.warning(self, "提示", "请选择或输入股票代码")
            return
        
        self._analyze_stock(symbol)

    def _analyze_stock(self, symbol: str):
        if self._analysis_thread and self._analysis_thread.isRunning():
            QMessageBox.information(self, "提示", "分析正在进行中，请稍候...")
            return

        self._analyze_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._status_label.setText(f"正在分析 {symbol}...")

        period = self._get_period_param()
        interval = self._get_interval_param()

        self._analysis_thread = TechnicalAnalysisThread(
            self._technical_analyzer, symbol, period, interval
        )
        self._analysis_thread.finished_signal.connect(self._on_analysis_finished)
        self._analysis_thread.error_signal.connect(self._on_analysis_error)
        self._analysis_thread.start()

    def _on_analysis_finished(self, result: Dict[str, Any]):
        self._analyze_btn.setEnabled(True)
        self._progress_bar.setVisible(False)

        if not result:
            self._status_label.setText("分析完成，但没有有效结果")
            return

        if not result.get('success'):
            self._status_label.setText(f"分析失败: {result.get('error', '未知错误')}")
            return

        self._current_data = result.get('data')
        self._display_result(self._current_data)
        self._status_label.setText(f"分析完成: {result.get('symbol')}")

    def _on_analysis_error(self, error_msg: str):
        self._analyze_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"分析出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"分析过程中出错:\n{error_msg}")

    def _display_result(self, data: Dict[str, Any]):
        self._price_chart.set_data(data, 'price')
        
        latest = data.get('latest', {})
        
        rsi = latest.get('rsi')
        if rsi is not None:
            self._latest_labels['rsi'].setText(f"{rsi:.2f}")
            if rsi < 30:
                self._latest_labels['rsi'].setStyleSheet("font-size: 14px; font-weight: bold; color: #22c55e;")
            elif rsi > 70:
                self._latest_labels['rsi'].setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
            else:
                self._latest_labels['rsi'].setStyleSheet("font-size: 14px; font-weight: bold; color: #3b82f6;")
        else:
            self._latest_labels['rsi'].setText("--")
            self._latest_labels['rsi'].setStyleSheet("font-size: 14px; font-weight: bold;")

        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        macd_histogram = latest.get('macd_histogram')
        
        if macd is not None:
            self._latest_labels['macd'].setText(f"{macd:.4f}")
        else:
            self._latest_labels['macd'].setText("--")
            
        if macd_signal is not None:
            self._latest_labels['macd_signal'].setText(f"{macd_signal:.4f}")
        else:
            self._latest_labels['macd_signal'].setText("--")
            
        if macd_histogram is not None:
            self._latest_labels['macd_histogram'].setText(f"{macd_histogram:.4f}")
            if macd_histogram > 0:
                self._latest_labels['macd_histogram'].setStyleSheet("font-size: 14px; font-weight: bold; color: #22c55e;")
            else:
                self._latest_labels['macd_histogram'].setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        else:
            self._latest_labels['macd_histogram'].setText("--")
            self._latest_labels['macd_histogram'].setStyleSheet("font-size: 14px; font-weight: bold;")

        k = latest.get('k')
        d = latest.get('d')
        j = latest.get('j')
        
        if k is not None:
            self._latest_labels['k'].setText(f"{k:.2f}")
        else:
            self._latest_labels['k'].setText("--")
            
        if d is not None:
            self._latest_labels['d'].setText(f"{d:.2f}")
        else:
            self._latest_labels['d'].setText("--")
            
        if j is not None:
            self._latest_labels['j'].setText(f"{j:.2f}")
        else:
            self._latest_labels['j'].setText("--")

        percent_b = latest.get('percent_b')
        if percent_b is not None:
            self._latest_labels['percent_b'].setText(f"{percent_b:.2f}")
        else:
            self._latest_labels['percent_b'].setText("--")

        signals = data.get('signals', {})
        if signals:
            self._signal_display.set_signals(signals)

        self._on_indicator_changed()

    def _on_indicator_changed(self):
        if self._current_data is None:
            return

        indicator_index = self._indicator_combo.currentIndex()
        
        indicator_map = {
            0: ('macd', 'MACD'),
            1: ('rsi', 'RSI'),
            2: ('bollinger', '布林带'),
            3: ('kdj', 'KDJ'),
            4: ('volume', '成交量')
        }

        indicator_type, title = indicator_map.get(indicator_index, ('macd', 'MACD'))
        self._indicator_chart.set_title(title)
        self._indicator_chart.set_data(self._current_data, indicator_type)

    def refresh(self):
        self._load_watchlist()


class TechnicalAnalysisThread(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, analyzer: TechnicalAnalyzer, symbol: str, period: str, interval: str):
        super().__init__()
        self._analyzer = analyzer
        self._symbol = symbol
        self._period = period
        self._interval = interval

    def run(self):
        try:
            data = self._analyzer.analyze_all_indicators(
                self._symbol,
                period=self._period,
                interval=self._interval
            )

            if data:
                self.finished_signal.emit({
                    'success': True,
                    'symbol': self._symbol.upper(),
                    'data': data
                })
            else:
                self.finished_signal.emit({
                    'success': False,
                    'symbol': self._symbol.upper(),
                    'error': '无法获取技术分析数据'
                })

        except Exception as e:
            self.error_signal.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._config = ConfigManager()
        self._watchlist_manager = WatchlistManager()
        self._init_ui()
        self._init_timer()
        self._init_menu_bar()

    def _init_ui(self):
        self.setWindowTitle("股票监控应用")
        self.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)

        self._tab_widget = QTabWidget()

        self._watchlist_tab = WatchlistTab()
        self._news_tab = NewsTab()
        self._screener_tab = ScreenerTab()
        self._valuation_tab = ValuationTab()
        self._technical_analysis_tab = TechnicalAnalysisTab()
        self._market_indicator_tab = MarketIndicatorTab()
        self._settings_tab = SettingsTab()

        self._tab_widget.addTab(self._watchlist_tab, "自选股")
        self._tab_widget.addTab(self._news_tab, "资讯")
        self._tab_widget.addTab(self._screener_tab, "选股工具")
        self._tab_widget.addTab(self._valuation_tab, "估值分析")
        self._tab_widget.addTab(self._technical_analysis_tab, "技术分析")
        self._tab_widget.addTab(self._market_indicator_tab, "市场指标")
        self._tab_widget.addTab(self._settings_tab, "设置")

        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tab_widget)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪")

    def _init_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._update_timer_interval()

        if self._config.auto_refresh:
            self._refresh_timer.start()

        self._settings_tab.settings_changed.connect(self._on_settings_changed)

    def _init_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")

        refresh_action = QAction("刷新数据(&R)", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_current_tab)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("视图(&V)")

        watchlist_action = QAction("自选股(&W)", self)
        watchlist_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(0))
        view_menu.addAction(watchlist_action)

        news_action = QAction("资讯(&N)", self)
        news_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(1))
        view_menu.addAction(news_action)

        screener_action = QAction("选股工具(&S)", self)
        screener_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(2))
        view_menu.addAction(screener_action)

        valuation_action = QAction("估值分析(&V)", self)
        valuation_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(3))
        view_menu.addAction(valuation_action)

        technical_analysis_action = QAction("技术分析(&T)", self)
        technical_analysis_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(4))
        view_menu.addAction(technical_analysis_action)

        market_indicator_action = QAction("市场指标(&M)", self)
        market_indicator_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(5))
        view_menu.addAction(market_indicator_action)

        settings_action = QAction("设置(&S)", self)
        settings_action.triggered.connect(lambda: self._tab_widget.setCurrentIndex(6))
        view_menu.addAction(settings_action)

        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _update_timer_interval(self):
        self._refresh_timer.setInterval(self._config.refresh_interval * 1000)

    def _auto_refresh(self):
        if self._config.auto_refresh:
            current_index = self._tab_widget.currentIndex()
            if current_index == 0:
                self._watchlist_tab.refresh()
            self._status_bar.showMessage(f"自动刷新于 {datetime.now().strftime('%H:%M:%S')}")

    def _on_tab_changed(self, index: int):
        if index == 0:
            self._status_bar.showMessage("自选股页面")
        elif index == 1:
            self._status_bar.showMessage("资讯页面")
        elif index == 2:
            self._status_bar.showMessage("选股工具页面")
        elif index == 3:
            self._status_bar.showMessage("估值分析页面")
        elif index == 4:
            self._status_bar.showMessage("技术分析页面")
        elif index == 5:
            self._status_bar.showMessage("市场指标页面")
        elif index == 6:
            self._status_bar.showMessage("设置页面")

    def _refresh_current_tab(self):
        current_index = self._tab_widget.currentIndex()
        if current_index == 0:
            self._watchlist_tab.refresh()
        elif current_index == 1:
            self._news_tab.refresh()
        elif current_index == 2:
            self._screener_tab.refresh()
        elif current_index == 3:
            self._valuation_tab.refresh()
        elif current_index == 4:
            self._technical_analysis_tab.refresh()
        elif current_index == 5:
            self._market_indicator_tab.refresh()
        elif current_index == 6:
            self._settings_tab.refresh()

        self._status_bar.showMessage(f"手动刷新于 {datetime.now().strftime('%H:%M:%S')}")

    def _on_settings_changed(self):
        self._update_timer_interval()
        if self._config.auto_refresh and not self._refresh_timer.isActive():
            self._refresh_timer.start()
        elif not self._config.auto_refresh and self._refresh_timer.isActive():
            self._refresh_timer.stop()

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "股票监控应用 v1.0.0\n\n"
            "基于 yfinance 和 PyQt5 开发\n\n"
            "功能:\n"
            "- 自选股管理\n"
            "- 实时行情监控\n"
            "- 新闻资讯获取\n"
            "- 智能选股工具\n"
            "- 估值分析功能\n"
            "- 技术分析功能"
        )

    def closeEvent(self, event):
        self._watchlist_manager.stop_auto_refresh()
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        event.accept()
