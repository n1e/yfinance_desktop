from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QGroupBox, QProgressBar,
    QSplitter, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from typing import List, Dict, Any, Optional, Callable
import pandas as pd

from .score_calculator import ScoreCalculator, StockScoreResult
from .watchlist import WatchlistManager


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text: str = '', value: float = 0.0):
        super().__init__(text)
        self._value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self._value < other._value
        return super().__lt__(other)

    @property
    def value(self) -> float:
        return self._value


class RankingWorker(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    completed_signal = pyqtSignal()

    def __init__(
        self,
        calculator: ScoreCalculator,
        symbols: List[str],
        weights: Optional[Dict[str, float]] = None
    ):
        super().__init__()
        self._calculator = calculator
        self._symbols = symbols
        self._weights = weights
        self._is_cancelled = False

    def run(self):
        results = []
        total = len(self._symbols)

        try:
            for i, symbol in enumerate(self._symbols):
                if self._is_cancelled:
                    break

                self.progress_signal.emit(i + 1, total, symbol)

                try:
                    result = self._calculator.calculate_score(symbol, self._weights)
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"计算 {symbol} 评分失败: {e}")
                    continue

            if not self._is_cancelled:
                results.sort(key=lambda x: x.weighted_score if x else 0, reverse=True)
                self.finished_signal.emit(results)

        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))
        finally:
            self.completed_signal.emit()

    def cancel(self):
        self._is_cancelled = True


