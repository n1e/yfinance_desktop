from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QSplitter,
    QCheckBox, QListWidget, QListWidgetItem, QMessageBox,
    QStackedWidget, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from typing import List, Dict, Any, Optional
import numpy as np

from .score_calculator import ScoreCalculator, StockScoreResult, ScoreDimension
from .enhanced_radar_chart import (
    SingleRadarChart, MultiRadarChart, ScoreBarChart,
    ScoreDetailPanel, WeightConfigWidget, STOCK_COLORS
)
from .score_ranking import ScoreRankingWidget
from .watchlist import WatchlistManager
from .data_provider import DataProvider


class ScoreAnalysisThread(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    completed_signal = pyqtSignal()

    def __init__(self, calculator: ScoreCalculator, symbol: str, weights: Optional[Dict[str, float]] = None):
        super().__init__()
        self._calculator = calculator
        self._symbol = symbol
        self._weights = weights
        self._is_cancelled = False

    def run(self):
        try:
            self.progress_signal.emit(0, 1, self._symbol)
            result = self._calculator.calculate_score(self._symbol, self._weights)
            if not self._is_cancelled:
                self.finished_signal.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))
        finally:
            self.completed_signal.emit()

    def cancel(self):
        self._is_cancelled = True


class ScoreRadarTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._watchlist_manager = WatchlistManager()
        self._score_calculator = ScoreCalculator()
        self._data_provider = DataProvider()
        self._current_result: Optional[StockScoreResult] = None
        self._compare_results: Dict[str, Optional[StockScoreResult]] = {}
        self._analysis_thread: Optional[ScoreAnalysisThread] = None
        self._init_ui()
        self._load_watchlist()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        control_group = QGroupBox("功能选择")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("功能模式:"))

        self._mode_combo = QComboBox()
        self._mode_combo.setMinimumWidth(200)
        self._mode_combo.addItem("单股票分析", "single")
        self._mode_combo.addItem("多股票对比", "compare")
        self._mode_combo.addItem("综合评分排行榜", "ranking")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        control_layout.addWidget(self._mode_combo)

        control_layout.addSpacing(30)

        self._weight_btn = QPushButton("调整权重配置")
        self._weight_btn.setMinimumHeight(35)
        self._weight_btn.clicked.connect(self._toggle_weight_panel)
        control_layout.addWidget(self._weight_btn)

        self._refresh_btn = QPushButton("刷新数据")
        self._refresh_btn.setMinimumHeight(35)
        self._refresh_btn.clicked.connect(self._refresh_data)
        control_layout.addWidget(self._refresh_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        main_splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self._weight_panel = QGroupBox("权重配置")
        self._weight_panel.setMaximumWidth(350)
        weight_layout = QVBoxLayout(self._weight_panel)

        self._weight_config = WeightConfigWidget()
        default_weights = self._score_calculator.DEFAULT_WEIGHTS.copy()
        default_dimensions = list(default_weights.keys())
        self._weight_config.set_dimensions(default_dimensions, default_weights)
        weight_layout.addWidget(self._weight_config)

        apply_weight_btn = QPushButton("应用权重")
        apply_weight_btn.clicked.connect(self._apply_weights)
        weight_layout.addWidget(apply_weight_btn)

        self._weight_panel.setVisible(False)
        left_layout.addWidget(self._weight_panel)

        self._stacked_widget = QStackedWidget()

        self._single_widget = self._create_single_analysis_widget()
        self._compare_widget = self._create_compare_widget()
        self._ranking_widget = ScoreRankingWidget()
        self._ranking_widget.stock_selected.connect(self._on_ranking_stock_selected)

        self._stacked_widget.addWidget(self._single_widget)
        self._stacked_widget.addWidget(self._compare_widget)
        self._stacked_widget.addWidget(self._ranking_widget)

        left_layout.addWidget(self._stacked_widget, 1)

        main_splitter.addWidget(left_widget)

        self._detail_panel = ScoreDetailPanel()
        self._detail_panel.setMinimumWidth(400)
        main_splitter.addWidget(self._detail_panel)

        main_splitter.setSizes([800, 400])

        layout.addWidget(main_splitter, 1)

    def _create_single_analysis_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        control_group = QGroupBox("股票选择")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("选择股票:"))

        self._single_stock_combo = QComboBox()
        self._single_stock_combo.setEditable(True)
        self._single_stock_combo.setMinimumWidth(200)
        control_layout.addWidget(self._single_stock_combo)

        self._single_analyze_btn = QPushButton("开始分析")
        self._single_analyze_btn.setMinimumHeight(35)
        self._single_analyze_btn.clicked.connect(self._analyze_single_stock)
        control_layout.addWidget(self._single_analyze_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        chart_group = QGroupBox("雷达图")
        chart_layout = QVBoxLayout(chart_group)

        self._single_radar = SingleRadarChart()
        self._single_radar.setMinimumHeight(400)
        chart_layout.addWidget(self._single_radar)

        layout.addWidget(chart_group, 1)

        return widget

    def _create_compare_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        control_group = QGroupBox("股票对比选择")
        control_layout = QVBoxLayout(control_group)

        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("选择要对比的股票 (最多5只):"))

        self._compare_stock_list = QListWidget()
        self._compare_stock_list.setSelectionMode(QListWidget.MultiSelection)
        self._compare_stock_list.setMaximumHeight(120)
        self._compare_stock_list.setMinimumHeight(80)

        btn_layout = QVBoxLayout()

        self._compare_analyze_btn = QPushButton("开始对比分析")
        self._compare_analyze_btn.setMinimumHeight(35)
        self._compare_analyze_btn.clicked.connect(self._analyze_compare_stocks)
        btn_layout.addWidget(self._compare_analyze_btn)

        self._select_all_btn = QPushButton("全选")
        self._select_all_btn.clicked.connect(self._select_all_compare_stocks)
        btn_layout.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("取消全选")
        self._deselect_all_btn.clicked.connect(self._deselect_all_compare_stocks)
        btn_layout.addWidget(self._deselect_all_btn)

        main_compare_layout = QHBoxLayout()
        main_compare_layout.addWidget(self._compare_stock_list, 3)
        main_compare_layout.addLayout(btn_layout, 1)

        control_layout.addLayout(select_layout)
        control_layout.addLayout(main_compare_layout)

        layout.addWidget(control_group)

        self._compare_stack = QStackedWidget()

        radar_compare_group = QGroupBox("雷达图对比")
        radar_compare_layout = QVBoxLayout(radar_compare_group)
        self._compare_radar = MultiRadarChart()
        self._compare_radar.setMinimumHeight(350)
        radar_compare_layout.addWidget(self._compare_radar)

        self._compare_stack.addWidget(radar_compare_group)

        bar_compare_group = QGroupBox("单维度柱状图对比")
        bar_compare_layout = QVBoxLayout(bar_compare_group)

        bar_control = QHBoxLayout()
        bar_control.addWidget(QLabel("选择维度:"))

        self._bar_dimension_combo = QComboBox()
        self._bar_dimension_combo.setMinimumWidth(200)
        self._bar_dimension_combo.addItem("综合评分 (加权)", "_weighted")
        self._bar_dimension_combo.addItem("综合评分 (平均)", "_total")
        for dim in ScoreDimension:
            self._bar_dimension_combo.addItem(dim.value, dim.value)
        self._bar_dimension_combo.currentIndexChanged.connect(self._update_bar_chart)
        bar_control.addWidget(self._bar_dimension_combo)
        bar_control.addStretch()

        bar_compare_layout.addLayout(bar_control)

        self._bar_chart = ScoreBarChart()
        self._bar_chart.setMinimumHeight(300)
        bar_compare_layout.addWidget(self._bar_chart)

        self._compare_stack.addWidget(bar_compare_group)

        switch_layout = QHBoxLayout()
        self._show_radar_btn = QPushButton("雷达图视图")
        self._show_radar_btn.clicked.connect(lambda: self._compare_stack.setCurrentIndex(0))
        self._show_bar_btn = QPushButton("柱状图视图")
        self._show_bar_btn.clicked.connect(lambda: self._compare_stack.setCurrentIndex(1))
        switch_layout.addWidget(self._show_radar_btn)
        switch_layout.addWidget(self._show_bar_btn)
        switch_layout.addStretch()

        layout.addLayout(switch_layout)
        layout.addWidget(self._compare_stack, 1)

        return widget

    def _load_watchlist(self):
        symbols = self._watchlist_manager.watchlist
        quotes = self._watchlist_manager.get_sorted_quotes()

        self._single_stock_combo.clear()
        self._compare_stock_list.clear()

        symbol_map = {}
        for quote in quotes:
            symbol = quote.get('symbol', '')
            name = quote.get('name', '')
            if symbol:
                display_text = f"{symbol}"
                if name:
                    display_text += f" - {name}"
                self._single_stock_combo.addItem(display_text, symbol)
                self._compare_stock_list.addItem(display_text)
                symbol_map[display_text] = symbol

        for symbol in symbols:
            exists = False
            for i in range(self._single_stock_combo.count()):
                if self._single_stock_combo.itemData(i) == symbol:
                    exists = True
                    break
            if not exists:
                self._single_stock_combo.addItem(symbol, symbol)
                self._compare_stock_list.addItem(symbol)

    def _get_selected_single_symbol(self) -> str:
        index = self._single_stock_combo.currentIndex()
        if index >= 0:
            symbol = self._single_stock_combo.itemData(index)
            if symbol:
                return symbol

        text = self._single_stock_combo.currentText().strip()
        if text:
            if ' - ' in text:
                return text.split(' - ')[0].strip()
            return text
        return ''

    def _get_selected_compare_symbols(self) -> List[str]:
        selected_items = self._compare_stock_list.selectedItems()
        symbols = []

        for item in selected_items:
            text = item.text()
            if ' - ' in text:
                symbol = text.split(' - ')[0].strip()
            else:
                symbol = text
            if symbol:
                symbols.append(symbol)

        return symbols[:5]

    def _cleanup_thread(self):
        if self._analysis_thread is not None:
            try:
                if self._analysis_thread.isRunning():
                    self._analysis_thread.cancel()
                    self._analysis_thread.quit()
                    if not self._analysis_thread.wait(3000):
                        self._analysis_thread.terminate()
                        self._analysis_thread.wait()
            except Exception:
                pass
            finally:
                self._analysis_thread = None

    def _analyze_single_stock(self):
        symbol = self._get_selected_single_symbol()
        if not symbol:
            QMessageBox.warning(self, "提示", "请选择或输入股票代码")
            return

        if self._analysis_thread is not None and self._analysis_thread.isRunning():
            QMessageBox.information(self, "提示", "分析正在进行中，请稍候...")
            return

        self._cleanup_thread()

        weights = self._weight_config.get_normalized_weights()

        self._single_analyze_btn.setEnabled(False)
        thread = ScoreAnalysisThread(
            self._score_calculator,
            symbol,
            weights
        )
        thread.finished_signal.connect(self._on_single_analysis_finished)
        thread.error_signal.connect(self._on_analysis_error)
        thread.completed_signal.connect(self._on_thread_completed)
        thread.finished.connect(thread.deleteLater)

        self._analysis_thread = thread
        thread.start()

    def _on_single_analysis_finished(self, result: Optional[StockScoreResult]):
        self._single_analyze_btn.setEnabled(True)

        if result is None:
            QMessageBox.warning(self, "提示", "无法获取股票评分数据")
            return

        self._current_result = result
        self._single_radar.set_data(result)
        self._detail_panel.set_result(result)

    def _on_thread_completed(self):
        pass

    def _analyze_compare_stocks(self):
        symbols = self._get_selected_compare_symbols()
        if len(symbols) < 2:
            QMessageBox.warning(self, "提示", "请至少选择2只股票进行对比")
            return

        if len(symbols) > 5:
            QMessageBox.warning(self, "提示", "最多只能选择5只股票进行对比")
            return

        weights = self._weight_config.get_normalized_weights()

        self._compare_analyze_btn.setEnabled(False)
        self._compare_results = {}

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def analyze_single(symbol: str) -> Optional[StockScoreResult]:
            try:
                return self._score_calculator.calculate_score(symbol, weights)
            except Exception as e:
                print(f"分析 {symbol} 失败: {e}")
                return None

        all_valid = True
        results = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_symbol = {executor.submit(analyze_single, symbol): symbol for symbol in symbols}

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    results[symbol] = result
                    if result is None:
                        all_valid = False
                except Exception as e:
                    print(f"处理 {symbol} 时出错: {e}")
                    results[symbol] = None
                    all_valid = False

        self._compare_results = results
        self._compare_radar.set_results(results)
        self._update_bar_chart()
        self._compare_analyze_btn.setEnabled(True)

        if not all_valid:
            QMessageBox.information(self, "提示", "部分股票无法获取完整数据")

    def _update_bar_chart(self):
        if not self._compare_results:
            return

        dimension = self._bar_dimension_combo.currentData()

        if dimension == "_weighted":
            weighted_results = {}
            for symbol, result in self._compare_results.items():
                if result:
                    weighted_results[symbol] = result
            self._bar_chart.set_data(weighted_results, "综合评分 (加权)")
        elif dimension == "_total":
            total_results = {}
            for symbol, result in self._compare_results.items():
                if result:
                    total_results[symbol] = result
            self._bar_chart.set_data(total_results, "综合评分 (平均)")
        else:
            self._bar_chart.set_data(self._compare_results, dimension)

    def _select_all_compare_stocks(self):
        count = self._compare_stock_list.count()
        for i in range(min(count, 5)):
            self._compare_stock_list.item(i).setSelected(True)

    def _deselect_all_compare_stocks(self):
        for i in range(self._compare_stock_list.count()):
            self._compare_stock_list.item(i).setSelected(False)

    def _on_ranking_stock_selected(self, result: StockScoreResult):
        if result:
            self._current_result = result
            self._detail_panel.set_result(result)

            for i in range(self._single_stock_combo.count()):
                if self._single_stock_combo.itemData(i) == result.symbol:
                    self._single_stock_combo.setCurrentIndex(i)
                    break

            self._single_radar.set_data(result)

    def _on_mode_changed(self, index):
        mode = self._mode_combo.currentData()

        if mode == "single":
            self._stacked_widget.setCurrentIndex(0)
        elif mode == "compare":
            self._stacked_widget.setCurrentIndex(1)
        elif mode == "ranking":
            self._stacked_widget.setCurrentIndex(2)

    def _toggle_weight_panel(self):
        is_visible = self._weight_panel.isVisible()
        self._weight_panel.setVisible(not is_visible)

        if not is_visible:
            self._weight_btn.setText("隐藏权重配置")
        else:
            self._weight_btn.setText("调整权重配置")

    def _apply_weights(self):
        weights = self._weight_config.get_normalized_weights()
        self._score_calculator.set_weights(weights)
        self._ranking_widget.set_weights(weights)

        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            QMessageBox.information(
                self, "提示",
                f"权重已自动归一化，总权重从 {total*100:.0f}% 调整为 100%"
            )
        else:
            QMessageBox.information(self, "提示", "权重已应用")

    def _refresh_data(self):
        self._load_watchlist()

        mode = self._mode_combo.currentData()
        if mode == "ranking":
            self._ranking_widget.refresh()

    def _on_analysis_error(self, error_msg: str):
        self._single_analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", f"分析过程中出错:\n{error_msg}")

    def refresh(self):
        self._load_watchlist()
