from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QLabel,
    QSplitter, QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class PositionPnLData:
    symbol: str
    name: str
    quantity: int
    cost_price: float
    current_price: float
    cost_value: float
    current_value: float
    pnl_amount: float
    pnl_percent: float
    contribution_percent: float = 0.0


class PnLAnalyzer:
    def __init__(self, watchlist_manager):
        self._watchlist = watchlist_manager

    def get_position_pnl_data(self) -> List[PositionPnLData]:
        quotes = self._watchlist.get_sorted_quotes()
        portfolio_data = []
        total_pnl = 0.0

        for quote in quotes:
            pnl = quote.get('pnl', {})
            if pnl.get('has_position', False):
                position_data = PositionPnLData(
                    symbol=quote.get('symbol', ''),
                    name=quote.get('name', quote.get('symbol', '')),
                    quantity=pnl.get('quantity', 0),
                    cost_price=pnl.get('cost_price', 0.0),
                    current_price=pnl.get('current_price', 0.0),
                    cost_value=pnl.get('cost_value', 0.0),
                    current_value=pnl.get('current_value', 0.0),
                    pnl_amount=pnl.get('pnl_amount', 0.0),
                    pnl_percent=pnl.get('pnl_percent', 0.0)
                )
                portfolio_data.append(position_data)
                total_pnl += position_data.pnl_amount

        for data in portfolio_data:
            if total_pnl != 0:
                data.contribution_percent = (data.pnl_amount / abs(total_pnl)) * 100
            else:
                data.contribution_percent = 0.0

        return portfolio_data

    def get_portfolio_stats(self) -> Dict[str, Any]:
        total_cost = 0.0
        total_value = 0.0
        total_pnl = 0.0
        position_count = 0

        data = self.get_position_pnl_data()
        for item in data:
            total_cost += item.cost_value
            total_value += item.current_value
            total_pnl += item.pnl_amount
            position_count += 1

        pnl_percent = 0.0
        if total_cost > 0:
            pnl_percent = (total_pnl / total_cost) * 100

        return {
            'total_cost': total_cost,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'position_count': position_count
        }

    def get_pnl_distribution(self) -> Dict[str, Any]:
        data = self.get_position_pnl_data()
        if not data:
            return {'bins': [], 'counts': [], 'min': 0, 'max': 0}

        pnl_percents = [item.pnl_percent for item in data]
        min_pnl = min(pnl_percents)
        max_pnl = max(pnl_percents)

        if min_pnl == max_pnl:
            min_pnl -= 5
            max_pnl += 5

        bin_count = min(10, len(data))
        if bin_count < 1:
            bin_count = 1

        bin_width = (max_pnl - min_pnl) / bin_count
        bins = []
        counts = [0] * bin_count

        for i in range(bin_count):
            bin_start = min_pnl + i * bin_width
            bin_end = min_pnl + (i + 1) * bin_width
            bins.append((bin_start, bin_end))

        for pnl in pnl_percents:
            bin_idx = min(int((pnl - min_pnl) / bin_width), bin_count - 1)
            counts[bin_idx] += 1

        return {
            'bins': bins,
            'counts': counts,
            'min': min_pnl,
            'max': max_pnl,
            'bin_width': bin_width
        }


