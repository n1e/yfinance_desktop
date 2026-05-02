from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QScrollArea, QFrame,
    QSplitter, QSizePolicy, QComboBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGridLayout, QTextEdit, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, 
    QPolygonF, QLinearGradient, QPainterPath
)
from typing import List, Dict, Any, Optional
import math
from datetime import datetime

from .watchlist import WatchlistManager
from .portfolio_health_analyzer import (
    PortfolioHealthAnalyzer, PortfolioHealthResult, 
    HealthDimension, DimensionScore, OptimizationSuggestion,
    HealthHistoryRecord
)


class HealthRadarChart(QWidget):
    DIMENSIONS = [
        (HealthDimension.LIQUIDITY.value, 0.20),
        (HealthDimension.VALUATION.value, 0.20),
        (HealthDimension.DIVERSIFICATION.value, 0.20),
        (HealthDimension.VOLATILITY.value, 0.20),
        (HealthDimension.TREND.value, 0.20),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scores: Dict[str, float] = {}
        self._total_score: float = 0.0
        self._status: str = ''
        self._status_color: QColor = QColor(100, 100, 100)
        self.setMinimumSize(400, 400)

    def set_data(self, result: PortfolioHealthResult):
        self._scores = {}
        for name, dim in result.dimension_scores.items():
            self._scores[name] = dim.score
        
        self._total_score = result.weighted_score
        self._status = result.status

        if self._total_score >= 80:
            self._status_color = QColor(34, 197, 94)
        elif self._total_score >= 65:
            self._status_color = QColor(59, 130, 246)
        elif self._total_score >= 50:
            self._status_color = QColor(168, 162, 158)
        elif self._total_score >= 35:
            self._status_color = QColor(251, 146, 60)
        else:
            self._status_color = QColor(239, 68, 68)

        self.update()

    def clear(self):
        self._scores = {}
        self._total_score = 0.0
        self._status = ''
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        max_radius = min(center_x, center_y) - 80

        self._draw_background(painter, center_x, center_y, max_radius)
        self._draw_grid(painter, center_x, center_y, max_radius)
        self._draw_data(painter, center_x, center_y, max_radius)
        self._draw_labels(painter, center_x, center_y, max_radius)
        self._draw_legend(painter, width, height)

    def _draw_background(self, painter: QPainter, cx: int, cy: int, radius: int):
        painter.setPen(Qt.NoPen)
        gradient = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        gradient.setColorAt(0, QColor(250, 250, 252))
        gradient.setColorAt(1, QColor(241, 245, 249))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(cx - radius - 10, cy - radius - 10, 
                           (radius + 10) * 2, (radius + 10) * 2)

    def _draw_grid(self, painter: QPainter, cx: int, cy: int, radius: int):
        painter.setPen(QPen(QColor(203, 213, 225), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)

        num_levels = 5
        for i in range(num_levels + 1):
            r = int(radius * i / num_levels)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            
            if i > 0:
                score_text = f"{int(i * 20)}"
                painter.setFont(QFont('Microsoft YaHei', 8))
                painter.setPen(QPen(QColor(148, 163, 184), 1))
                painter.drawText(cx + 5, cy - r, score_text)

        num_axes = len(self.DIMENSIONS)
        painter.setPen(QPen(QColor(148, 163, 184), 1, Qt.SolidLine))
        for i in range(num_axes):
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            painter.drawLine(cx, cy, x, y)

    def _draw_data(self, painter: QPainter, cx: int, cy: int, radius: int):
        num_axes = len(self.DIMENSIONS)

        points = []
        for i in range(num_axes):
            name, _ = self.DIMENSIONS[i]
            score = self._scores.get(name, 0)
            r = int(radius * score / 100.0)
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))

        if any(self._scores.values()):
            polygon = QPolygonF()
            for x, y in points:
                polygon.append(QPointF(x, y))

            fill_color = QColor(self._status_color.red(), self._status_color.green(), 
                               self._status_color.blue(), 60)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(QPen(self._status_color, 2, Qt.SolidLine))
            painter.drawPolygon(polygon)

            for x, y in points:
                painter.setBrush(QBrush(self._status_color))
                painter.setPen(QPen(Qt.white, 2))
                painter.drawEllipse(x - 5, y - 5, 10, 10)

    def _draw_labels(self, painter: QPainter, cx: int, cy: int, radius: int):
        num_axes = len(self.DIMENSIONS)
        label_radius = radius + 35

        painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))

        for i in range(num_axes):
            name, _ = self.DIMENSIONS[i]
            score = self._scores.get(name, 0)
            
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(label_radius * math.cos(angle))
            y = cy + int(label_radius * math.sin(angle))

            short_name = name.replace('评分', '')
            score_text = f"{int(score)}分"

            if abs(math.cos(angle)) < 0.1:
                align = Qt.AlignHCenter
            elif math.cos(angle) > 0:
                align = Qt.AlignLeft
            else:
                align = Qt.AlignRight

            if abs(math.sin(angle)) < 0.1:
                align |= Qt.AlignVCenter
            elif math.sin(angle) > 0:
                align |= Qt.AlignTop
            else:
                align |= Qt.AlignBottom

            if score >= 70:
                color = QColor(34, 197, 94)
            elif score >= 50:
                color = QColor(59, 130, 246)
            elif score >= 30:
                color = QColor(251, 146, 60)
            else:
                color = QColor(239, 68, 68)

            painter.setPen(QPen(color, 1))

            if align & Qt.AlignLeft:
                draw_x = x
            elif align & Qt.AlignRight:
                draw_x = x - 80
            else:
                draw_x = x - 40

            if align & Qt.AlignTop:
                draw_y = y
            elif align & Qt.AlignBottom:
                draw_y = y - 35
            else:
                draw_y = y - 17

            painter.drawText(draw_x, draw_y, 80, 35, 
                           Qt.AlignCenter | Qt.TextWordWrap, 
                           f"{short_name}\n{score_text}")

    def _draw_legend(self, painter: QPainter, width: int, height: int):
        if self._total_score <= 0:
            return

        painter.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        painter.setPen(QPen(self._status_color, 1))

        legend_text = f'综合健康度: {int(self._total_score)}分'
        if self._status:
            legend_text += f'  ({self._status})'

        painter.drawText(0, height - 25, width, 20, Qt.AlignCenter, legend_text)


