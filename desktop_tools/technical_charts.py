from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient
from typing import List, Dict, Any, Optional, Tuple
import math


class PriceChartWidget(QWidget):
    COLOR_RED = QColor(239, 68, 68)
    COLOR_GREEN = QColor(34, 197, 94)
    COLOR_BLUE = QColor(59, 130, 246)
    COLOR_ORANGE = QColor(251, 146, 60)
    COLOR_PURPLE = QColor(168, 85, 247)
    COLOR_GRAY = QColor(107, 114, 128)
    COLOR_LIGHT_GRAY = QColor(229, 231, 235)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: Optional[Dict[str, Any]] = None
        self._indicator_type: str = 'price'
        self._title: str = '价格走势'
        self.setMinimumSize(400, 300)
        self.setMinimumHeight(250)

    def set_data(self, data: Dict[str, Any], indicator_type: str = 'price'):
        self._data = data
        self._indicator_type = indicator_type
        self.update()

    def set_title(self, title: str):
        self._title = title
        self.update()

    def clear(self):
        self._data = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        self._draw_background(painter, width, height)
        self._draw_title(painter, width, height)

        if self._data is None:
            self._draw_placeholder(painter, width, height)
            return

        chart_rect = QRectF(60, 30, width - 70, height - 50)

        if self._indicator_type == 'price':
            self._draw_price_chart(painter, chart_rect)
        elif self._indicator_type == 'macd':
            self._draw_macd_chart(painter, chart_rect)
        elif self._indicator_type == 'rsi':
            self._draw_rsi_chart(painter, chart_rect)
        elif self._indicator_type == 'bollinger':
            self._draw_bollinger_chart(painter, chart_rect)
        elif self._indicator_type == 'kdj':
            self._draw_kdj_chart(painter, chart_rect)
        elif self._indicator_type == 'volume':
            self._draw_volume_chart(painter, chart_rect)

    def _draw_background(self, painter: QPainter, width: int, height: int):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(0, 0, width, height)

    def _draw_title(self, painter: QPainter, width: int, height: int):
        painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawText(10, 20, self._title)

    def _draw_placeholder(self, painter: QPainter, width: int, height: int):
        painter.setFont(QFont('Microsoft YaHei', 12))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawText(0, 0, width, height, Qt.AlignCenter, '等待数据加载...')

    def _get_valid_data_range(self, values: List[float]) -> Tuple[float, float]:
        valid_values = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
        if not valid_values:
            return 0, 100
        return min(valid_values), max(valid_values)

    def _draw_grid(self, painter: QPainter, rect: QRectF, y_min: float, y_max: float, levels: int = 5):
        painter.setPen(QPen(self.COLOR_LIGHT_GRAY, 1, Qt.SolidLine))

        for i in range(levels + 1):
            y = rect.top() + rect.height() * i / levels
            painter.drawLine(rect.left(), y, rect.right(), y)

            value = y_max - (y_max - y_min) * i / levels
            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(
                rect.left() - 55, y - 6, 50, 12,
                Qt.AlignRight | Qt.AlignVCenter,
                f'{value:.2f}'
            )

    def _draw_price_chart(self, painter: QPainter, rect: QRectF):
        price_data = self._data.get('price_data', {})
        closes = price_data.get('close', [])
        opens = price_data.get('open', [])
        highs = price_data.get('high', [])
        lows = price_data.get('low', [])
        volumes = price_data.get('volume', [])
        
        ma = self._data.get('ma', {})

        if not closes:
            return

        all_values = closes.copy()
        for period, ma_values in ma.items():
            all_values.extend([v for v in ma_values if v is not None])

        y_min, y_max = self._get_valid_data_range(all_values)
        if y_max == y_min:
            y_max = y_min + 1

        self._draw_grid(painter, rect, y_min, y_max)

        points = len(closes)
        if points < 2:
            return

        x_step = rect.width() / (points - 1) if points > 1 else rect.width()

        for i in range(points):
            x = rect.left() + i * x_step
            
            if opens and highs and lows and closes and i < len(opens) and i < len(highs) and i < len(lows):
                open_val = opens[i]
                high_val = highs[i]
                low_val = lows[i]
                close_val = closes[i]

                if all(v is not None for v in [open_val, high_val, low_val, close_val]):
                    color = self.COLOR_GREEN if close_val >= open_val else self.COLOR_RED
                    
                    high_y = rect.bottom() - (high_val - y_min) / (y_max - y_min) * rect.height()
                    low_y = rect.bottom() - (low_val - y_min) / (y_max - y_min) * rect.height()
                    open_y = rect.bottom() - (open_val - y_min) / (y_max - y_min) * rect.height()
                    close_y = rect.bottom() - (close_val - y_min) / (y_max - y_min) * rect.height()

                    painter.setPen(QPen(color, 1))
                    painter.drawLine(x, high_y, x, low_y)

                    candle_width = max(2, x_step * 0.6)
                    painter.setBrush(QBrush(color))
                    painter.setPen(Qt.NoPen)
                    
                    top_y = min(open_y, close_y)
                    bottom_y = max(open_y, close_y)
                    candle_height = max(1, bottom_y - top_y)
                    
                    painter.drawRect(
                        x - candle_width / 2,
                        top_y,
                        candle_width,
                        candle_height
                    )

        ma_colors = {
            5: self.COLOR_BLUE,
            20: self.COLOR_GREEN,
            50: self.COLOR_ORANGE,
            200: self.COLOR_PURPLE
        }

        for period, ma_values in ma.items():
            if not ma_values:
                continue
            
            color = ma_colors.get(period, self.COLOR_GRAY)
            painter.setPen(QPen(color, 2))

            first_valid = None
            for i in range(len(ma_values)):
                if ma_values[i] is not None and not math.isnan(ma_values[i]):
                    if first_valid is None:
                        first_valid = i
                    else:
                        x1 = rect.left() + first_valid * x_step
                        y1 = rect.bottom() - (ma_values[first_valid] - y_min) / (y_max - y_min) * rect.height()
                        x2 = rect.left() + i * x_step
                        y2 = rect.bottom() - (ma_values[i] - y_min) / (y_max - y_min) * rect.height()
                        
                        painter.drawLine(x1, y1, x2, y2)
                        first_valid = i

        legend_y = 5
        painter.setFont(QFont('Microsoft YaHei', 8))
        for period, color in ma_colors.items():
            if period in ma and ma[period]:
                painter.setPen(QPen(color, 1))
                painter.setBrush(QBrush(color))
                painter.drawRect(rect.left() + legend_y, 5, 20, 3)
                painter.setPen(QPen(self.COLOR_GRAY, 1))
                painter.drawText(rect.left() + legend_y + 25, 15, f'MA{period}')
                legend_y += 60

    def _draw_macd_chart(self, painter: QPainter, rect: QRectF):
        macd = self._data.get('macd', {})
        macd_line = macd.get('macd_line', [])
        signal_line = macd.get('signal_line', [])
        histogram = macd.get('histogram', [])

        if not macd_line:
            return

        all_values = []
        all_values.extend([v for v in macd_line if v is not None])
        all_values.extend([v for v in signal_line if v is not None])
        all_values.extend([v for v in histogram if v is not None])

        y_min, y_max = self._get_valid_data_range(all_values)
        y_max = max(y_max, abs(y_min))
        y_min = -y_max
        if y_max == 0:
            y_max = 1
            y_min = -1

        self._draw_grid(painter, rect, y_min, y_max)

        zero_y = rect.bottom() - (0 - y_min) / (y_max - y_min) * rect.height()
        painter.setPen(QPen(self.COLOR_GRAY, 1, Qt.DashLine))
        painter.drawLine(rect.left(), zero_y, rect.right(), zero_y)

        points = len(macd_line)
        if points < 2:
            return

        x_step = rect.width() / (points - 1) if points > 1 else rect.width()

        for i in range(len(histogram)):
            if histogram[i] is None or math.isnan(histogram[i]):
                continue

            x = rect.left() + i * x_step
            value = histogram[i]
            
            color = self.COLOR_GREEN if value >= 0 else self.COLOR_RED
            
            bar_y = rect.bottom() - (value - y_min) / (y_max - y_min) * rect.height()
            bar_height = abs(bar_y - zero_y)
            bar_width = max(2, x_step * 0.6)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            
            if value >= 0:
                painter.drawRect(
                    x - bar_width / 2,
                    bar_y,
                    bar_width,
                    bar_height
                )
            else:
                painter.drawRect(
                    x - bar_width / 2,
                    zero_y,
                    bar_width,
                    bar_height
                )

        for line_data, color, label in [
            (macd_line, self.COLOR_BLUE, 'MACD'),
            (signal_line, self.COLOR_ORANGE, 'Signal')
        ]:
            if not line_data:
                continue
            
            painter.setPen(QPen(color, 2))

            first_valid = None
            for i in range(len(line_data)):
                if line_data[i] is not None and not math.isnan(line_data[i]):
                    if first_valid is None:
                        first_valid = i
                    else:
                        x1 = rect.left() + first_valid * x_step
                        y1 = rect.bottom() - (line_data[first_valid] - y_min) / (y_max - y_min) * rect.height()
                        x2 = rect.left() + i * x_step
                        y2 = rect.bottom() - (line_data[i] - y_min) / (y_max - y_min) * rect.height()
                        
                        painter.drawLine(x1, y1, x2, y2)
                        first_valid = i

        painter.setFont(QFont('Microsoft YaHei', 8))
        painter.setPen(QPen(self.COLOR_BLUE, 1))
        painter.setBrush(QBrush(self.COLOR_BLUE))
        painter.drawRect(rect.left(), 5, 20, 3)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(rect.left() + 25, 15, 'MACD')

        painter.setPen(QPen(self.COLOR_ORANGE, 1))
        painter.setBrush(QBrush(self.COLOR_ORANGE))
        painter.drawRect(rect.left() + 70, 5, 20, 3)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(rect.left() + 95, 15, 'Signal')

        painter.setBrush(QBrush(self.COLOR_GREEN))
        painter.drawRect(rect.left() + 140, 5, 20, 3)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(rect.left() + 165, 15, 'Histogram')

    def _draw_rsi_chart(self, painter: QPainter, rect: QRectF):
        rsi = self._data.get('rsi', [])

        if not rsi:
            return

        y_min, y_max = 0, 100
        self._draw_grid(painter, rect, y_min, y_max)

        overbought_y = rect.bottom() - (70 - y_min) / (y_max - y_min) * rect.height()
        oversold_y = rect.bottom() - (30 - y_min) / (y_max - y_min) * rect.height()
        middle_y = rect.bottom() - (50 - y_min) / (y_max - y_min) * rect.height()

        painter.setPen(QPen(self.COLOR_RED, 1, Qt.DashLine))
        painter.drawLine(rect.left(), overbought_y, rect.right(), overbought_y)
        
        painter.setPen(QPen(self.COLOR_GREEN, 1, Qt.DashLine))
        painter.drawLine(rect.left(), oversold_y, rect.right(), oversold_y)
        
        painter.setPen(QPen(self.COLOR_GRAY, 1, Qt.DashLine))
        painter.drawLine(rect.left(), middle_y, rect.right(), middle_y)

        points = len(rsi)
        if points < 2:
            return

        x_step = rect.width() / (points - 1) if points > 1 else rect.width()

        painter.setPen(QPen(self.COLOR_PURPLE, 2))

        first_valid = None
        for i in range(len(rsi)):
            if rsi[i] is not None and not math.isnan(rsi[i]):
                if first_valid is None:
                    first_valid = i
                else:
                    x1 = rect.left() + first_valid * x_step
                    y1 = rect.bottom() - (rsi[first_valid] - y_min) / (y_max - y_min) * rect.height()
                    x2 = rect.left() + i * x_step
                    y2 = rect.bottom() - (rsi[i] - y_min) / (y_max - y_min) * rect.height()
                    
                    painter.drawLine(x1, y1, x2, y2)
                    first_valid = i

        painter.setFont(QFont('Microsoft YaHei', 8))
        painter.setPen(QPen(self.COLOR_RED, 1))
        painter.drawText(rect.left(), int(overbought_y) - 5, '超买 70')
        
        painter.setPen(QPen(self.COLOR_GREEN, 1))
        painter.drawText(rect.left(), int(oversold_y) + 12, '超卖 30')

    def _draw_bollinger_chart(self, painter: QPainter, rect: QRectF):
        price_data = self._data.get('price_data', {})
        closes = price_data.get('close', [])
        bollinger = self._data.get('bollinger', {})
        
        upper_band = bollinger.get('upper_band', [])
        middle_band = bollinger.get('middle_band', [])
        lower_band = bollinger.get('lower_band', [])

        if not closes:
            return

        all_values = closes.copy()
        all_values.extend([v for v in upper_band if v is not None])
        all_values.extend([v for v in middle_band if v is not None])
        all_values.extend([v for v in lower_band if v is not None])

        y_min, y_max = self._get_valid_data_range(all_values)
        if y_max == y_min:
            y_max = y_min + 1

        self._draw_grid(painter, rect, y_min, y_max)

        points = len(closes)
        if points < 2:
            return

        x_step = rect.width() / (points - 1) if points > 1 else rect.width()

        painter.setPen(QPen(self.COLOR_GRAY, 1, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(200, 220, 255, 50)))

        fill_points = []
        for i in range(len(upper_band)):
            if upper_band[i] is not None and not math.isnan(upper_band[i]):
                x = rect.left() + i * x_step
                y = rect.bottom() - (upper_band[i] - y_min) / (y_max - y_min) * rect.height()
                fill_points.append(QPointF(x, y))
        
        for i in range(len(lower_band) - 1, -1, -1):
            if lower_band[i] is not None and not math.isnan(lower_band[i]):
                x = rect.left() + i * x_step
                y = rect.bottom() - (lower_band[i] - y_min) / (y_max - y_min) * rect.height()
                fill_points.append(QPointF(x, y))

        if len(fill_points) >= 3:
            from PyQt5.QtGui import QPolygonF
            painter.drawPolygon(QPolygonF(fill_points))

        for line_data, color, label in [
            (upper_band, self.COLOR_RED, '上轨'),
            (middle_band, self.COLOR_BLUE, '中轨'),
            (lower_band, self.COLOR_GREEN, '下轨')
        ]:
            if not line_data:
                continue
            
            painter.setPen(QPen(color, 2))

            first_valid = None
            for i in range(len(line_data)):
                if line_data[i] is not None and not math.isnan(line_data[i]):
                    if first_valid is None:
                        first_valid = i
                    else:
                        x1 = rect.left() + first_valid * x_step
                        y1 = rect.bottom() - (line_data[first_valid] - y_min) / (y_max - y_min) * rect.height()
                        x2 = rect.left() + i * x_step
                        y2 = rect.bottom() - (line_data[i] - y_min) / (y_max - y_min) * rect.height()
                        
                        painter.drawLine(x1, y1, x2, y2)
                        first_valid = i

        painter.setPen(QPen(self.COLOR_ORANGE, 1))
        for i in range(len(closes)):
            if closes[i] is not None:
                x = rect.left() + i * x_step
                y = rect.bottom() - (closes[i] - y_min) / (y_max - y_min) * rect.height()
                painter.drawEllipse(x - 2, y - 2, 4, 4)

        painter.setFont(QFont('Microsoft YaHei', 8))
        legend_x = rect.left()
        for color, label in [
            (self.COLOR_RED, '上轨'),
            (self.COLOR_BLUE, '中轨'),
            (self.COLOR_GREEN, '下轨')
        ]:
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            painter.drawRect(legend_x, 5, 20, 3)
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(legend_x + 25, 15, label)
            legend_x += 60

    def _draw_kdj_chart(self, painter: QPainter, rect: QRectF):
        kdj = self._data.get('kdj', {})
        k = kdj.get('k', [])
        d = kdj.get('d', [])
        j = kdj.get('j', [])

        if not k or not d:
            return

        all_values = []
        all_values.extend([v for v in k if v is not None])
        all_values.extend([v for v in d if v is not None])
        all_values.extend([v for v in j if v is not None])

        y_min, y_max = self._get_valid_data_range(all_values)
        y_min = min(y_min, 0)
        y_max = max(y_max, 100)
        if y_max == y_min:
            y_max = 100
            y_min = 0

        self._draw_grid(painter, rect, y_min, y_max)

        overbought_y = rect.bottom() - (80 - y_min) / (y_max - y_min) * rect.height()
        oversold_y = rect.bottom() - (20 - y_min) / (y_max - y_min) * rect.height()

        painter.setPen(QPen(self.COLOR_RED, 1, Qt.DashLine))
        painter.drawLine(rect.left(), overbought_y, rect.right(), overbought_y)
        
        painter.setPen(QPen(self.COLOR_GREEN, 1, Qt.DashLine))
        painter.drawLine(rect.left(), oversold_y, rect.right(), oversold_y)

        points = len(k)
        if points < 2:
            return

        x_step = rect.width() / (points - 1) if points > 1 else rect.width()

        for line_data, color, label in [
            (k, self.COLOR_BLUE, 'K'),
            (d, self.COLOR_ORANGE, 'D'),
            (j, self.COLOR_PURPLE, 'J')
        ]:
            if not line_data:
                continue
            
            painter.setPen(QPen(color, 2))

            first_valid = None
            for i in range(len(line_data)):
                if line_data[i] is not None and not math.isnan(line_data[i]):
                    if first_valid is None:
                        first_valid = i
                    else:
                        x1 = rect.left() + first_valid * x_step
                        y1 = rect.bottom() - (line_data[first_valid] - y_min) / (y_max - y_min) * rect.height()
                        x2 = rect.left() + i * x_step
                        y2 = rect.bottom() - (line_data[i] - y_min) / (y_max - y_min) * rect.height()
                        
                        painter.drawLine(x1, y1, x2, y2)
                        first_valid = i

        painter.setFont(QFont('Microsoft YaHei', 8))
        legend_x = rect.left()
        for color, label in [
            (self.COLOR_BLUE, 'K'),
            (self.COLOR_ORANGE, 'D'),
            (self.COLOR_PURPLE, 'J')
        ]:
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            painter.drawRect(legend_x, 5, 20, 3)
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(legend_x + 25, 15, label)
            legend_x += 40

        painter.setPen(QPen(self.COLOR_RED, 1))
        painter.drawText(rect.left(), int(overbought_y) - 5, '超买 80')
        
        painter.setPen(QPen(self.COLOR_GREEN, 1))
        painter.drawText(rect.left(), int(oversold_y) + 12, '超卖 20')

    def _draw_volume_chart(self, painter: QPainter, rect: QRectF):
        price_data = self._data.get('price_data', {})
        volumes = price_data.get('volume', [])
        closes = price_data.get('close', [])
        opens = price_data.get('open', [])
        volume_data = self._data.get('volume', {})
        
        volume_ma_5 = volume_data.get('volume_ma_5', [])
        volume_ma_20 = volume_data.get('volume_ma_20', [])

        if not volumes:
            return

        all_values = volumes.copy()
        all_values.extend([v for v in volume_ma_5 if v is not None])
        all_values.extend([v for v in volume_ma_20 if v is not None])

        y_min, y_max = self._get_valid_data_range(all_values)
        y_min = 0
        if y_max == y_min:
            y_max = 1

        self._draw_grid(painter, rect, y_min, y_max)

        points = len(volumes)
        if points < 1:
            return

        x_step = rect.width() / points if points > 0 else rect.width()

        for i in range(len(volumes)):
            if volumes[i] is None:
                continue

            x = rect.left() + i * x_step + x_step * 0.1
            value = volumes[i]
            
            if closes and opens and i < len(closes) and i < len(opens):
                color = self.COLOR_GREEN if closes[i] >= opens[i] else self.COLOR_RED
            else:
                color = self.COLOR_GRAY
            
            bar_height = (value - y_min) / (y_max - y_min) * rect.height()
            bar_width = x_step * 0.8

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(
                x,
                rect.bottom() - bar_height,
                bar_width,
                bar_height
            )

        for line_data, color, label in [
            (volume_ma_5, self.COLOR_BLUE, 'MA5'),
            (volume_ma_20, self.COLOR_ORANGE, 'MA20')
        ]:
            if not line_data:
                continue
            
            painter.setPen(QPen(color, 2))

            first_valid = None
            for i in range(len(line_data)):
                if line_data[i] is not None and not math.isnan(line_data[i]):
                    if first_valid is None:
                        first_valid = i
                    else:
                        x1 = rect.left() + first_valid * x_step + x_step / 2
                        y1 = rect.bottom() - (line_data[first_valid] - y_min) / (y_max - y_min) * rect.height()
                        x2 = rect.left() + i * x_step + x_step / 2
                        y2 = rect.bottom() - (line_data[i] - y_min) / (y_max - y_min) * rect.height()
                        
                        painter.drawLine(x1, y1, x2, y2)
                        first_valid = i

        painter.setFont(QFont('Microsoft YaHei', 8))
        legend_x = rect.left()
        for color, label in [
            (self.COLOR_BLUE, 'MA5'),
            (self.COLOR_ORANGE, 'MA20')
        ]:
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            painter.drawRect(legend_x, 5, 20, 3)
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(legend_x + 25, 15, label)
            legend_x += 60

        painter.setPen(QPen(self.COLOR_GREEN, 1))
        painter.setBrush(QBrush(self.COLOR_GREEN))
        painter.drawRect(legend_x, 5, 15, 10)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(legend_x + 20, 15, '涨')
        legend_x += 45

        painter.setPen(QPen(self.COLOR_RED, 1))
        painter.setBrush(QBrush(self.COLOR_RED))
        painter.drawRect(legend_x, 5, 15, 10)
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        painter.drawText(legend_x + 20, 15, '跌')