class BaseChartWidget(QWidget):
    COLOR_RED = QColor(239, 68, 68)
    COLOR_GREEN = QColor(34, 197, 94)
    COLOR_BLUE = QColor(59, 130, 246)
    COLOR_ORANGE = QColor(251, 146, 60)
    COLOR_PURPLE = QColor(168, 85, 247)
    COLOR_GRAY = QColor(107, 114, 128)
    COLOR_LIGHT_GRAY = QColor(229, 231, 235)
    COLOR_DARK_GRAY = QColor(55, 65, 81)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = "图表"
        self._data: Optional[Any] = None
        self._highlighted_symbol: Optional[str] = None
        self.setMinimumSize(400, 300)
        self.setMinimumHeight(250)

    def set_title(self, title: str):
        self._title = title
        self.update()

    def set_data(self, data: Any):
        self._data = data
        self.update()

    def set_highlighted_symbol(self, symbol: str):
        self._highlighted_symbol = symbol
        self.update()

    def clear_highlight(self):
        self._highlighted_symbol = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        self._draw_background(painter, width, height)
        self._draw_title(painter, width, height)

        if self._data is None or not self._has_valid_data():
            self._draw_placeholder(painter, width, height)
            return

        chart_rect = QRectF(60, 40, width - 70, height - 60)
        self._draw_chart(painter, chart_rect)

    def _draw_background(self, painter: QPainter, width: int, height: int):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(0, 0, width, height)

    def _draw_title(self, painter: QPainter, width: int, height: int):
        painter.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
        painter.drawText(15, 25, self._title)

    def _draw_placeholder(self, painter: QPainter, width: int, height: int):
        painter.setFont(QFont('Microsoft YaHei', 12))
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(0, 0, width, height, Qt.AlignCenter, '暂无持仓数据\n请在自选股中设置持仓信息')

    def _has_valid_data(self) -> bool:
        if self._data is None:
            return False
        if isinstance(self._data, list) and len(self._data) == 0:
            return False
        if isinstance(self._data, dict):
            if 'bins' in self._data and not self._data.get('bins'):
                return False
        return True

    def _draw_chart(self, painter: QPainter, rect: QRectF):
        pass

    def _get_color_for_pnl(self, pnl: float) -> QColor:
        if pnl > 0:
            return self.COLOR_GREEN
        elif pnl < 0:
            return self.COLOR_RED
        return self.COLOR_GRAY

    def _draw_grid(self, painter: QPainter, rect: QRectF, y_min: float, y_max: float, levels: int = 5):
        painter.setPen(QPen(self.COLOR_LIGHT_GRAY, 1, Qt.SolidLine))

        for i in range(levels + 1):
            y = int(rect.top() + rect.height() * i / levels)
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

            value = y_max - (y_max - y_min) * i / levels
            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(
                int(rect.left() - 55), int(y - 6), 50, 12,
                Qt.AlignRight | Qt.AlignVCenter,
                self._format_value(value)
            )

    def _format_value(self, value: float) -> str:
        if abs(value) >= 1e9:
            return f"{value/1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"{value/1e6:.2f}M"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.2f}K"
        elif abs(value) < 1 and abs(value) > 0:
            return f"{value:.2f}"
        else:
            return f"{value:.0f}"

    def _format_percent(self, value: float) -> str:
        return f"{value:+.1f}%"


