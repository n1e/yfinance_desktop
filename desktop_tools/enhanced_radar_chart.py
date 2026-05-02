from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPolygonF, QLinearGradient, QPainterPath
from typing import List, Dict, Any, Optional, Tuple
import math

from .score_calculator import StockScoreResult, ScoreDimension


STOCK_COLORS = [
    QColor(59, 130, 246),
    QColor(34, 197, 94),
    QColor(245, 158, 11),
    QColor(239, 68, 68),
    QColor(147, 51, 234),
]


class SingleRadarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dimensions: List[str] = []
        self._scores: List[float] = []
        self._weights: List[float] = []
        self._total_score: float = 0.0
        self._symbol: str = ''
        self._status: str = ''
        self._color: QColor = QColor(59, 130, 246)
        self.setMinimumSize(300, 300)

    def set_data(
        self,
        result: Optional[StockScoreResult],
        color: Optional[QColor] = None
    ):
        if result is None:
            self._dimensions = []
            self._scores = []
            self._weights = []
            self._total_score = 0.0
            self._symbol = ''
            self._status = ''
        else:
            self._dimensions = []
            self._scores = []
            self._weights = []

            for dim_name, dim_score in result.dimension_scores.items():
                self._dimensions.append(dim_name)
                self._scores.append(dim_score.score)
                self._weights.append(dim_score.weight)

            self._total_score = result.weighted_score
            self._symbol = result.symbol
            self._status = result.status

        if color:
            self._color = color

        self.update()

    def clear(self):
        self._dimensions = []
        self._scores = []
        self._weights = []
        self._total_score = 0.0
        self._symbol = ''
        self._status = ''
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        max_radius = min(center_x, center_y) - 50

        if not self._dimensions:
            self._draw_placeholder(painter, center_x, center_y, max_radius)
            return

        self._draw_grid(painter, center_x, center_y, max_radius)
        self._draw_data(painter, center_x, center_y, max_radius)
        self._draw_labels(painter, center_x, center_y, max_radius)
        self._draw_legend(painter, width, height)

    def _draw_placeholder(self, painter: QPainter, cx: int, cy: int, radius: int):
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setFont(QFont('Microsoft YaHei', 12))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawText(cx - 60, cy - 15, 120, 30, Qt.AlignCenter, '暂无数据')

    def _draw_grid(self, painter: QPainter, cx: int, cy: int, radius: int):
        num_axes = len(self._dimensions)
        num_levels = 5

        painter.setPen(QPen(QColor(220, 220, 220), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)

        for i in range(1, num_levels + 1):
            r = int(radius * i / num_levels)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

            painter.setFont(QFont('Microsoft YaHei', 7))
            painter.setPen(QPen(QColor(180, 180, 180), 1))
            score_label = str(int(100 * i / num_levels))
            painter.drawText(cx + 5, cy - r, 30, 15, Qt.AlignLeft | Qt.AlignVCenter, score_label)

        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.SolidLine))
        for i in range(num_axes):
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            painter.drawLine(cx, cy, x, y)

    def _draw_data(self, painter: QPainter, cx: int, cy: int, radius: int):
        num_axes = len(self._dimensions)
        if num_axes == 0:
            return

        points = []
        for i in range(num_axes):
            score = self._scores[i] if i < len(self._scores) else 0
            r = int(radius * score / 100.0)
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))

        if any(self._scores):
            polygon = QPolygonF()
            for x, y in points:
                polygon.append(QPointF(x, y))

            fill_color = QColor(self._color.red(), self._color.green(),
                               self._color.blue(), 80)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(QPen(self._color, 2, Qt.SolidLine))
            painter.drawPolygon(polygon)

            for x, y in points:
                painter.setBrush(QBrush(self._color))
                painter.setPen(QPen(self._color, 1, Qt.SolidLine))
                painter.drawEllipse(x - 5, y - 5, 10, 10)

    def _draw_labels(self, painter: QPainter, cx: int, cy: int, radius: int):
        num_axes = len(self._dimensions)
        label_radius = radius + 25

        painter.setFont(QFont('Microsoft YaHei', 8))
        painter.setPen(QPen(QColor(60, 60, 60), 1))

        for i in range(num_axes):
            name = self._dimensions[i]
            score = self._scores[i] if i < len(self._scores) else 0
            weight = self._weights[i] if i < len(self._weights) else 0

            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(label_radius * math.cos(angle))
            y = cy + int(label_radius * math.sin(angle))

            text = f'{name}\n{int(score)}分 ({int(weight*100)}%)'

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

            if align & Qt.AlignLeft:
                draw_x = x
            elif align & Qt.AlignRight:
                draw_x = x - 80
            else:
                draw_x = x - 40

            if align & Qt.AlignTop:
                draw_y = y
            elif align & Qt.AlignBottom:
                draw_y = y - 40
            else:
                draw_y = y - 20

            painter.drawText(draw_x, draw_y, 80, 40,
                           Qt.AlignCenter | Qt.TextWordWrap, text)

    def _draw_legend(self, painter: QPainter, width: int, height: int):
        if self._total_score <= 0 and not self._symbol:
            return

        painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
        painter.setPen(QPen(self._color, 1))

        legend_text = f'{self._symbol}: {int(self._total_score)}分'
        if self._status:
            legend_text += f' ({self._status})'

        painter.drawText(0, height - 30, width, 25, Qt.AlignCenter, legend_text)


class MultiRadarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: Dict[str, Optional[StockScoreResult]] = {}
        self._colors: Dict[str, QColor] = {}
        self._common_dimensions: List[str] = []
        self.setMinimumSize(600, 500)

    def set_results(self, results: Dict[str, Optional[StockScoreResult]]):
        self._results = results.copy()

        all_dimensions = set()
        for symbol, result in results.items():
            if result:
                for dim_name in result.dimension_scores.keys():
                    all_dimensions.add(dim_name)

        self._common_dimensions = list(all_dimensions)

        symbols = list(results.keys())
        for i, symbol in enumerate(symbols):
            self._colors[symbol] = STOCK_COLORS[i % len(STOCK_COLORS)]

        self.update()

    def clear(self):
        self._results = {}
        self._colors = {}
        self._common_dimensions = []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        if not self._results or not self._common_dimensions:
            self._draw_placeholder(painter, width, height)
            return

        num_stocks = len(self._results)
        num_axes = len(self._common_dimensions)

        legend_height = 50
        chart_height = height - legend_height - 20

        chart_width = width - 40
        chart_x = 20
        chart_y = 20

        cx = chart_x + chart_width // 2
        cy = chart_y + chart_height // 2
        radius = min(chart_width, chart_height) // 2 - 30

        self._draw_grid(painter, cx, cy, radius, num_axes)

        for symbol, result in self._results.items():
            if result:
                color = self._colors.get(symbol, STOCK_COLORS[0])
                self._draw_stock_data(painter, cx, cy, radius, result, color)

        self._draw_labels(painter, cx, cy, radius)
        self._draw_legend(painter, width, height)

    def _draw_placeholder(self, painter: QPainter, width: int, height: int):
        painter.setFont(QFont('Microsoft YaHei', 12))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawText(0, 0, width, height, Qt.AlignCenter, '请选择股票进行对比')

    def _draw_grid(self, painter: QPainter, cx: int, cy: int, radius: int, num_axes: int):
        num_levels = 5

        painter.setPen(QPen(QColor(230, 230, 230), 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)

        for i in range(1, num_levels + 1):
            r = int(radius * i / num_levels)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.setPen(QPen(QColor(180, 180, 180), 1))
            score_label = str(int(100 * i / num_levels))
            painter.drawText(cx + 5, cy - r, 30, 15, Qt.AlignLeft | Qt.AlignVCenter, score_label)

        painter.setPen(QPen(QColor(210, 210, 210), 1, Qt.SolidLine))
        for i in range(num_axes):
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            painter.drawLine(cx, cy, x, y)

    def _draw_stock_data(
        self,
        painter: QPainter,
        cx: int, cy: int, radius: int,
        result: StockScoreResult,
        color: QColor
    ):
        num_axes = len(self._common_dimensions)
        if num_axes == 0:
            return

        points = []
        valid_points = []

        for i, dim_name in enumerate(self._common_dimensions):
            dim_score = result.dimension_scores.get(dim_name)
            score = dim_score.score if dim_score else 0
            r = int(radius * score / 100.0)
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))
            valid_points.append(score > 0)

        if any(valid_points):
            polygon = QPolygonF()
            for x, y in points:
                polygon.append(QPointF(x, y))

            fill_color = QColor(color.red(), color.green(), color.blue(), 50)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(QPen(color, 2, Qt.SolidLine))
            painter.drawPolygon(polygon)

            for i, (x, y) in enumerate(points):
                if valid_points[i]:
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(color, 1, Qt.SolidLine))
                    painter.drawEllipse(x - 4, y - 4, 8, 8)

    def _draw_labels(self, painter: QPainter, cx: int, cy: int, radius: int):
        num_axes = len(self._common_dimensions)
        label_radius = radius + 30

        painter.setFont(QFont('Microsoft YaHei', 9))
        painter.setPen(QPen(QColor(60, 60, 60), 1))

        for i, name in enumerate(self._common_dimensions):
            angle = (i * 2 * math.pi / num_axes) - math.pi / 2
            x = cx + int(label_radius * math.cos(angle))
            y = cy + int(label_radius * math.sin(angle))

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

            if align & Qt.AlignLeft:
                draw_x = x
            elif align & Qt.AlignRight:
                draw_x = x - 70
            else:
                draw_x = x - 35

            if align & Qt.AlignTop:
                draw_y = y
            elif align & Qt.AlignBottom:
                draw_y = y - 20
            else:
                draw_y = y - 10

            painter.drawText(draw_x, draw_y, 70, 20,
                           Qt.AlignCenter, name)

    def _draw_legend(self, painter: QPainter, width: int, height: int):
        legend_y = height - 40
        spacing = 150
        start_x = 20

        painter.setFont(QFont('Microsoft YaHei', 10))

        i = 0
        for symbol, result in self._results.items():
            if result:
                x = start_x + i * spacing
                color = self._colors.get(symbol, STOCK_COLORS[0])

                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color, 1))
                painter.drawRect(x, legend_y, 20, 15)

                painter.setPen(QPen(QColor(60, 60, 60), 1))
                legend_text = f'{symbol}: {int(result.weighted_score)}分'
                painter.drawText(x + 25, legend_y - 2, 120, 20,
                               Qt.AlignLeft | Qt.AlignVCenter, legend_text)
                i += 1


class ScoreBarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: Dict[str, Optional[StockScoreResult]] = {}
        self._dimension: str = ''
        self.setMinimumSize(400, 300)

    def set_data(self, results: Dict[str, Optional[StockScoreResult]], dimension: str):
        self._results = results.copy()
        self._dimension = dimension
        self.update()

    def clear(self):
        self._results = {}
        self._dimension = ''
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        if not self._results or not self._dimension:
            return

        margin_left = 80
        margin_right = 30
        margin_top = 40
        margin_bottom = 50

        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        valid_results = {s: r for s, r in self._results.items() if r}
        if not valid_results:
            return

        symbols = list(valid_results.keys())
        symbols.sort(key=lambda s: (
            valid_results[s].dimension_scores.get(self._dimension, type('obj', (), {'score': 0})).score
            if valid_results[s] else 0
        ), reverse=True)

        num_stocks = len(symbols)
        bar_height = chart_height / (num_stocks * 2 + 1)
        bar_gap = bar_height

        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setFont(QFont('Microsoft YaHei', 9))
        for i in range(0, 101, 20):
            x = margin_left + int(chart_width * i / 100)
            painter.drawLine(x, margin_top, x, height - margin_bottom)
            painter.drawText(x - 20, height - margin_bottom + 5, 40, 20,
                           Qt.AlignCenter, str(i))

        painter.setFont(QFont('Microsoft YaHei', 10))
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawText(margin_left, 10, chart_width, 25,
                        Qt.AlignCenter, f'{self._dimension} 对比')

        for idx, symbol in enumerate(symbols):
            result = valid_results[symbol]
            dim_score = result.dimension_scores.get(self._dimension)
            score = dim_score.score if dim_score else 0

            bar_y = margin_top + int(bar_gap + idx * (bar_height + bar_gap))

            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.drawText(margin_left - 75, bar_y, 70, int(bar_height),
                            Qt.AlignRight | Qt.AlignVCenter, symbol)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(230, 230, 230)))
            painter.drawRoundedRect(margin_left, bar_y + 2, chart_width, int(bar_height) - 4, 3, 3)

            bar_width = int(chart_width * score / 100)
            if bar_width > 0:
                color_idx = idx % len(STOCK_COLORS)
                bar_color = STOCK_COLORS[color_idx]
                painter.setBrush(QBrush(bar_color))
                painter.drawRoundedRect(margin_left, bar_y + 2, bar_width, int(bar_height) - 4, 3, 3)

            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            painter.drawText(margin_left + bar_width + 5, bar_y, 50, int(bar_height),
                            Qt.AlignLeft | Qt.AlignVCenter, f'{int(score)}分')


class ScoreDetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: Optional[StockScoreResult] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self._header_label = QLabel("评分明细")
        self._header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        layout.addWidget(self._header_label)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setSpacing(10)

        self._scroll_area.setWidget(self._content_widget)
        layout.addWidget(self._scroll_area, 1)

    def set_result(self, result: Optional[StockScoreResult]):
        self._result = result
        self._update_display()

    def _update_display(self):
        for i in reversed(range(self._content_layout.count())):
            item = self._content_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

        if not self._result:
            no_data_label = QLabel("暂无评分数据")
            no_data_label.setStyleSheet("color: #888; font-size: 12px; padding: 20px;")
            no_data_label.setAlignment(Qt.AlignCenter)
            self._content_layout.addWidget(no_data_label)
            return

        for dim_name, dim_score in self._result.dimension_scores.items():
            group = QGroupBox(f"{dim_name} - {int(dim_score.score)}分 (权重: {int(dim_score.weight*100)}%)")
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """)

            group_layout = QVBoxLayout(group)
            group_layout.setSpacing(5)

            if dim_score.details:
                summary = dim_score.details.get('summary', '')
                if summary:
                    summary_label = QLabel(f"摘要: {summary}")
                    summary_label.setStyleSheet("color: #555; font-size: 11px;")
                    summary_label.setWordWrap(True)
                    group_layout.addWidget(summary_label)

                indicators = dim_score.details.get('indicators', {})
                if indicators:
                    indicators_group = QFrame()
                    indicators_layout = QVBoxLayout(indicators_group)
                    indicators_layout.setSpacing(3)
                    indicators_layout.setContentsMargins(10, 5, 10, 5)

                    for key, value in indicators.items():
                        ind_label = QLabel(f"  • {key}: {value}")
                        ind_label.setStyleSheet("color: #666; font-size: 11px;")
                        indicators_layout.addWidget(ind_label)

                    group_layout.addWidget(indicators_group)

                signals = dim_score.details.get('signals', [])
                if signals:
                    signals_label = QLabel("信号: " + " | ".join(signals))
                    signals_label.setStyleSheet("color: #4a90d9; font-size: 11px;")
                    signals_label.setWordWrap(True)
                    group_layout.addWidget(signals_label)

                buy_signals = dim_score.details.get('buy_signals', [])
                sell_signals = dim_score.details.get('sell_signals', [])
                neutral_signals = dim_score.details.get('neutral_signals', [])

                if buy_signals:
                    buy_label = QLabel(f"买入信号 ({len(buy_signals)}): " + " | ".join(buy_signals[:3]))
                    buy_label.setStyleSheet("color: #22c55e; font-size: 11px;")
                    buy_label.setWordWrap(True)
                    group_layout.addWidget(buy_label)

                if sell_signals:
                    sell_label = QLabel(f"卖出信号 ({len(sell_signals)}): " + " | ".join(sell_signals[:3]))
                    sell_label.setStyleSheet("color: #ef4444; font-size: 11px;")
                    sell_label.setWordWrap(True)
                    group_layout.addWidget(sell_label)

                if neutral_signals:
                    neutral_label = QLabel(f"中性信号: " + " | ".join(neutral_signals[:3]))
                    neutral_label.setStyleSheet("color: #eab308; font-size: 11px;")
                    neutral_label.setWordWrap(True)
                    group_layout.addWidget(neutral_label)

            metrics = dim_score.raw_metrics
            if metrics:
                metrics_text = "原始指标: "
                metric_items = []
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        if abs(value) > 1000:
                            metric_items.append(f"{key}: {value:,.0f}")
                        elif abs(value) < 1:
                            metric_items.append(f"{key}: {value:.4f}")
                        else:
                            metric_items.append(f"{key}: {value:.2f}")
                    elif isinstance(value, list) and len(value) > 0:
                        metric_items.append(f"{key}: [...{len(value)}项]")

                if metric_items:
                    metrics_label = QLabel(metrics_text + " | ".join(metric_items[:5]))
                    metrics_label.setStyleSheet("color: #888; font-size: 10px;")
                    metrics_label.setWordWrap(True)
                    group_layout.addWidget(metrics_label)

            group_layout.addStretch()
            self._content_layout.addWidget(group)

        self._content_layout.addStretch()


class WeightConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._weights: Dict[str, float] = {}
        self._default_weights: Dict[str, float] = {}
        self._dimensions: List[str] = []
        self._init_ui()

    def _init_ui(self):
        from PyQt5.QtWidgets import (
            QFormLayout, QDoubleSpinBox, QPushButton,
            QLabel, QHBoxLayout
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_label = QLabel("维度权重设置")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self._reset_btn = QPushButton("恢复默认")
        self._reset_btn.setMaximumWidth(100)
        self._reset_btn.clicked.connect(self._reset_weights)
        header_layout.addWidget(self._reset_btn)

        layout.addLayout(header_layout)

        self._form_layout = QFormLayout()
        self._form_layout.setSpacing(10)
        layout.addLayout(self._form_layout)

        self._total_label = QLabel("总权重: 100%")
        self._total_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self._total_label)

        layout.addStretch()

    def set_dimensions(self, dimensions: List[str], weights: Dict[str, float]):
        self._dimensions = dimensions.copy()
        self._weights = weights.copy()
        self._default_weights = weights.copy()
        self._update_ui()

    def _update_ui(self):
        for i in reversed(range(self._form_layout.count())):
            self._form_layout.itemAt(i).widget().setParent(None)

        from PyQt5.QtWidgets import QDoubleSpinBox

        self._spin_boxes: Dict[str, QDoubleSpinBox] = {}

        for dim_name in self._dimensions:
            weight = self._weights.get(dim_name, 0.0)

            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.05)
            spin.setValue(weight)
            spin.setDecimals(2)
            spin.setSuffix("  (权重)")
            spin.valueChanged.connect(lambda v, d=dim_name: self._on_weight_changed(d, v))

            self._form_layout.addRow(f"{dim_name}:", spin)
            self._spin_boxes[dim_name] = spin

        self._update_total()

    def _on_weight_changed(self, dimension: str, value: float):
        self._weights[dimension] = value
        self._update_total()

    def _update_total(self):
        total = sum(self._weights.values())
        self._total_label.setText(f"总权重: {total*100:.0f}%")

        if abs(total - 1.0) > 0.01:
            self._total_label.setStyleSheet("font-weight: bold; color: #ef4444;")
        else:
            self._total_label.setStyleSheet("font-weight: bold; color: #22c55e;")

    def _reset_weights(self):
        self._weights = self._default_weights.copy()
        self._update_ui()

    def get_weights(self) -> Dict[str, float]:
        return self._weights.copy()

    def get_normalized_weights(self) -> Dict[str, float]:
        total = sum(self._weights.values())
        if abs(total - 1.0) > 0.001 and total > 0:
            return {k: v / total for k, v in self._weights.items()}
        return self._weights.copy()