class SignalDisplayWidget(QWidget):
    COLOR_GREEN = QColor(34, 197, 94)
    COLOR_RED = QColor(239, 68, 68)
    COLOR_YELLOW = QColor(251, 191, 36)
    COLOR_GRAY = QColor(107, 114, 128)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._signals: Optional[Dict[str, Any]] = None
        self.setMinimumHeight(150)

    def set_signals(self, signals: Dict[str, Any]):
        self._signals = signals
        self.update()

    def clear(self):
        self._signals = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(0, 0, width, height)

        if self._signals is None:
            painter.setFont(QFont('Microsoft YaHei', 12))
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(0, 0, width, height, Qt.AlignCenter, '等待分析...')
            return

        overall_signal = self._signals.get('overall_signal', '观望')
        signal_color = self._signals.get('signal_color', 'yellow')
        buy_score = self._signals.get('buy_score', 0)
        sell_score = self._signals.get('sell_score', 0)
        total_score = self._signals.get('total_score', 0)

        color_map = {
            'green': self.COLOR_GREEN,
            'red': self.COLOR_RED,
            'yellow': self.COLOR_YELLOW
        }
        display_color = color_map.get(signal_color, self.COLOR_GRAY)

        painter.setFont(QFont('Microsoft YaHei', 24, QFont.Bold))
        painter.setPen(QPen(display_color, 1))
        painter.drawText(0, 10, width, 50, Qt.AlignCenter, f'综合信号: {overall_signal}')

        painter.setFont(QFont('Microsoft YaHei', 12))
        painter.setPen(QPen(self.COLOR_GRAY, 1))
        score_text = f'买入: {buy_score}  |  卖出: {sell_score}  |  总分: {total_score}'
        painter.drawText(0, 55, width, 30, Qt.AlignCenter, score_text)

        buy_signals = self._signals.get('buy_signals', [])
        sell_signals = self._signals.get('sell_signals', [])
        neutral_signals = self._signals.get('neutral_signals', [])

        y_start = 90
        line_height = 20

        painter.setFont(QFont('Microsoft YaHei', 10))

        if buy_signals:
            painter.setPen(QPen(self.COLOR_GREEN, 1))
            painter.drawText(10, y_start, width - 20, line_height, Qt.AlignLeft, f'买入信号 ({len(buy_signals)}):')
            y_start += line_height
            
            for signal in buy_signals[:3]:
                painter.setPen(QPen(self.COLOR_GREEN, 1))
                painter.drawText(30, y_start, width - 40, line_height, Qt.AlignLeft, f'• {signal}')
                y_start += line_height

        if sell_signals:
            painter.setPen(QPen(self.COLOR_RED, 1))
            painter.drawText(10, y_start, width - 20, line_height, Qt.AlignLeft, f'卖出信号 ({len(sell_signals)}):')
            y_start += line_height
            
            for signal in sell_signals[:3]:
                painter.setPen(QPen(self.COLOR_RED, 1))
                painter.drawText(30, y_start, width - 40, line_height, Qt.AlignLeft, f'• {signal}')
                y_start += line_height

        if neutral_signals and y_start + line_height < height:
            painter.setPen(QPen(self.COLOR_GRAY, 1))
            painter.drawText(10, y_start, width - 20, line_height, Qt.AlignLeft, f'其他信号 ({len(neutral_signals)}):')
            y_start += line_height
            
            for signal in neutral_signals[:2]:
                if y_start + line_height < height:
                    painter.setPen(QPen(self.COLOR_GRAY, 1))
                    painter.drawText(30, y_start, width - 40, line_height, Qt.AlignLeft, f'• {signal}')
                    y_start += line_height