class DimensionDetailCard(QFrame):
    def __init__(self, dimension_score: DimensionScore, parent=None):
        super().__init__(parent)
        self._score = dimension_score
        self._init_ui()

    def _init_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            DimensionDetailCard {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
            DimensionDetailCard:hover {
                border: 1px solid #cbd5e1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        
        name_label = QLabel(self._score.name)
        name_label.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        name_label.setStyleSheet("color: #1e293b;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        score_text = f"{int(self._score.score)}分"
        score_label = QLabel(score_text)
        score_label.setFont(QFont('Microsoft YaHei', 16, QFont.Bold))
        
        if self._score.score >= 70:
            score_label.setStyleSheet("color: #22c55e;")
        elif self._score.score >= 50:
            score_label.setStyleSheet("color: #3b82f6;")
        elif self._score.score >= 30:
            score_label.setStyleSheet("color: #fb923c;")
        else:
            score_label.setStyleSheet("color: #ef4444;")
        header_layout.addWidget(score_label)
        
        layout.addLayout(header_layout)

        bar_layout = QHBoxLayout()
        
        bar_container = QFrame()
        bar_container.setFixedHeight(20)
        bar_layout_inner = QHBoxLayout(bar_container)
        bar_layout_inner.setContentsMargins(0, 0, 0, 0)
        
        bar_bg = QFrame()
        bar_bg.setStyleSheet("""
            background-color: #e2e8f0;
            border-radius: 10px;
        """)
        bar_bg.setFixedHeight(16)
        
        fill_width = int(self._score.score / 100 * 200)
        
        if self._score.score >= 70:
            color = "#22c55e"
        elif self._score.score >= 50:
            color = "#3b82f6"
        elif self._score.score >= 30:
            color = "#fb923c"
        else:
            color = "#ef4444"
        
        bar_fill = QFrame()
        bar_fill.setStyleSheet(f"""
            background-color: {color};
            border-radius: 8px;
        """)
        bar_fill.setFixedHeight(14)
        bar_fill.setFixedWidth(fill_width if fill_width > 0 else 2)
        
        bar_layout_inner.addWidget(bar_fill)
        bar_layout_inner.addStretch()
        
        bar_layout.addWidget(bar_container)
        layout.addLayout(bar_layout)

        if self._score.current_value:
            current_label = QLabel(f"当前值: {self._score.current_value}")
            current_label.setStyleSheet("color: #64748b; font-size: 11px;")
            current_label.setWordWrap(True)
            layout.addWidget(current_label)

        if self._score.calculation_logic:
            logic_label = QLabel(f"计算逻辑: {self._score.calculation_logic}")
            logic_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
            logic_label.setWordWrap(True)
            layout.addWidget(logic_label)

        layout.addStretch()


class SuggestionCard(QFrame):
    def __init__(self, suggestion: OptimizationSuggestion, parent=None):
        super().__init__(parent)
        self._suggestion = suggestion
        self._init_ui()

    def _init_ui(self):
        self.setFrameStyle(QFrame.StyledPanel)
        
        if self._suggestion.severity == "danger":
            border_color = "#fecaca"
            bg_color = "#fef2f2"
            icon_color = "#ef4444"
        elif self._suggestion.severity == "warning":
            border_color = "#fed7aa"
            bg_color = "#fff7ed"
            icon_color = "#f97316"
        else:
            border_color = "#bfdbfe"
            bg_color = "#eff6ff"
            icon_color = "#3b82f6"

        self.setStyleSheet(f"""
            SuggestionCard {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 1px solid {border_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        
        category_label = QLabel(f"[{self._suggestion.category}]")
        category_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        category_label.setStyleSheet(f"color: {icon_color};")
        header_layout.addWidget(category_label)
        
        header_layout.addStretch()
        
        severity_label = QLabel(self._get_severity_text())
        severity_label.setFont(QFont('Microsoft YaHei', 9))
        severity_label.setStyleSheet(f"color: {icon_color};")
        header_layout.addWidget(severity_label)
        
        layout.addLayout(header_layout)

        title_label = QLabel(self._suggestion.title)
        title_label.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        title_label.setStyleSheet("color: #1e293b;")
        layout.addWidget(title_label)

        desc_label = QLabel(self._suggestion.description)
        desc_label.setStyleSheet("color: #475569; font-size: 11px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        action_label = QLabel(f"💡 建议: {self._suggestion.action}")
        action_label.setStyleSheet("color: #64748b; font-size: 11px;")
        action_label.setWordWrap(True)
        layout.addWidget(action_label)

        if self._suggestion.related_symbols:
            symbols_label = QLabel(f"相关标的: {', '.join(self._suggestion.related_symbols)}")
            symbols_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
            layout.addWidget(symbols_label)

    def _get_severity_text(self) -> str:
        if self._suggestion.severity == "danger":
            return "🔴 高优先级"
        elif self._suggestion.severity == "warning":
            return "🟡 中优先级"
        else:
            return "🔵 信息提示"


class HistoryTrendChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: List[HealthHistoryRecord] = []
        self.setMinimumHeight(250)

    def set_history(self, history: List[HealthHistoryRecord]):
        self._history = history
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        padding_left = 60
        padding_right = 20
        padding_top = 30
        padding_bottom = 40
        
        chart_width = width - padding_left - padding_right
        chart_height = height - padding_top - padding_bottom

        painter.fillRect(0, 0, width, height, QColor(255, 255, 255))

        if not self._history:
            painter.setFont(QFont('Microsoft YaHei', 12))
            painter.setPen(QPen(QColor(148, 163, 184), 1))
            painter.drawText(0, 0, width, height, Qt.AlignCenter, "暂无历史数据")
            return

        painter.setPen(QPen(QColor(226, 232, 240), 1, Qt.DashLine))
        for i in range(5):
            y = int(padding_top + chart_height * i / 4)
            painter.drawLine(padding_left, y, width - padding_right, y)

        painter.setFont(QFont('Microsoft YaHei', 9))
        painter.setPen(QPen(QColor(100, 116, 139), 1))
        for i in range(5):
            y = int(padding_top + chart_height * i / 4)
            score = 100 - i * 25
            painter.drawText(5, y - 8, 50, 16, Qt.AlignRight | Qt.AlignVCenter, f"{score}分")

        if len(self._history) > 1:
            path = QPainterPath()
            fill_path = QPainterPath()
            
            points = []
            for i, record in enumerate(self._history):
                x = padding_left + chart_width * i / (len(self._history) - 1)
                y = padding_top + chart_height * (1 - record.total_score / 100)
                points.append((float(x), float(y)))

            fill_path.moveTo(float(padding_left), float(padding_top + chart_height))
            for i, (x, y) in enumerate(points):
                if i == 0:
                    path.moveTo(x, y)
                    fill_path.lineTo(x, y)
                else:
                    path.lineTo(x, y)
                    fill_path.lineTo(x, y)
            
            fill_path.lineTo(float(points[-1][0]) if points else float(padding_left), 
                           float(padding_top + chart_height))
            fill_path.closeSubpath()

            gradient = QLinearGradient(0, float(padding_top), 0, float(padding_top + chart_height))
            gradient.setColorAt(0, QColor(59, 130, 246, 40))
            gradient.setColorAt(1, QColor(59, 130, 246, 10))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawPath(fill_path)

            painter.setPen(QPen(QColor(59, 130, 246), 2, Qt.SolidLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

            for x, y in points:
                painter.setBrush(QBrush(QColor(59, 130, 246)))
                painter.setPen(QPen(Qt.white, 2))
                painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)

        painter.setPen(QPen(QColor(100, 116, 139), 1))
        painter.setFont(QFont('Microsoft YaHei', 8))
        
        if len(self._history) > 0:
            step = max(1, len(self._history) // 5)
            for i in range(0, len(self._history), step):
                record = self._history[i]
                x = int(padding_left + chart_width * i / (len(self._history) - 1 if len(self._history) > 1 else 1))
                date_str = record.date.strftime("%m-%d")
                painter.drawText(int(x) - 25, height - 25, 50, 20, Qt.AlignCenter, date_str)

        painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
        painter.setPen(QPen(QColor(51, 65, 85), 1))
        painter.drawText(padding_left, 5, 200, 20, Qt.AlignLeft, "健康度历史趋势")


class HealthAnalysisThread(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, analyzer: PortfolioHealthAnalyzer, symbols: List[str], parent=None):
        super().__init__(parent)
        self._analyzer = analyzer
        self._symbols = symbols

    def run(self):
        try:
            def progress_callback(current, total, symbol):
                self.progress_signal.emit(current, total, symbol)

            result = self._analyzer.analyze_portfolio(
                self._symbols,
                progress_callback=progress_callback
            )

            self.finished_signal.emit(result)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_signal.emit(str(e))


class PortfolioHealthTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._watchlist_manager = WatchlistManager()
        self._health_analyzer = PortfolioHealthAnalyzer()
        self._analysis_thread = None
        self._current_result: Optional[PortfolioHealthResult] = None
        self._init_ui()
        self._init_connections()
        self._load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("股票数量:"))
        self._stock_count_label = QLabel("0")
        self._stock_count_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self._stock_count_label)

        control_layout.addSpacing(20)

        self._analyze_btn = QPushButton("开始诊断")
        self._analyze_btn.setMinimumHeight(35)
        self._analyze_btn.setMinimumWidth(120)
        self._analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
        """)
        control_layout.addWidget(self._analyze_btn)

        self._refresh_history_btn = QPushButton("刷新历史")
        self._refresh_history_btn.setMinimumHeight(35)
        control_layout.addWidget(self._refresh_history_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("请添加股票到自选股后开始诊断")
        self._status_label.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(self._status_label)

        main_splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        radar_group = QGroupBox("健康度雷达图")
        radar_layout = QVBoxLayout(radar_group)
        radar_layout.setContentsMargins(5, 5, 5, 5)
        
        self._radar_chart = HealthRadarChart()
        self._radar_chart.setMinimumHeight(350)
        radar_layout.addWidget(self._radar_chart)
        
        left_layout.addWidget(radar_group)

        history_group = QGroupBox("历史趋势")
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(5, 5, 5, 5)
        
        self._history_chart = HistoryTrendChart()
        self._history_chart.setMinimumHeight(200)
        history_layout.addWidget(self._history_chart)
        
        left_layout.addWidget(history_group)

        main_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        dimensions_group = QGroupBox("维度详情")
        dimensions_layout = QGridLayout(dimensions_group)
        dimensions_layout.setSpacing(10)
        
        self._dimension_cards: Dict[str, DimensionDetailCard] = {}
        dimensions = [
            HealthDimension.LIQUIDITY.value,
            HealthDimension.VALUATION.value,
            HealthDimension.DIVERSIFICATION.value,
            HealthDimension.VOLATILITY.value,
            HealthDimension.TREND.value,
        ]
        
        for i, dim_name in enumerate(dimensions):
            empty_score = DimensionScore(name=dim_name)
            card = DimensionDetailCard(empty_score)
            row = i // 2
            col = i % 2
            dimensions_layout.addWidget(card, row, col)
            self._dimension_cards[dim_name] = card
        
        right_layout.addWidget(dimensions_group)

        suggestions_group = QGroupBox("优化建议")
        suggestions_layout = QVBoxLayout(suggestions_group)
        
        self._suggestions_scroll = QScrollArea()
        self._suggestions_scroll.setWidgetResizable(True)
        self._suggestions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self._suggestions_container = QWidget()
        self._suggestions_container_layout = QVBoxLayout(self._suggestions_container)
        self._suggestions_container_layout.setSpacing(10)
        self._suggestions_container_layout.addStretch()
        
        self._suggestions_scroll.setWidget(self._suggestions_container)
        suggestions_layout.addWidget(self._suggestions_scroll)
        
        right_layout.addWidget(suggestions_group, 1)

        main_splitter.addWidget(right_widget)

        main_splitter.setSizes([500, 500])
        layout.addWidget(main_splitter, 1)

        self._update_stock_count()

    def _init_connections(self):
        self._analyze_btn.clicked.connect(self._start_analysis)
        self._refresh_history_btn.clicked.connect(self._load_history)
        self._watchlist_manager.add_update_callback(self._update_stock_count)

    def _update_stock_count(self):
        count = len(self._watchlist_manager.watchlist)
        self._stock_count_label.setText(str(count))
        
        if count == 0:
            self._status_label.setText("请先添加股票到自选股")
            self._analyze_btn.setEnabled(False)
        else:
            self._status_label.setText(f"已加载 {count} 只股票，点击开始诊断")
            self._analyze_btn.setEnabled(True)

    def _load_history(self):
        history = self._health_analyzer.get_history(days=30)
        self._history_chart.set_history(history)
        
        if history:
            self._status_label.setText(f"已加载 {len(history)} 天历史数据")

    def _start_analysis(self):
        symbols = self._watchlist_manager.watchlist
        if not symbols:
            QMessageBox.warning(self, "提示", "自选股列表为空，请先添加股票")
            return

        if self._analysis_thread and self._analysis_thread.isRunning():
            QMessageBox.information(self, "提示", "诊断正在进行中，请稍候...")
            return

        self._analyze_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(symbols))
        self._progress_bar.setValue(0)
        self._status_label.setText(f"开始诊断 {len(symbols)} 只股票...")

        self._analysis_thread = HealthAnalysisThread(
            self._health_analyzer, symbols
        )
        self._analysis_thread.progress_signal.connect(self._on_analysis_progress)
        self._analysis_thread.finished_signal.connect(self._on_analysis_finished)
        self._analysis_thread.error_signal.connect(self._on_analysis_error)
        self._analysis_thread.start()

    def _on_analysis_progress(self, current: int, total: int, symbol: str):
        self._progress_bar.setValue(current)
        self._status_label.setText(f"正在分析: {symbol} ({current}/{total})")

    def _on_analysis_finished(self, result: PortfolioHealthResult):
        self._analyze_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._current_result = result

        self._display_result(result)

        self._health_analyzer.add_history_record(result)
        self._load_history()

        self._status_label.setText(
            f"诊断完成: 综合评分 {result.weighted_score:.0f}分 ({result.status})"
        )

    def _on_analysis_error(self, error_msg: str):
        self._analyze_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"诊断出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"诊断过程中出错:\n{error_msg}")

    def _display_result(self, result: PortfolioHealthResult):
        self._radar_chart.set_data(result)

        for name, dim_score in result.dimension_scores.items():
            if name in self._dimension_cards:
                old_card = self._dimension_cards[name]
                parent_layout = old_card.parentWidget().layout()
                if parent_layout:
                    index = parent_layout.indexOf(old_card)
                    if index >= 0:
                        row = index // 2
                        col = index % 2
                        
                        parent_layout.removeWidget(old_card)
                        old_card.deleteLater()
                        
                        new_card = DimensionDetailCard(dim_score)
                        parent_layout.addWidget(new_card, row, col)
                        self._dimension_cards[name] = new_card

        for i in reversed(range(self._suggestions_container_layout.count())):
            item = self._suggestions_container_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, SuggestionCard):
                    widget.deleteLater()

        if result.suggestions:
            for suggestion in result.suggestions:
                card = SuggestionCard(suggestion)
                self._suggestions_container_layout.insertWidget(
                    self._suggestions_container_layout.count() - 1, card
                )
        else:
            no_suggestion_label = QLabel("暂无优化建议")
            no_suggestion_label.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 20px;")
            no_suggestion_label.setAlignment(Qt.AlignCenter)
            self._suggestions_container_layout.insertWidget(
                self._suggestions_container_layout.count() - 1, no_suggestion_label
            )

    def refresh(self):
        self._update_stock_count()
        self._load_history()
