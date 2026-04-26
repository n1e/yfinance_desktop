from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPolygonF, QPainterPath
from typing import List, Optional, Dict, Any
import math


class RadarChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: List[str] = []
        self._values: List[float] = []
        self._dimension_scores: Dict[str, float] = {}
        self._title: str = "估值雷达图"
        self._min_value: float = 0
        self._max_value: float = 100
        self._levels: int = 5
        
        self._bg_color = QColor(255, 255, 255)
        self._grid_color = QColor(200, 200, 200)
        self._line_color = QColor(30, 144, 255)
        self._fill_color = QColor(30, 144, 255, 100)
        self._text_color = QColor(50, 50, 50)
        
        self.setMinimumSize(400, 400)
        
    def set_data(self, labels: List[str], values: List[float], 
                  dimension_scores: Optional[Dict[str, float]] = None):
        self._labels = labels
        self._values = values
        if dimension_scores:
            self._dimension_scores = dimension_scores
        self.update()
        
    def set_title(self, title: str):
        self._title = title
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        painter.fillRect(self.rect(), self._bg_color)
        
        center_x = width // 2
        center_y = height // 2
        
        title_font = QFont("Microsoft YaHei", 12, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(self._text_color)
        title_rect = painter.boundingRect(0, 0, width, 40, Qt.AlignCenter, self._title)
        painter.drawText(0, 10, width, 40, Qt.AlignCenter, self._title)
        
        chart_top = title_rect.bottom() + 20
        chart_height = height - chart_top - 60
        chart_width = width - 100
        
        radius = min(chart_width, chart_height) // 2 - 20
        
        center_x = width // 2
        center_y = chart_top + chart_height // 2
        
        self._draw_grid(painter, center_x, center_y, radius)
        self._draw_data(painter, center_x, center_y, radius)
        self._draw_legend(painter, center_x, height - 50)
        
    def _draw_grid(self, painter: QPainter, center_x: int, center_y: int, radius: int):
        num_vars = len(self._labels) if self._labels else 10
        
        painter.setPen(QPen(self._grid_color, 1, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        
        for level in range(1, self._levels + 1):
            r = radius * level / self._levels
            points = []
            for i in range(num_vars):
                angle = 2 * math.pi * i / num_vars - math.pi / 2
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                points.append(QPointF(x, y))
            
            if len(points) >= 3:
                polygon = QPolygonF(points)
                painter.drawPolygon(polygon)
        
        painter.setPen(QPen(self._grid_color, 1, Qt.SolidLine))
        for i in range(num_vars):
            angle = 2 * math.pi * i / num_vars - math.pi / 2
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            painter.drawLine(QPointF(center_x, center_y), QPointF(x, y))
            
            if self._labels and i < len(self._labels):
                label = self._labels[i]
                label_radius = radius + 30
                label_x = center_x + label_radius * math.cos(angle)
                label_y = center_y + label_radius * math.sin(angle)
                
                font = QFont("Microsoft YaHei", 9)
                painter.setFont(font)
                painter.setPen(self._text_color)
                
                text_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignCenter, label)
                
                align_flag = Qt.AlignCenter
                if abs(math.cos(angle)) < 0.1:
                    if math.sin(angle) > 0:
                        align_flag = Qt.AlignHCenter | Qt.AlignTop
                    else:
                        align_flag = Qt.AlignHCenter | Qt.AlignBottom
                elif math.cos(angle) > 0:
                    align_flag = Qt.AlignLeft | Qt.AlignVCenter
                else:
                    align_flag = Qt.AlignRight | Qt.AlignVCenter
                
                label_x -= text_rect.width() // 2
                label_y -= text_rect.height() // 2
                
                painter.drawText(int(label_x), int(label_y), 
                               text_rect.width(), text_rect.height(), 
                               align_flag, label)
                
                if self._values and i < len(self._values):
                    value = self._values[i]
                    value_text = f"{value:.0f}"
                    
                    value_radius = radius + 15
                    value_x = center_x + value_radius * math.cos(angle)
                    value_y = center_y + value_radius * math.sin(angle)
                    
                    value_font = QFont("Microsoft YaHei", 8, QFont.Bold)
                    painter.setFont(value_font)
                    
                    if value >= 60:
                        painter.setPen(QColor(0, 150, 0))
                    elif value >= 40:
                        painter.setPen(QColor(200, 150, 0))
                    else:
                        painter.setPen(QColor(200, 0, 0))
                    
                    value_rect = painter.boundingRect(0, 0, 30, 15, Qt.AlignCenter, value_text)
                    painter.drawText(int(value_x - value_rect.width() // 2), 
                                   int(value_y - value_rect.height() // 2),
                                   value_rect.width(), value_rect.height(),
                                   Qt.AlignCenter, value_text)

    def _draw_data(self, painter: QPainter, center_x: int, center_y: int, radius: int):
        if not self._values or len(self._values) == 0:
            return
        
        num_vars = len(self._values)
        
        points = []
        for i in range(num_vars):
            angle = 2 * math.pi * i / num_vars - math.pi / 2
            value = self._values[i]
            r = radius * (value - self._min_value) / (self._max_value - self._min_value)
            r = max(0, min(r, radius))
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            points.append(QPointF(x, y))
        
        if len(points) >= 3:
            polygon = QPolygonF(points)
            
            painter.setBrush(self._fill_color)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(polygon)
            
            painter.setPen(QPen(self._line_color, 2, Qt.SolidLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(polygon)
            
            point_color = QColor(30, 144, 255)
            point_brush = QBrush(point_color)
            painter.setBrush(point_brush)
            painter.setPen(QPen(point_color, 1))
            
            for point in points:
                painter.drawEllipse(point, 4, 4)

    def _draw_legend(self, painter: QPainter, center_x: int, y: int):
        if not self._dimension_scores:
            return
        
        legend_font = QFont("Microsoft YaHei", 10)
        painter.setFont(legend_font)
        
        labels = ['价格合理性', '成长性', '安全性']
        colors = [QColor(30, 144, 255), QColor(34, 139, 34), QColor(255, 140, 0)]
        
        total_width = 0
        spacing = 40
        
        for i, label in enumerate(labels):
            if i == 0 and 'price_reasonableness' in self._dimension_scores:
                score = self._dimension_scores['price_reasonableness']
                text = f"{label}: {score:.1f}"
            elif i == 1 and 'growth' in self._dimension_scores:
                score = self._dimension_scores['growth']
                text = f"{label}: {score:.1f}"
            elif i == 2 and 'safety' in self._dimension_scores:
                score = self._dimension_scores['safety']
                text = f"{label}: {score:.1f}"
            else:
                continue
                
            rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignLeft, text)
            total_width += rect.width() + 20 + spacing
        
        start_x = center_x - total_width // 2
        
        for i, label in enumerate(labels):
            if i == 0 and 'price_reasonableness' in self._dimension_scores:
                score = self._dimension_scores['price_reasonableness']
                text = f"{label}: {score:.1f}"
            elif i == 1 and 'growth' in self._dimension_scores:
                score = self._dimension_scores['growth']
                text = f"{label}: {score:.1f}"
            elif i == 2 and 'safety' in self._dimension_scores:
                score = self._dimension_scores['safety']
                text = f"{label}: {score:.1f}"
            else:
                continue
                
            color = colors[i]
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 1))
            painter.drawRect(start_x, y, 15, 15)
            
            painter.setPen(self._text_color)
            painter.drawText(start_x + 20, y, 100, 15, Qt.AlignLeft | Qt.AlignVCenter, text)
            
            rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignLeft, text)
            start_x += rect.width() + 20 + spacing


class DimensionScoreBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._score: float = 0
        self._label: str = ""
        self._max_score: float = 100
        
        self.setMinimumHeight(50)
        self.setMaximumHeight(60)
        
    def set_score(self, score: float, label: str = ""):
        self._score = max(0, min(score, self._max_score))
        self._label = label
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        label_font = QFont("Microsoft YaHei", 10, QFont.Bold)
        painter.setFont(label_font)
        painter.setPen(QColor(50, 50, 50))
        
        label_text = self._label if self._label else "评分"
        painter.drawText(10, 0, 100, height, Qt.AlignLeft | Qt.AlignVCenter, label_text)
        
        bar_start_x = 110
        bar_width = width - bar_start_x - 100
        bar_height = 20
        bar_y = (height - bar_height) // 2
        
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRoundedRect(bar_start_x, bar_y, bar_width, bar_height, 5, 5)
        
        score_ratio = self._score / self._max_score
        fill_width = bar_width * score_ratio
        
        if self._score >= 70:
            fill_color = QColor(34, 139, 34)
        elif self._score >= 50:
            fill_color = QColor(255, 165, 0)
        else:
            fill_color = QColor(220, 20, 60)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(fill_color))
        if fill_width > 0:
            painter.drawRoundedRect(bar_start_x, bar_y, fill_width, bar_height, 5, 5)
        
        score_font = QFont("Microsoft YaHei", 11, QFont.Bold)
        painter.setFont(score_font)
        painter.setPen(fill_color)
        
        score_text = f"{self._score:.1f}/{self._max_score}"
        score_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignLeft, score_text)
        painter.drawText(bar_start_x + bar_width + 10, 0, 100, height, 
                        Qt.AlignLeft | Qt.AlignVCenter, score_text)


class TotalScoreDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._score: float = 0
        self._status: str = ""
        
        self.setMinimumSize(150, 150)
        self.setMaximumSize(200, 200)
        
    def set_score(self, score: float, status: str = ""):
        self._score = max(0, min(score, 100))
        self._status = status
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        center_x = width // 2
        center_y = height // 2
        
        radius = min(width, height) // 2 - 10
        
        if self._score >= 70:
            color = QColor(34, 139, 34)
        elif self._score >= 50:
            color = QColor(255, 165, 0)
        else:
            color = QColor(220, 20, 60)
        
        painter.setPen(QPen(QColor(230, 230, 230), 12))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center_x - radius + 6, center_y - radius + 6, 
                          radius * 2 - 12, radius * 2 - 12)
        
        painter.setPen(QPen(color, 12))
        start_angle = 90 * 16
        span_angle = int(-self._score / 100 * 360 * 16)
        painter.drawArc(center_x - radius + 6, center_y - radius + 6,
                       radius * 2 - 12, radius * 2 - 12,
                       start_angle, span_angle)
        
        score_font = QFont("Microsoft YaHei", 24, QFont.Bold)
        painter.setFont(score_font)
        painter.setPen(color)
        
        score_text = f"{self._score:.0f}"
        score_rect = painter.boundingRect(0, 0, 100, 40, Qt.AlignCenter, score_text)
        painter.drawText(center_x - score_rect.width() // 2, 
                        center_y - score_rect.height() // 2 - 10,
                        score_rect.width(), score_rect.height(),
                        Qt.AlignCenter, score_text)
        
        label_font = QFont("Microsoft YaHei", 10)
        painter.setFont(label_font)
        painter.setPen(QColor(100, 100, 100))
        
        label_text = "综合评分"
        label_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignCenter, label_text)
        painter.drawText(center_x - label_rect.width() // 2,
                        center_y + score_rect.height() // 2,
                        label_rect.width(), label_rect.height(),
                        Qt.AlignCenter, label_text)
        
        if self._status:
            status_font = QFont("Microsoft YaHei", 11, QFont.Bold)
            painter.setFont(status_font)
            painter.setPen(color)
            
            status_rect = painter.boundingRect(0, 0, 150, 25, Qt.AlignCenter, self._status)
            painter.drawText(center_x - status_rect.width() // 2,
                            center_y + score_rect.height() // 2 + label_rect.height() + 5,
                            status_rect.width(), status_rect.height(),
                            Qt.AlignCenter, self._status)
