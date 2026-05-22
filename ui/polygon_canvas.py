from math import cos, sin, pi, sqrt
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient
from PyQt6.QtWidgets import QWidget, QSizePolicy


class PolygonCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.values: List[int] = []
        self.ops: List[str] = []
        self.edge_ids: List[int] = []
        self.is_chain = False
        self.deleted_edge: Optional[int] = None

        self.edge_segments: List[Tuple[int, QPointF, QPointF]] = []
        self.hover_edge: Optional[int] = None
        self.on_edge_clicked = None

        self.setMinimumSize(650, 520)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_state(
        self,
        values: List[int],
        ops: List[str],
        edge_ids: List[int],
        is_chain: bool,
        deleted_edge: Optional[int],
    ) -> None:
        self.values = values[:]
        self.ops = ops[:]
        self.edge_ids = edge_ids[:]
        self.is_chain = is_chain
        self.deleted_edge = deleted_edge
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#f8fafc"))
        gradient.setColorAt(1, QColor("#eef2ff"))
        painter.fillRect(self.rect(), gradient)

        if not self.values:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "等待房主开始游戏")
            return

        points = self._layout_points()
        self.edge_segments = []

        for i in range(len(self.ops)):
            p1 = points[i]
            p2 = points[i + 1] if self.is_chain else points[(i + 1) % len(points)]
            self.edge_segments.append((i, p1, p2))
            self._draw_edge(painter, i, p1, p2)

        if self.is_chain and self.deleted_edge is not None:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(18, 30, f"已删除原边：{self.deleted_edge + 1}")

        for i, point in enumerate(points):
            self._draw_vertex(painter, i, point)

    def _layout_points(self) -> List[QPointF]:
        n = len(self.values)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        if n == 1:
            return [QPointF(cx, cy)]

        radius = min(w, h) * 0.34

        if self.is_chain:
            if n == 2:
                return [QPointF(w * 0.35, cy), QPointF(w * 0.65, cy)]

            start_angle = pi * 0.78
            end_angle = pi * 2.22
            return [
                QPointF(
                    cx + radius * cos(start_angle + (end_angle - start_angle) * i / (n - 1)),
                    cy + radius * sin(start_angle + (end_angle - start_angle) * i / (n - 1)),
                )
                for i in range(n)
            ]

        return [
            QPointF(
                cx + radius * cos(-pi / 2 + 2 * pi * i / n),
                cy + radius * sin(-pi / 2 + 2 * pi * i / n),
            )
            for i in range(n)
        ]

    def _draw_edge(self, painter: QPainter, edge_index: int, p1: QPointF, p2: QPointF) -> None:
        is_hover = edge_index == self.hover_edge
        color = QColor("#2563eb") if is_hover else QColor("#475569")
        width = 5 if is_hover else 3

        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p1, p2)

        mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        edge_no = self.edge_ids[edge_index] + 1 if edge_index < len(self.edge_ids) else edge_index + 1
        label = f"{edge_no}:{self.ops[edge_index]}"

        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        fm = painter.fontMetrics()
        rect = QRectF(
            mid.x() - fm.horizontalAdvance(label) / 2 - 8,
            mid.y() - 16,
            fm.horizontalAdvance(label) + 16,
            32,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(rect, 9, 9)

        painter.setPen(QColor("#0f172a"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_vertex(self, painter: QPainter, vertex_index: int, point: QPointF) -> None:
        radius = 30

        painter.setPen(QPen(QColor("#1d4ed8"), 3))
        painter.setBrush(QBrush(QColor("#dbeafe")))
        painter.drawEllipse(point, radius, radius)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        painter.drawText(
            QRectF(point.x() - radius, point.y() - radius, radius * 2, radius * 2),
            Qt.AlignmentFlag.AlignCenter,
            str(self.values[vertex_index]),
        )

    @staticmethod
    def _distance_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
        px, py = p.x(), p.y()
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()

        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return sqrt((px - ax) ** 2 + (py - ay) ** 2)

        t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))

        qx = ax + t * dx
        qy = ay + t * dy
        return sqrt((px - qx) ** 2 + (py - qy) ** 2)

    def _hit_edge(self, pos: QPointF) -> Optional[int]:
        best_edge = None
        best_dist = 999999.0

        for edge_index, p1, p2 in self.edge_segments:
            distance = self._distance_to_segment(pos, p1, p2)
            if distance < best_dist:
                best_edge = edge_index
                best_dist = distance

        return best_edge if best_dist <= 16 else None

    def mouseMoveEvent(self, event) -> None:
        edge = self._hit_edge(event.position())

        if edge != self.hover_edge:
            self.hover_edge = edge
            self.update()

        if edge is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._hit_edge(event.position())
            if edge is not None and self.on_edge_clicked:
                self.on_edge_clicked(edge)