class PnLHistogramWidget(BaseChartWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("盈亏分布直方图")

    def _draw_chart(self, painter: QPainter, rect: QRectF):
        dist = self._data
        if not dist or not dist.get('bins'):
            return

        bins = dist['bins']
        counts = dist['counts']
        if not counts:
            return

        max_count = max(counts) if counts else 0
        if max_count == 0:
            max_count = 1

        self._draw_grid(painter, rect, 0, max_count, min(5, max_count))

        bin_count = len(bins)
        if bin_count == 0:
            return

        x_step = rect.width() / bin_count
        bar_width = x_step * 0.8

        for i, ((bin_start, bin_end), count) in enumerate(zip(bins, counts)):
            x = rect.left() + i * x_step + (x_step - bar_width) / 2
            bar_height = (count / max_count) * rect.height() if max_count > 0 else 0

            bin_mid = (bin_start + bin_end) / 2
            color = self._get_color_for_pnl(bin_mid)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(
                int(x),
                int(rect.bottom() - bar_height),
                int(bar_width),
                int(bar_height)
            )

            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.setFont(QFont('Microsoft YaHei', 8))
            label = self._format_percent(bin_mid)
            painter.drawText(
                int(x), int(rect.bottom() + 15),
                int(bar_width), 15,
                Qt.AlignCenter, label
            )

            if count > 0:
                painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
                painter.drawText(
                    int(x), int(rect.bottom() - bar_height - 18),
                    int(bar_width), 15,
                    Qt.AlignCenter, f"{count}只"
                )


class BubbleChartWidget(BaseChartWidget):
    bubble_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("盈亏/市值气泡图")
        self._bubble_positions: List[Tuple[str, QPointF, float]] = []

    def _draw_chart(self, painter: QPainter, rect: QRectF):
        data: List[PositionPnLData] = self._data
        if not data:
            return

        self._bubble_positions = []

        pnl_percents = [d.pnl_percent for d in data]
        current_values = [d.current_value for d in data]
        quantities = [d.quantity for d in data]

        x_min, x_max = min(pnl_percents), max(pnl_percents)
        y_min, y_max = min(current_values), max(current_values)
        size_min, size_max = min(quantities), max(quantities)

        if x_max == x_min:
            x_min -= 5
            x_max += 5
        if y_max == y_min:
            y_min -= max(1, y_min * 0.1)
            y_max += max(1, y_max * 0.1)

        x_padding = (x_max - x_min) * 0.1
        y_padding = (y_max - y_min) * 0.1
        x_min -= x_padding
        x_max += x_padding
        y_min -= y_padding
        y_max += y_padding

        self._draw_axes(painter, rect, x_min, x_max, y_min, y_max)

        min_size = 15
        max_size = 60

        zero_x = rect.left() + (0 - x_min) / (x_max - x_min) * rect.width()
        if rect.left() <= zero_x <= rect.right():
            painter.setPen(QPen(self.COLOR_GRAY, 1, Qt.DashLine))
            painter.drawLine(int(zero_x), int(rect.top()), int(zero_x), int(rect.bottom()))

        for item in data:
            x = rect.left() + (item.pnl_percent - x_min) / (x_max - x_min) * rect.width()
            y = rect.bottom() - (item.current_value - y_min) / (y_max - y_min) * rect.height()

            if size_max == size_min:
                bubble_size = (min_size + max_size) / 2
            else:
                size_ratio = (item.quantity - size_min) / (size_max - size_min)
                bubble_size = min_size + size_ratio * (max_size - min_size)

            color = self._get_color_for_pnl(item.pnl_percent)
            
            is_highlighted = self._highlighted_symbol == item.symbol
            
            self._bubble_positions.append((item.symbol, QPointF(x, y), bubble_size))

            if is_highlighted:
                painter.setPen(QPen(self.COLOR_PURPLE, 3))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(int(x - bubble_size/2 - 3), int(y - bubble_size/2 - 3), int(bubble_size + 6), int(bubble_size + 6))
            else:
                painter.setPen(QPen(color.lighter(120), 2))
                painter.setBrush(QBrush(color))
            
            painter.setOpacity(0.7)
            painter.drawEllipse(int(x - bubble_size/2), int(y - bubble_size/2), int(bubble_size), int(bubble_size))
            painter.setOpacity(1.0)

            painter.setPen(QPen(Qt.white, 1))
            painter.setFont(QFont('Microsoft YaHei', 8, QFont.Bold))
            symbol_text = item.symbol[:4]
            painter.drawText(
                int(x - bubble_size/2), int(y - bubble_size/2),
                int(bubble_size), int(bubble_size),
                Qt.AlignCenter, symbol_text
            )

    def _draw_axes(self, painter: QPainter, rect: QRectF, x_min: float, x_max: float, y_min: float, y_max: float):
        painter.setPen(QPen(self.COLOR_GRAY, 1, Qt.SolidLine))
        
        painter.drawLine(int(rect.left()), int(rect.bottom()), int(rect.right()), int(rect.bottom()))
        painter.drawLine(int(rect.left()), int(rect.top()), int(rect.left()), int(rect.bottom()))

        painter.setFont(QFont('Microsoft YaHei', 9))
        painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
        painter.drawText(int(rect.left()), int(rect.bottom() + 30), "盈亏率 (%)")
        painter.save()
        painter.translate(int(rect.left() - 45), int(rect.top() + rect.height()/2))
        painter.rotate(-90)
        painter.drawText(0, 0, "持仓市值")
        painter.restore()

        painter.setFont(QFont('Microsoft YaHei', 8))
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        
        x_steps = 5
        for i in range(x_steps + 1):
            x_val = x_min + (x_max - x_min) * i / x_steps
            x = rect.left() + rect.width() * i / x_steps
            painter.drawLine(int(x), int(rect.bottom()), int(x), int(rect.bottom() + 5))
            painter.drawText(int(x) - 25, int(rect.bottom() + 10), 50, 15, Qt.AlignCenter, self._format_percent(x_val))

        y_steps = 5
        for i in range(y_steps + 1):
            y_val = y_max - (y_max - y_min) * i / y_steps
            y = rect.top() + rect.height() * i / y_steps
            painter.drawLine(int(rect.left() - 5), int(y), int(rect.left()), int(y))
            painter.drawText(int(rect.left() - 55), int(y) - 7, 50, 14, Qt.AlignRight | Qt.AlignVCenter, self._format_value(y_val))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_pos = event.pos()
            for symbol, center, size in self._bubble_positions:
                distance = math.sqrt((click_pos.x() - center.x())**2 + (click_pos.y() - center.y())**2)
                if distance <= size / 2:
                    self.bubble_clicked.emit(symbol)
                    break
        super().mousePressEvent(event)


class WaterfallChartWidget(BaseChartWidget):
    item_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("贡献度瀑布图")
        self._bar_positions: List[Tuple[str, QRectF]] = []

    def _draw_chart(self, painter: QPainter, rect: QRectF):
        data: List[PositionPnLData] = self._data
        if not data:
            return

        self._bar_positions = []

        sorted_data = sorted(data, key=lambda x: x.pnl_amount, reverse=True)

        total_pnl = sum(d.pnl_amount for d in data)

        all_values = []
        cumulative = 0
        for d in sorted_data:
            all_values.append(cumulative)
            cumulative += d.pnl_amount
            all_values.append(cumulative)
        all_values.append(total_pnl)

        y_min = min(all_values) if all_values else 0
        y_max = max(all_values) if all_values else 0

        if y_max == y_min:
            y_min -= 1
            y_max += 1

        y_padding = (y_max - y_min) * 0.1
        y_min -= y_padding
        y_max += y_padding

        self._draw_grid(painter, rect, y_min, y_max)

        bar_count = len(sorted_data) + 1
        x_step = rect.width() / bar_count
        bar_width = x_step * 0.6

        zero_y = rect.bottom() - (0 - y_min) / (y_max - y_min) * rect.height()

        cumulative = 0
        for i, item in enumerate(sorted_data):
            start_y = rect.bottom() - (cumulative - y_min) / (y_max - y_min) * rect.height()
            bar_height = (item.pnl_amount / (y_max - y_min)) * rect.height() if (y_max - y_min) != 0 else 0

            x = rect.left() + i * x_step + (x_step - bar_width) / 2

            color = self._get_color_for_pnl(item.pnl_amount)
            is_highlighted = self._highlighted_symbol == item.symbol

            if bar_height > 0:
                bar_rect = QRectF(x, start_y - abs(bar_height), bar_width, abs(bar_height))
            else:
                bar_rect = QRectF(x, start_y, bar_width, abs(bar_height))

            self._bar_positions.append((item.symbol, bar_rect))

            if is_highlighted:
                painter.setPen(QPen(self.COLOR_PURPLE, 3))
            else:
                painter.setPen(QPen(color.lighter(120), 1))

            painter.setBrush(QBrush(color))
            painter.setOpacity(0.8)
            painter.drawRect(int(bar_rect.left()), int(bar_rect.top()), int(bar_rect.width()), int(bar_rect.height()))
            painter.setOpacity(1.0)

            if i > 0 or cumulative != 0:
                painter.setPen(QPen(self.COLOR_GRAY, 1, Qt.DashLine))
                painter.drawLine(int(rect.left() + i * x_step), int(start_y), int(x), int(start_y))

            painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.drawText(int(x), int(rect.bottom() + 10), int(bar_width), 15, Qt.AlignCenter, item.symbol[:5])

            pnl_text = f"{item.pnl_amount:+.0f}" if abs(item.pnl_amount) < 1000 else f"{item.pnl_amount/1000:+.1f}K"
            if bar_height > 0:
                painter.drawText(int(x), int(bar_rect.top() - 18), int(bar_width), 15, Qt.AlignCenter, pnl_text)
            else:
                painter.drawText(int(x), int(bar_rect.bottom() + 3), int(bar_width), 15, Qt.AlignCenter, pnl_text)

            cumulative += item.pnl_amount

        total_x = rect.left() + (bar_count - 1) * x_step + (x_step - bar_width) / 2
        total_height = (total_pnl / (y_max - y_min)) * rect.height() if (y_max - y_min) != 0 else 0

        if total_height > 0:
            total_rect = QRectF(total_x, zero_y - abs(total_height), bar_width, abs(total_height))
        else:
            total_rect = QRectF(total_x, zero_y, bar_width, abs(total_height))

        total_color = self._get_color_for_pnl(total_pnl)
        painter.setPen(QPen(total_color.lighter(120), 1))
        painter.setBrush(QBrush(total_color))
        painter.setOpacity(0.9)
        painter.drawRect(int(total_rect.left()), int(total_rect.top()), int(total_rect.width()), int(total_rect.height()))
        painter.setOpacity(1.0)

        painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
        painter.setFont(QFont('Microsoft YaHei', 8, QFont.Bold))
        painter.drawText(int(total_x), int(rect.bottom() + 10), int(bar_width), 15, Qt.AlignCenter, "合计")

        total_text = f"${total_pnl:+,.0f}" if abs(total_pnl) < 10000 else f"${total_pnl/1000:+.1f}K"
        if total_height > 0:
            painter.drawText(int(total_x), int(total_rect.top() - 18), int(bar_width), 15, Qt.AlignCenter, total_text)
        else:
            painter.drawText(int(total_x), int(total_rect.bottom() + 3), int(bar_width), 15, Qt.AlignCenter, total_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_pos = event.pos()
            for symbol, rect in self._bar_positions:
                if rect.contains(click_pos):
                    self.item_clicked.emit(symbol)
                    break
        super().mousePressEvent(event)


class PriceComparisonChartWidget(BaseChartWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("成本价与现价对比图")

    def _draw_chart(self, painter: QPainter, rect: QRectF):
        data: List[PositionPnLData] = self._data
        if not data:
            return

        sorted_data = sorted(data, key=lambda x: x.current_price, reverse=True)

        all_prices = []
        for d in sorted_data:
            all_prices.append(d.cost_price)
            all_prices.append(d.current_price)

        y_min = min(all_prices) if all_prices else 0
        y_max = max(all_prices) if all_prices else 0

        if y_max == y_min:
            y_min -= 1
            y_max += 1

        y_padding = (y_max - y_min) * 0.1
        y_min -= y_padding
        y_max += y_padding

        self._draw_grid(painter, rect, y_min, y_max)

        bar_count = len(sorted_data)
        x_step = rect.width() / bar_count
        bar_width = x_step * 0.35

        for i, item in enumerate(sorted_data):
            x = rect.left() + i * x_step

            cost_x = x + (x_step - 2 * bar_width) / 3
            current_x = cost_x + bar_width + (x_step - 2 * bar_width) / 3

            is_highlighted = self._highlighted_symbol == item.symbol

            cost_height = (item.cost_price - y_min) / (y_max - y_min) * rect.height() if (y_max - y_min) != 0 else 0
            cost_y = rect.bottom() - cost_height

            if is_highlighted:
                painter.setPen(QPen(self.COLOR_PURPLE, 2))
            else:
                painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.setBrush(QBrush(self.COLOR_ORANGE))
            painter.setOpacity(0.8)
            painter.drawRect(int(cost_x), int(cost_y), int(bar_width), int(cost_height))
            painter.setOpacity(1.0)

            current_height = (item.current_price - y_min) / (y_max - y_min) * rect.height() if (y_max - y_min) != 0 else 0
            current_y = rect.bottom() - current_height

            current_color = self._get_color_for_pnl(item.pnl_amount)
            if is_highlighted:
                painter.setPen(QPen(self.COLOR_PURPLE, 2))
            else:
                painter.setPen(QPen(current_color.lighter(120), 1))
            painter.setBrush(QBrush(current_color))
            painter.setOpacity(0.8)
            painter.drawRect(int(current_x), int(current_y), int(bar_width), int(current_height))
            painter.setOpacity(1.0)

            painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.drawText(int(x), int(rect.bottom() + 10), int(x_step), 15, Qt.AlignCenter, item.symbol[:5])

            painter.setFont(QFont('Microsoft YaHei', 7))
            cost_text = f"${item.cost_price:.2f}"
            if cost_height < 30:
                painter.drawText(int(cost_x), int(cost_y - 15), int(bar_width), 12, Qt.AlignCenter, cost_text)
            else:
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(int(cost_x), int(cost_y + 3), int(bar_width), 12, Qt.AlignCenter, cost_text)

            current_text = f"${item.current_price:.2f}"
            if current_height < 30:
                painter.setPen(QPen(self.COLOR_DARK_GRAY, 1))
                painter.drawText(int(current_x), int(current_y - 15), int(bar_width), 12, Qt.AlignCenter, current_text)
            else:
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(int(current_x), int(current_y + 3), int(bar_width), 12, Qt.AlignCenter, current_text)

        legend_y = 10
        painter.setFont(QFont('Microsoft YaHei', 9))
        
        painter.setPen(QPen(self.COLOR_ORANGE, 1))
        painter.setBrush(QBrush(self.COLOR_ORANGE))
        painter.drawRect(int(rect.left()), legend_y, 15, 12)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(int(rect.left() + 20), legend_y + 11, "成本价")

        painter.setPen(QPen(self.COLOR_GREEN, 1))
        painter.setBrush(QBrush(self.COLOR_GREEN))
        painter.drawRect(int(rect.left() + 80), legend_y, 15, 12)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(int(rect.left() + 100), legend_y + 11, "现价(盈利)")

        painter.setPen(QPen(self.COLOR_RED, 1))
        painter.setBrush(QBrush(self.COLOR_RED))
        painter.drawRect(int(rect.left() + 180), legend_y, 15, 12)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(int(rect.left() + 200), legend_y + 11, "现价(亏损)")


class PnLRankingTable(QWidget):
    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._data: List[PositionPnLData] = []
        self._selected_symbol: Optional[str] = None

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("盈亏排名")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(5, 10, 5, 5)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "排名", "股票代码", "名称", "持仓数量", "盈亏金额", "盈亏率", "贡献度"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        group_layout.addWidget(self._table)
        layout.addWidget(group)

    def set_data(self, data: List[PositionPnLData]):
        self._data = sorted(data, key=lambda x: x.pnl_amount, reverse=True)
        self._update_table()

    def _update_table(self):
        self._table.setRowCount(len(self._data))

        green_color = QColor(34, 197, 94)
        red_color = QColor(239, 68, 68)
        black_color = QColor(0, 0, 0)
        highlight_color = QColor(168, 85, 247)

        for row, item in enumerate(self._data):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, rank_item)

            symbol_item = QTableWidgetItem(item.symbol)
            symbol_item.setData(Qt.UserRole, item.symbol)
            self._table.setItem(row, 1, symbol_item)

            name_item = QTableWidgetItem(item.name[:10] if len(item.name) > 10 else item.name)
            self._table.setItem(row, 2, name_item)

            quantity_item = QTableWidgetItem(f"{item.quantity:,}")
            quantity_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 3, quantity_item)

            pnl_amount_text = f"${item.pnl_amount:+,.2f}"
            pnl_amount_item = QTableWidgetItem(pnl_amount_text)
            pnl_amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if item.pnl_amount > 0:
                pnl_amount_item.setForeground(green_color)
            elif item.pnl_amount < 0:
                pnl_amount_item.setForeground(red_color)
            self._table.setItem(row, 4, pnl_amount_item)

            pnl_percent_text = f"{item.pnl_percent:+.2f}%"
            pnl_percent_item = QTableWidgetItem(pnl_percent_text)
            pnl_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if item.pnl_percent > 0:
                pnl_percent_item.setForeground(green_color)
            elif item.pnl_percent < 0:
                pnl_percent_item.setForeground(red_color)
            self._table.setItem(row, 5, pnl_percent_item)

            contrib_text = f"{item.contribution_percent:+.1f}%"
            contrib_item = QTableWidgetItem(contrib_text)
            contrib_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if item.contribution_percent > 0:
                contrib_item.setForeground(green_color)
            elif item.contribution_percent < 0:
                contrib_item.setForeground(red_color)
            self._table.setItem(row, 6, contrib_item)

            if self._selected_symbol == item.symbol:
                for col in range(self._table.columnCount()):
                    cell_item = self._table.item(row, col)
                    if cell_item:
                        cell_item.setBackground(QColor(240, 230, 255))
                        cell_item.setForeground(highlight_color)

    def _on_selection_changed(self):
        selected = self._table.selectedItems()
        if selected:
            row = selected[0].row()
            symbol_item = self._table.item(row, 1)
            if symbol_item:
                symbol = symbol_item.data(Qt.UserRole)
                if symbol:
                    self._selected_symbol = symbol
                    self.item_selected.emit(symbol)

    def set_selected_symbol(self, symbol: str):
        self._selected_symbol = symbol
        for row in range(self._table.rowCount()):
            symbol_item = self._table.item(row, 1)
            if symbol_item and symbol_item.data(Qt.UserRole) == symbol:
                self._table.selectRow(row)
                self._table.scrollToItem(symbol_item)
                break
        self._update_table()

    def clear_selection(self):
        self._selected_symbol = None
        self._table.clearSelection()
        self._update_table()


class PortfolioStatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("组合总体统计")
        group_layout = QHBoxLayout(group)
        group_layout.setSpacing(20)
        group_layout.setContentsMargins(15, 15, 15, 15)

        self._total_cost_label = self._create_stat_label("总成本", "$0.00")
        self._total_value_label = self._create_stat_label("总市值", "$0.00")
        self._total_pnl_label = self._create_stat_label("总盈亏", "$0.00 (0.00%)")
        self._position_count_label = self._create_stat_label("持仓数量", "0只")

        group_layout.addWidget(self._total_cost_label)
        group_layout.addWidget(self._total_value_label)
        group_layout.addWidget(self._total_pnl_label)
        group_layout.addWidget(self._position_count_label)
        group_layout.addStretch()

        layout.addWidget(group)

    def _create_stat_label(self, title: str, value: str) -> QWidget:
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        widget.setStyleSheet("QFrame { background-color: #f8fafc; border-radius: 8px; padding: 10px; }")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("color: #1f2937; font-size: 18px; font-weight: bold;")
        value_label.setObjectName("value_label")
        layout.addWidget(value_label)

        return widget

    def set_stats(self, stats: Dict[str, Any]):
        total_cost = stats.get('total_cost', 0)
        total_value = stats.get('total_value', 0)
        total_pnl = stats.get('total_pnl', 0)
        pnl_percent = stats.get('pnl_percent', 0)
        position_count = stats.get('position_count', 0)

        self._update_stat_label(self._total_cost_label, "总成本", f"${total_cost:,.2f}")
        self._update_stat_label(self._total_value_label, "总市值", f"${total_value:,.2f}")
        
        pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
        pnl_text = f"${total_pnl:+,.2f} ({pnl_percent:+.2f}%)"
        self._update_stat_label(self._total_pnl_label, "总盈亏", pnl_text, pnl_color)
        
        self._update_stat_label(self._position_count_label, "持仓数量", f"{position_count}只")

    def _update_stat_label(self, widget: QWidget, title: str, value: str, color: str = None):
        for child in widget.findChildren(QLabel):
            if child.objectName() == "value_label":
                child.setText(value)
                if color:
                    child.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
                else:
                    child.setStyleSheet("color: #1f2937; font-size: 18px; font-weight: bold;")


class PnLAnalysisTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from .watchlist import WatchlistManager
        self._watchlist = WatchlistManager()
        self._analyzer = PnLAnalyzer(self._watchlist)
        self._init_ui()
        self._watchlist.add_update_callback(self._refresh_data)
        self._refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self._stats_widget = PortfolioStatsWidget()
        layout.addWidget(self._stats_widget)

        main_splitter = QSplitter(Qt.Horizontal)

        left_splitter = QSplitter(Qt.Vertical)

        self._histogram_widget = PnLHistogramWidget()
        left_splitter.addWidget(self._histogram_widget)

        self._bubble_widget = BubbleChartWidget()
        self._bubble_widget.bubble_clicked.connect(self._on_chart_item_clicked)
        left_splitter.addWidget(self._bubble_widget)

        left_splitter.setSizes([250, 350])

        right_splitter = QSplitter(Qt.Vertical)

        self._waterfall_widget = WaterfallChartWidget()
        self._waterfall_widget.item_clicked.connect(self._on_chart_item_clicked)
        right_splitter.addWidget(self._waterfall_widget)

        self._price_chart_widget = PriceComparisonChartWidget()
        right_splitter.addWidget(self._price_chart_widget)

        right_splitter.setSizes([350, 250])

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([500, 500])

        layout.addWidget(main_splitter, 1)

        self._ranking_table = PnLRankingTable()
        self._ranking_table.item_selected.connect(self._on_table_item_selected)
        layout.addWidget(self._ranking_table)

    def _refresh_data(self):
        pnl_data = self._analyzer.get_position_pnl_data()
        stats = self._analyzer.get_portfolio_stats()
        distribution = self._analyzer.get_pnl_distribution()

        self._stats_widget.set_stats(stats)
        self._histogram_widget.set_data(distribution)
        self._bubble_widget.set_data(pnl_data)
        self._waterfall_widget.set_data(pnl_data)
        self._price_chart_widget.set_data(pnl_data)
        self._ranking_table.set_data(pnl_data)

    def _on_chart_item_clicked(self, symbol: str):
        self._highlight_symbol(symbol)

    def _on_table_item_selected(self, symbol: str):
        self._highlight_symbol(symbol)

    def _highlight_symbol(self, symbol: str):
        self._bubble_widget.set_highlighted_symbol(symbol)
        self._waterfall_widget.set_highlighted_symbol(symbol)
        self._price_chart_widget.set_highlighted_symbol(symbol)
        self._ranking_table.set_selected_symbol(symbol)

    def refresh(self):
        self._refresh_data()