class ScoreRankingWidget(QWidget):
    stock_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watchlist_manager = WatchlistManager()
        self._score_calculator = ScoreCalculator()
        self._current_results: List[StockScoreResult] = []
        self._current_weights: Optional[Dict[str, float]] = None
        self._ranking_worker: Optional[RankingWorker] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        control_group = QGroupBox("排行榜控制")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("排序方式:"))

        self._sort_combo = QComboBox()
        self._sort_combo.setMinimumWidth(180)
        self._sort_combo.addItem("综合评分 (加权)", "weighted_score")
        self._sort_combo.addItem("综合评分 (平均)", "total_score")
        self._sort_combo.currentIndexChanged.connect(self._sort_results)
        control_layout.addWidget(self._sort_combo)

        control_layout.addSpacing(20)
        control_layout.addWidget(QLabel("筛选维度:"))

        self._filter_combo = QComboBox()
        self._filter_combo.setMinimumWidth(180)
        self._filter_combo.addItem("全部维度", "all")
        self._filter_combo.addItem("技术面信号", "技术面信号")
        self._filter_combo.addItem("估值合理性", "估值合理性")
        self._filter_combo.addItem("动量强度", "动量强度")
        self._filter_combo.addItem("市值规模", "市值规模")
        self._filter_combo.addItem("量价配合", "量价配合")
        self._filter_combo.addItem("波动率风险", "波动率风险")
        self._filter_combo.addItem("成长潜力", "成长潜力")
        self._filter_combo.currentIndexChanged.connect(self._filter_results)
        control_layout.addWidget(self._filter_combo)

        control_layout.addSpacing(20)

        self._refresh_btn = QPushButton("刷新排行榜")
        self._refresh_btn.setMinimumHeight(35)
        self._refresh_btn.clicked.connect(self._refresh_ranking)
        control_layout.addWidget(self._refresh_btn)

        self._analyze_all_btn = QPushButton("重新计算所有评分")
        self._analyze_all_btn.setMinimumHeight(35)
        self._analyze_all_btn.clicked.connect(self._analyze_all_stocks)
        control_layout.addWidget(self._analyze_all_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("点击'刷新排行榜'或'重新计算所有评分'开始")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        self._table = QTableWidget()
        self._table.setMinimumHeight(300)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_double_clicked)

        layout.addWidget(self._table, 1)

        self._init_table_columns()

    def _init_table_columns(self):
        columns = [
            "排名", "股票代码", "公司名称", "综合评分(加权)", "综合评分(平均)", "状态",
            "技术面信号", "估值合理性", "动量强度", "市值规模",
            "量价配合", "波动率风险", "成长潜力"
        ]

        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels(columns)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        for i in range(3, len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 80)

    def set_weights(self, weights: Dict[str, float]):
        self._current_weights = weights.copy()

    def get_current_results(self) -> List[StockScoreResult]:
        return self._current_results.copy()

    def get_selected_result(self) -> Optional[StockScoreResult]:
        selected = self._table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        if 0 <= row < len(self._current_results):
            return self._current_results[row]
        return None

    def _refresh_ranking(self):
        watchlist = self._watchlist_manager.watchlist
        if not watchlist:
            QMessageBox.information(self, "提示", "自选股列表为空，请先添加股票")
            return

        if not self._current_results:
            self._analyze_all_stocks()
            return

        self._display_results(self._current_results)

    def _is_worker_running(self) -> bool:
        if self._ranking_worker is None:
            return False
        try:
            return self._ranking_worker.isRunning()
        except RuntimeError:
            self._ranking_worker = None
            return False

    def _cleanup_worker(self):
        if self._ranking_worker is None:
            return

        try:
            if self._ranking_worker.isRunning():
                self._ranking_worker.cancel()
                self._ranking_worker.quit()
                if not self._ranking_worker.wait(3000):
                    self._ranking_worker.terminate()
                    self._ranking_worker.wait()
        except RuntimeError:
            pass
        except Exception:
            pass
        finally:
            self._ranking_worker = None

    def _analyze_all_stocks(self):
        watchlist = self._watchlist_manager.watchlist
        if not watchlist:
            QMessageBox.information(self, "提示", "自选股列表为空，请先添加股票")
            return

        if self._is_worker_running():
            QMessageBox.information(self, "提示", "评分计算正在进行中，请稍候...")
            return

        self._cleanup_worker()

        self._refresh_btn.setEnabled(False)
        self._analyze_all_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(watchlist))
        self._progress_bar.setValue(0)
        self._status_label.setText(f"开始计算 {len(watchlist)} 只股票的评分...")

        worker = RankingWorker(
            self._score_calculator,
            watchlist,
            self._current_weights
        )
        worker.progress_signal.connect(self._on_progress)
        worker.finished_signal.connect(self._on_analysis_finished)
        worker.error_signal.connect(self._on_analysis_error)

        self._ranking_worker = worker
        worker.start()

    def _on_progress(self, current: int, total: int, symbol: str):
        self._progress_bar.setValue(current)
        self._status_label.setText(f"正在计算: {symbol} ({current}/{total})")

    def _on_analysis_finished(self, results: List[StockScoreResult]):
        self._refresh_btn.setEnabled(True)
        self._analyze_all_btn.setEnabled(True)
        self._progress_bar.setVisible(False)

        self._current_results = results
        self._display_results(results)

        self._status_label.setText(f"计算完成，共 {len(results)} 只股票")

        if results:
            self._table.selectRow(0)

    def _on_analysis_error(self, error_msg: str):
        self._refresh_btn.setEnabled(True)
        self._analyze_all_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"计算出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"评分计算过程中出错:\n{error_msg}")

    def _display_results(self, results: List[StockScoreResult]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        if not results:
            return

        sort_by = self._sort_combo.currentData()
        filter_by = self._filter_combo.currentData()

        display_results = results.copy()

        if filter_by != "all":
            display_results = [
                r for r in display_results
                if filter_by in r.dimension_scores
            ]

        if sort_by == "weighted_score":
            display_results.sort(key=lambda x: x.weighted_score, reverse=True)
        elif sort_by == "total_score":
            display_results.sort(key=lambda x: x.total_score, reverse=True)

        self._table.setRowCount(len(display_results))

        green = QColor(34, 197, 94)
        yellow = QColor(245, 158, 11)
        red = QColor(239, 68, 68)
        blue = QColor(59, 130, 246)

        for row, result in enumerate(display_results):
            self._table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

            symbol_item = QTableWidgetItem(result.symbol)
            symbol_item.setData(Qt.UserRole, result)
            self._table.setItem(row, 1, symbol_item)

            self._table.setItem(row, 2, QTableWidgetItem(result.name))

            weighted_score = result.weighted_score
            avg_score = result.total_score

            weighted_item = NumericTableWidgetItem(f"{weighted_score:.1f}", weighted_score)
            avg_item = NumericTableWidgetItem(f"{avg_score:.1f}", avg_score)

            if weighted_score >= 80:
                weighted_item.setForeground(green)
            elif weighted_score >= 65:
                weighted_item.setForeground(blue)
            elif weighted_score >= 50:
                weighted_item.setForeground(yellow)
            else:
                weighted_item.setForeground(red)

            if avg_score >= 80:
                avg_item.setForeground(green)
            elif avg_score >= 65:
                avg_item.setForeground(blue)
            elif avg_score >= 50:
                avg_item.setForeground(yellow)
            else:
                avg_item.setForeground(red)

            self._table.setItem(row, 3, weighted_item)
            self._table.setItem(row, 4, avg_item)

            status_item = QTableWidgetItem(result.status)
            if result.status == "优秀":
                status_item.setForeground(green)
            elif result.status == "良好":
                status_item.setForeground(blue)
            elif result.status == "一般":
                status_item.setForeground(yellow)
            else:
                status_item.setForeground(red)
            self._table.setItem(row, 5, status_item)

            col_index = 6
            dimension_order = [
                "技术面信号", "估值合理性", "动量强度", "市值规模",
                "量价配合", "波动率风险", "成长潜力"
            ]

            for dim_name in dimension_order:
                dim_score = result.dimension_scores.get(dim_name)
                if dim_score:
                    score = dim_score.score
                    item = NumericTableWidgetItem(f"{score:.0f}", score)

                    if score >= 75:
                        item.setForeground(green)
                    elif score >= 50:
                        item.setForeground(blue)
                    elif score >= 30:
                        item.setForeground(yellow)
                    else:
                        item.setForeground(red)

                    self._table.setItem(row, col_index, item)
                else:
                    self._table.setItem(row, col_index, QTableWidgetItem("-"))
                col_index += 1

        self._table.setSortingEnabled(True)

        if filter_by == "all":
            self._status_label.setText(f"显示 {len(display_results)} 只股票")
        else:
            self._status_label.setText(f"按'{filter_by}'筛选，显示 {len(display_results)} 只股票")

    def _sort_results(self):
        if self._current_results:
            self._display_results(self._current_results)

    def _filter_results(self):
        if self._current_results:
            self._display_results(self._current_results)

    def _on_selection_changed(self):
        selected = self.get_selected_result()
        if selected:
            self.stock_selected.emit(selected)

    def _on_double_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self._current_results):
            result = self._current_results[row]
            self.stock_selected.emit(result)

    def refresh(self):
        if self._current_results:
            self._display_results(self._current_results)
        else:
            self._analyze_all_stocks()
