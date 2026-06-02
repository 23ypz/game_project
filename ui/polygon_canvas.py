from math import cos, sin, pi, sqrt
from typing import List, Optional, Tuple, Callable

from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
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

        # Flash phase (no movement)
        self.flash_active: bool = False
        self.flash_indices: Optional[Tuple[int, int]] = None
        self.flash_on: bool = False
        self.flash_ticks_left: int = 0
        self.flash_timer: Optional[QTimer] = None
        self.flash_callback: Optional[Callable[[], None]] = None

        # Transition phase (move all vertices from old layout to new layout)
        self.trans_active: bool = False
        self.trans_from: List[QPointF] = []
        self.trans_to: List[QPointF] = []
        self.trans_progress: float = 0.0
        self.trans_timer: Optional[QTimer] = None
        self.trans_callback: Optional[Callable[[], None]] = None
        self.trans_ease: str = "linear"  # 'linear' | 'inout' | 'outback'
        self._last_collapse_to: List[QPointF] = []

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

        base_points = self._layout_points()

        # If transition animation is active, interpolate points
        if self.trans_active and self.trans_from and self.trans_to:
            m = min(len(self.trans_from), len(self.trans_to))
            t = self._ease(self.trans_progress)
            interp = [QPointF(
                self.trans_from[idx].x() * (1 - t) + self.trans_to[idx].x() * t,
                self.trans_from[idx].y() * (1 - t) + self.trans_to[idx].y() * t,
            ) for idx in range(m)]
            # If base layout has more points (e.g., during delete where counts equal, or other edge cases), append remaining base points
            if len(base_points) > m:
                interp.extend(base_points[m:])
            points = interp
        else:
            points = base_points
        self.edge_segments = []

        n_points = len(points)
        if self.is_chain:
            edge_count = min(len(self.ops), max(0, n_points - 1))
        else:
            edge_count = min(len(self.ops), n_points)

        for i in range(edge_count):
            p1 = points[i]
            p2 = points[i + 1] if self.is_chain else points[(i + 1) % n_points]
            self.edge_segments.append((i, p1, p2))
            self._draw_edge(painter, i, p1, p2)

        if self.is_chain and self.deleted_edge is not None:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(18, 30, f"已删除原边：{self.deleted_edge + 1}")

        count = min(len(points), len(self.values))
        for i in range(count):
            point = points[i]
            highlight = False
            if self.flash_active and self.flash_indices is not None and i in self.flash_indices:
                highlight = self.flash_on
            self._draw_vertex(painter, i, point, highlight)

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

    def _draw_vertex(self, painter: QPainter, vertex_index: int, point: QPointF, highlight: bool = False) -> None:
        radius = 30

        if highlight:
            pen_color = QColor("#ef4444")  # red
            brush_color = QColor(239, 68, 68, 220)
        else:
            pen_color = QColor("#1d4ed8")
            brush_color = QColor("#dbeafe")

        painter.setPen(QPen(pen_color, 3))
        painter.setBrush(QBrush(brush_color))
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
        if self.flash_active or self.trans_active:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._hit_edge(event.position())
            if edge is not None and self.on_edge_clicked:
                self.on_edge_clicked(edge)

    # ========= Flash API =========
    def start_flash_on_edge(self, edge_index: int, cycles: int = 10, interval_ms: int = 80,
                             finished: Optional[Callable[[], None]] = None) -> None:
        n = len(self.values)
        if n == 0:
            if finished:
                finished()
            return
        i = edge_index
        j = (edge_index + 1) % n if not self.is_chain else edge_index + 1
        if j >= n:
            j = n - 1
        self.flash_indices = (i, j)
        self.flash_active = True
        self.flash_on = True
        self.flash_ticks_left = max(1, cycles)
        self.flash_callback = finished
        if self.flash_timer is None:
            self.flash_timer = QTimer(self)
            self.flash_timer.timeout.connect(self._on_flash_tick)
        self.flash_timer.start(max(30, interval_ms))
        self.update()

    def _on_flash_tick(self) -> None:
        self.flash_on = not self.flash_on
        self.flash_ticks_left -= 1
        if self.flash_ticks_left <= 0:
            self.flash_timer.stop()
            self.flash_active = False
            self.flash_indices = None
            self.flash_on = False
            cb = self.flash_callback
            self.flash_callback = None
            self.update()
            if cb:
                cb()
            return
        self.update()

    # ========= Transition API =========
    def current_points(self) -> List[QPointF]:
        return self._layout_points()

    def start_transition_after_delete(self, old_points: List[QPointF], deleted_edge_index_before: int,
                                      duration_ms: int = 500, finished: Optional[Callable[[], None]] = None) -> None:
        # After delete, order starts from (edge+1) and count unchanged
        n = len(old_points)
        if n <= 0:
            if finished:
                finished()
            return
        start = (deleted_edge_index_before + 1) % n
        from_pts = [old_points[(start + k) % n] for k in range(n)]
        to_pts = self._layout_points()
        self.trans_callback = finished
        self._start_transition(from_pts, to_pts, duration_ms)

    def start_transition_after_merge(self, old_points: List[QPointF], merged_edge_index_before: int,
                                     duration_ms: int = 500) -> None:
        # After merge, count reduces by 1. Map new points from old points, with merged vertex starting at midpoint.
        old_n = len(old_points)
        new_n = len(self.values)
        if old_n == 0 or new_n == 0:
            return
        i = merged_edge_index_before
        j = (i + 1) if self.is_chain else (i + 1) % old_n
        if j >= old_n:
            j = old_n - 1
        from_pts: List[QPointF] = []
        for k in range(new_n):
            if k < i:
                from_pts.append(old_points[k])
            elif k == i:
                p1, p2 = old_points[i], old_points[j]
                from_pts.append(QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2))
            else:
                from_pts.append(old_points[k + 1])
        to_pts = self._layout_points()
        self._start_transition(from_pts, to_pts, duration_ms)

    def _start_transition(self, from_pts: List[QPointF], to_pts: List[QPointF], duration_ms: int) -> None:
        m = min(len(from_pts), len(to_pts))
        if m == 0:
            return
        self.trans_from = from_pts[:m]
        self.trans_to = to_pts[:m]
        self.trans_progress = 0.0
        self.trans_active = True
        if self.trans_timer is None:
            self.trans_timer = QTimer(self)
            self.trans_timer.timeout.connect(self._on_trans_tick)
        interval = 16
        self.trans_steps = max(1, duration_ms // interval)
        self.trans_step_count = 0
        self.trans_timer.start(interval)
        self.update()

    def _on_trans_tick(self) -> None:
        self.trans_step_count += 1
        self.trans_progress = min(1.0, self.trans_step_count / float(self.trans_steps))
        if self.trans_progress >= 1.0:
            self.trans_timer.stop()
            self.trans_active = False
            cb = self.trans_callback
            self.trans_callback = None
            self.update()
            if cb:
                cb()
            return
        self.update()

    # Public helper to start transition to current layout using custom start points
    def start_transition_to_current(self, from_pts: List[QPointF], duration_ms: int = 520, ease: str = "outback",
                                    finished: Optional[Callable[[], None]] = None) -> None:
        self.trans_ease = ease
        self.trans_callback = finished
        to_pts = self._layout_points()
        self._start_transition(from_pts, to_pts, duration_ms)

    # Collapse-only phase: move the two vertices of an edge to their midpoint (no state change)
    def start_collapse_two_vertices(self, old_points: List[QPointF], edge_index: int, duration_ms: int = 320,
                                    ease: str = "inout", finished: Optional[Callable[[], None]] = None) -> None:
        n = len(old_points)
        if n < 2:
            if finished:
                finished()
            return
        i = edge_index
        j = (edge_index + 1) % n if not self.is_chain else edge_index + 1
        if j >= n:
            j = n - 1
        p1, p2 = old_points[i], old_points[j]
        mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        to_pts = old_points[:]
        to_pts[i] = mid
        to_pts[j] = mid
        self._last_collapse_to = to_pts[:]
        self.trans_ease = ease
        self.trans_callback = finished
        self._start_transition(old_points, to_pts, duration_ms)

    def get_last_collapse_points(self) -> List[QPointF]:
        return self._last_collapse_to[:]

    # Easing functions
    def _ease(self, t: float) -> float:
        t = max(0.0, min(1.0, t))
        if self.trans_ease == "inout":
            return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
        if self.trans_ease == "outback":
            c1 = 1.70158
            c3 = c1 + 1
            # easeOutBack
            return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
        return t

    # Stop and reset any ongoing animations
    def stop_all_animations(self) -> None:
        if self.flash_timer is not None:
            self.flash_timer.stop()
        if self.trans_timer is not None:
            self.trans_timer.stop()
        self.flash_active = False
        self.flash_indices = None
        self.flash_on = False
        self.flash_ticks_left = 0
        self.trans_active = False
        self.trans_from = []
        self.trans_to = []
        self.trans_progress = 0.0
        self.trans_callback = None
        self.update()
