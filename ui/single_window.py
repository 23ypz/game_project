import copy
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from common.dp_solver import DPSolution, current_state_best, solve_polygon_dp, solve_polygon_dp_with_one_change
from common.game_logic import validate_values_ops
from ui.polygon_canvas import PolygonCanvas


@dataclass
class LocalSnapshot:
    values: List[int]
    ops: List[str]
    edge_ids: List[int]
    is_chain: bool
    deleted_edge: Optional[int]
    history: List[Dict[str, str]]
    change_used: bool


class SinglePlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多边形游戏 - 单人模式")
        self.resize(1280, 800)

        self.raw_values: List[int] = [3, -2, 5, 4]
        self.raw_ops: List[str] = ["+", "*", "+", "*"]

        self.values: List[int] = []
        self.ops: List[str] = []
        self.edge_ids: List[int] = []
        self.is_chain = False
        self.deleted_edge: Optional[int] = None
        self.history: List[Dict[str, str]] = []
        self.change_used = False

        self.undo_stack: List[LocalSnapshot] = []
        self.redo_stack: List[LocalSnapshot] = []

        self.dp_solution: Optional[DPSolution] = None
        self.demo_edges: List[int] = []
        self.demo_timer = QTimer(self)
        self.demo_timer.timeout.connect(self._demo_next_step)

        self._build_ui()
        self._apply_style()
        self.load_manual_data()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        root.addWidget(self._left_panel(), 0)
        root.addWidget(self._center_panel(), 1)
        root.addWidget(self._right_panel(), 0)

    def _left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(330)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        title = QLabel("单人模式")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        layout.addWidget(QLabel("顶点值，例如：3,-2,5,4"))
        self.values_edit = QLineEdit("3,-2,5,4")
        layout.addWidget(self.values_edit)

        layout.addWidget(QLabel("边运算符，例如：+,*,+,*"))
        self.ops_edit = QLineEdit("+,*,+,*")
        layout.addWidget(self.ops_edit)

        self.load_btn = QPushButton("载入手动数据")
        self.load_btn.clicked.connect(self.load_manual_data)
        layout.addWidget(self.load_btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setObjectName("Separator")
        layout.addWidget(sep1)

        random_title = QLabel("随机生成")
        random_title.setObjectName("PanelTitle")
        layout.addWidget(random_title)

        grid = QGridLayout()
        self.n_spin = QSpinBox()
        self.n_spin.setRange(3, 12)
        self.n_spin.setValue(5)

        self.min_spin = QSpinBox()
        self.min_spin.setRange(-99, 99)
        self.min_spin.setValue(-10)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(-99, 99)
        self.max_spin.setValue(10)

        grid.addWidget(QLabel("顶点数 n"), 0, 0)
        grid.addWidget(self.n_spin, 0, 1)
        grid.addWidget(QLabel("最小值"), 1, 0)
        grid.addWidget(self.min_spin, 1, 1)
        grid.addWidget(QLabel("最大值"), 2, 0)
        grid.addWidget(self.max_spin, 2, 1)
        layout.addLayout(grid)

        self.random_btn = QPushButton("随机生成并开始")
        self.random_btn.clicked.connect(self.random_data)
        layout.addWidget(self.random_btn)

        sep_change = QFrame()
        sep_change.setFrameShape(QFrame.Shape.HLine)
        sep_change.setObjectName("Separator")
        layout.addWidget(sep_change)

        change_title = QLabel("一次改边符号机会")
        change_title.setObjectName("PanelTitle")
        layout.addWidget(change_title)

        change_grid = QGridLayout()
        self.change_edge_spin = QSpinBox()
        self.change_edge_spin.setRange(1, 1)
        self.change_op_combo = QComboBox()
        self.change_op_combo.addItems(["+", "*"])
        change_grid.addWidget(QLabel("当前边序号"), 0, 0)
        change_grid.addWidget(self.change_edge_spin, 0, 1)
        change_grid.addWidget(QLabel("改为"), 1, 0)
        change_grid.addWidget(self.change_op_combo, 1, 1)
        layout.addLayout(change_grid)

        self.change_btn = QPushButton("使用一次改符号机会")
        self.change_btn.clicked.connect(self.change_edge_symbol)
        layout.addWidget(self.change_btn)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("Separator")
        layout.addWidget(sep2)

        action_title = QLabel("游戏操作")
        action_title.setObjectName("PanelTitle")
        layout.addWidget(action_title)

        row = QHBoxLayout()
        self.undo_btn = QPushButton("撤销")
        self.redo_btn = QPushButton("重做")
        self.undo_btn.clicked.connect(self.undo)
        self.redo_btn.clicked.connect(self.redo)
        row.addWidget(self.undo_btn)
        row.addWidget(self.redo_btn)
        layout.addLayout(row)

        self.reset_btn = QPushButton("重置当前数据")
        self.reset_btn.clicked.connect(self.reset_game)
        layout.addWidget(self.reset_btn)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setObjectName("Separator")
        layout.addWidget(sep3)

        dp_title = QLabel("动态规划")
        dp_title.setObjectName("PanelTitle")
        layout.addWidget(dp_title)

        self.solve_btn = QPushButton("原始数据 DP 对比")
        self.solve_btn.clicked.connect(self.solve_original_compare)
        layout.addWidget(self.solve_btn)

        self.current_hint_btn = QPushButton("当前局面最高分 / 下一步提示")
        self.current_hint_btn.clicked.connect(self.solve_current_hint)
        layout.addWidget(self.current_hint_btn)

        self.demo_btn = QPushButton("演示不修改 max")
        self.demo_btn.clicked.connect(self.start_demo)
        layout.addWidget(self.demo_btn)

        self.demo_change_btn = QPushButton("演示修改一次后的 max")
        self.demo_change_btn.clicked.connect(self.start_demo_with_change)
        layout.addWidget(self.demo_change_btn)

        help_text = QLabel("提示：第一次点击边是删边；之后点击边是合并。每局有一次改符号机会。")
        help_text.setWordWrap(True)
        help_text.setObjectName("InfoLabel")
        layout.addWidget(help_text)

        layout.addStretch()
        return panel

    def _center_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        self.status_label = QLabel("当前状态：-")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

        self.canvas = PolygonCanvas()
        self.canvas.on_edge_clicked = self.on_edge_clicked
        layout.addWidget(self.canvas, 1)

        self.current_label = QLabel("当前顶点：-\\n当前边：-")
        self.current_label.setWordWrap(True)
        self.current_label.setObjectName("InfoLabel")
        layout.addWidget(self.current_label)

        return panel

    def _right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(390)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        result_title = QLabel("DP 最高分方案")
        result_title.setObjectName("PanelTitle")
        layout.addWidget(result_title)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(200)
        self.result_text.setText("点击“计算最高分方案”查看结果。")
        layout.addWidget(self.result_text)

        history_title = QLabel("历史步骤")
        history_title.setObjectName("PanelTitle")
        layout.addWidget(history_title)

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["步数", "类型", "说明", "结果"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.history_table, 1)

        return panel

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #e2e8f0;
                font-family: 'Microsoft YaHei', 'PingFang SC', Arial;
            }
            #Panel {
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 16px;
            }
            #PanelTitle {
                color: #0f172a;
                font-size: 17px;
                font-weight: 700;
                padding: 4px 0 6px 0;
            }
            #StatusLabel {
                color: #0f172a;
                font-size: 18px;
                font-weight: 700;
            }
            #InfoLabel {
                color: #475569;
                font-size: 12px;
            }
            QLabel {
                color: #334155;
                font-size: 12px;
            }
            QLineEdit, QSpinBox, QComboBox, QTextEdit, QTableWidget {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 6px;
                color: #0f172a;
                selection-background-color: #bfdbfe;
            }
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 9px 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton:disabled {
                background: #94a3b8;
            }
            #Separator {
                color: #e2e8f0;
                background: #e2e8f0;
                max-height: 1px;
            }
            QHeaderView::section {
                background: #e0e7ff;
                color: #1e293b;
                padding: 6px;
                border: none;
                font-weight: 700;
            }
            """
        )

    def make_snapshot(self) -> LocalSnapshot:
        return LocalSnapshot(
            values=self.values[:],
            ops=self.ops[:],
            edge_ids=self.edge_ids[:],
            is_chain=self.is_chain,
            deleted_edge=self.deleted_edge,
            history=copy.deepcopy(self.history),
            change_used=self.change_used,
        )

    def restore_snapshot(self, snapshot: LocalSnapshot) -> None:
        self.values = snapshot.values[:]
        self.ops = snapshot.ops[:]
        self.edge_ids = snapshot.edge_ids[:]
        self.is_chain = snapshot.is_chain
        self.deleted_edge = snapshot.deleted_edge
        self.history = copy.deepcopy(snapshot.history)
        self.change_used = snapshot.change_used
        self.refresh_ui()

    def push_undo(self) -> None:
        self.undo_stack.append(self.make_snapshot())
        self.redo_stack.clear()

    def load_manual_data(self) -> None:
        try:
            values = [
                int(x.strip())
                for x in self.values_edit.text().replace("，", ",").split(",")
                if x.strip()
            ]
            ops = [
                x.strip()
                for x in self.ops_edit.text().replace("，", ",").split(",")
                if x.strip()
            ]

            err = validate_values_ops(values, ops)
            if err:
                raise ValueError(err)

            self.raw_values = values
            self.raw_ops = ops
            self.dp_solution = None
            self.result_text.setText("点击“计算最高分方案”查看结果。")
            self.reset_game()

        except Exception as e:
            QMessageBox.warning(self, "输入错误", str(e))

    def random_data(self) -> None:
        n = self.n_spin.value()
        lo = self.min_spin.value()
        hi = self.max_spin.value()

        if lo > hi:
            QMessageBox.warning(self, "输入错误", "最小值不能大于最大值")
            return

        values = [random.randint(lo, hi) for _ in range(n)]
        ops = [random.choice(["+", "*"]) for _ in range(n)]

        self.values_edit.setText(",".join(map(str, values)))
        self.ops_edit.setText(",".join(ops))
        self.load_manual_data()

    def reset_game(self) -> None:
        self.demo_timer.stop()
        self.values = self.raw_values[:]
        self.ops = self.raw_ops[:]
        self.edge_ids = list(range(len(self.raw_ops)))
        self.is_chain = False
        self.deleted_edge = None
        self.change_used = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.history = [
            {
                "type": "初始",
                "desc": f"顶点 {self.raw_values}，边 {self.raw_ops}",
                "result": "-",
            }
        ]
        self.refresh_ui()

    def undo(self) -> None:
        if not self.undo_stack:
            return
        self.demo_timer.stop()
        self.redo_stack.append(self.make_snapshot())
        self.restore_snapshot(self.undo_stack.pop())

    def redo(self) -> None:
        if not self.redo_stack:
            return
        self.demo_timer.stop()
        self.undo_stack.append(self.make_snapshot())
        self.restore_snapshot(self.redo_stack.pop())


    def change_edge_symbol(self) -> None:
        if self.change_used:
            QMessageBox.information(self, "提示", "你已经使用过一次改符号机会")
            return
        if not self.ops:
            QMessageBox.information(self, "提示", "当前没有可修改的边")
            return

        edge_index = self.change_edge_spin.value() - 1
        new_op = self.change_op_combo.currentText()

        if edge_index < 0 or edge_index >= len(self.ops):
            QMessageBox.warning(self, "操作错误", "边编号不合法")
            return

        old_op = self.ops[edge_index]
        if old_op == new_op:
            QMessageBox.warning(self, "操作错误", "新符号不能和原符号相同")
            return

        self.push_undo()
        original_edge = self.edge_ids[edge_index]
        self.ops[edge_index] = new_op
        self.change_used = True

        # 如果还没有删边，当前边就是原始多边形的边，同步到 raw_ops，后续 DP 会基于修改后的初始数据计算。
        if not self.is_chain:
            self.raw_ops[original_edge] = new_op
            self.ops_edit.setText(",".join(self.raw_ops))

        self.history.append({
            "type": "改符号",
            "desc": f"将原边 {original_edge + 1} 从 {old_op} 改为 {new_op}",
            "result": "-",
        })

        self.dp_solution = None
        self.refresh_ui()

    def _animate_delete(self, edge_index: int, source: str = "手动", record_undo: bool = True, on_done: Optional[Callable[[], None]] = None) -> None:
        self.canvas.stop_all_animations()
        old_points = self.canvas.current_points()
        def after_flash_delete():
            self.delete_edge(edge_index, record_undo=record_undo, source=source)
            self.canvas.start_transition_after_delete(old_points, edge_index, duration_ms=420, finished=on_done)
        self.canvas.start_flash_on_edge(edge_index, cycles=6, interval_ms=70, finished=after_flash_delete)

    def _animate_merge(self, edge_index: int, source: str = "手动", record_undo: bool = True, on_done: Optional[Callable[[], None]] = None) -> None:
        self.canvas.stop_all_animations()
        old_points = self.canvas.current_points()
        if edge_index < 0 or edge_index >= len(self.edge_ids):
            if on_done: on_done()
            return
        target_original_edge = self.edge_ids[edge_index]
        
        def after_collapse():
            if target_original_edge in self.edge_ids:
                current_index = self.edge_ids.index(target_original_edge)
            else:
                current_index = min(edge_index, max(0, len(self.ops) - 1))
            self.merge_edge(current_index, record_undo=record_undo, source=source)
            
            collapsed_pts = self.canvas.get_last_collapse_points()
            if len(collapsed_pts) > len(self.values):
                j = (current_index + 1) % len(collapsed_pts) if not self.is_chain else current_index + 1
                if j >= len(collapsed_pts):
                    j = len(collapsed_pts) - 1
                collapsed_pts.pop(j)
                
            self.canvas.start_transition_to_current(collapsed_pts, duration_ms=520, ease="outback", finished=on_done)
            
        def after_flash_merge():
            if target_original_edge in self.edge_ids:
                current_index = self.edge_ids.index(target_original_edge)
            else:
                current_index = edge_index
            self.canvas.start_collapse_two_vertices(old_points, current_index, duration_ms=280, ease="inout", finished=after_collapse)
            
        self.canvas.start_flash_on_edge(edge_index, cycles=6, interval_ms=70, finished=after_flash_merge)

    def on_edge_clicked(self, edge_index: int) -> None:
        self.demo_timer.stop()
        if not self.is_chain:
            self._animate_delete(edge_index, source="手动", record_undo=True)
        else:
            self._animate_merge(edge_index, source="手动", record_undo=True)

    def delete_edge(self, edge_index: int, record_undo: bool = True, source: str = "手动") -> None:
        if self.is_chain:
            return

        n = len(self.values)
        if edge_index < 0 or edge_index >= n:
            QMessageBox.warning(self, "操作错误", "边编号不合法")
            return

        if record_undo:
            self.push_undo()

        old_values = self.values[:]
        old_ops = self.ops[:]
        start = (edge_index + 1) % n

        self.values = [old_values[(start + i) % n] for i in range(n)]
        self.ops = [old_ops[(start + i) % n] for i in range(n - 1)]
        self.edge_ids = [(start + i) % n for i in range(n - 1)]
        self.is_chain = True
        self.deleted_edge = edge_index

        self.history.append({
            "type": f"{source}删边",
            "desc": f"删除原边 {edge_index + 1}，多边形转为链",
            "result": "-",
        })

        self.refresh_ui()

    def merge_edge(self, edge_index: int, record_undo: bool = True, source: str = "手动") -> None:
        if not self.is_chain:
            QMessageBox.information(self, "提示", "第一步需要先删除一条边")
            return

        if len(self.values) <= 1:
            return

        if edge_index < 0 or edge_index >= len(self.values) - 1:
            QMessageBox.warning(self, "操作错误", f"边编号不合法 {edge_index}")
            return

        if record_undo:
            self.push_undo()

        a = self.values[edge_index]
        b = self.values[edge_index + 1]
        op = self.ops[edge_index]
        result = a + b if op == "+" else a * b
        original_edge = self.edge_ids[edge_index]

        self.values = self.values[:edge_index] + [result] + self.values[edge_index + 2:]
        self.ops = self.ops[:edge_index] + self.ops[edge_index + 1:]
        self.edge_ids = self.edge_ids[:edge_index] + self.edge_ids[edge_index + 1:]

        self.history.append({
            "type": f"{source}合并",
            "desc": f"使用原边 {original_edge + 1}({op})：{a} {op} {b}",
            "result": str(result),
        })

        self.refresh_ui()

    def solve_dp(self) -> None:
        self.solve_original_compare()

    def solve_original_compare(self) -> None:
        try:
            normal = solve_polygon_dp(self.raw_values, self.raw_ops)
            changed = solve_polygon_dp_with_one_change(self.raw_values, self.raw_ops)

            lines = [
                "【原始数据：不修改符号 max】",
                f"最高得分：{normal.max_score}",
                f"第一步应删除的边：{normal.delete_edge + 1}",
                "最优表达式：",
                normal.expression,
                "演示过程：",
            ]

            for i, step in enumerate(normal.step_texts, 1):
                lines.append(f"{i}. {step}")

            lines += [
                "",
                "【原始数据：允许且必须修改一次符号 max】",
                f"最高得分：{changed.max_score}",
                f"建议修改原边：{changed.change_edge + 1}",
                f"修改方式：{changed.old_op} -> {changed.new_op}",
                f"修改后的边序列：{changed.after_change_ops}",
                f"修改后第一步应删除的边：{changed.base_solution.delete_edge + 1}",
                "最优表达式：",
                changed.base_solution.expression,
                "演示过程：",
            ]

            for i, step in enumerate(changed.base_solution.step_texts, 1):
                lines.append(f"{i}. {step}")

            self.dp_solution = normal
            self.result_text.setText("\n".join(lines))

        except Exception as e:
            QMessageBox.warning(self, "DP 计算失败", str(e))

    def solve_dp_with_change(self) -> None:
        self.solve_original_compare()

    def solve_current_hint(self) -> None:
        try:
            result = current_state_best(self.values, self.ops, self.edge_ids, self.is_chain)

            lines = [
                "【当前局面最高分 / 下一步提示】",
                f"当前最高可达到：{result['score']}",
                f"最优表达式：{result['expression']}",
                "",
            ]

            if result["action"] == "delete":
                lines.append(f"下一步建议：删除当前第 {result['edge_index'] + 1} 条边 / 原边 {result['edge_id'] + 1}")
            else:
                if result["edge_index"] is None:
                    lines.append("下一步建议：游戏已结束，无需操作")
                else:
                    lines.append(f"下一步建议：合并当前第 {result['edge_index'] + 1} 条边 / 原边 {result['edge_id'] + 1}")

            lines.append("")
            lines.append("后续最优演示过程：")
            for i, step in enumerate(result["steps"], 1):
                lines.append(f"{i}. {step}")

            self.result_text.setText("\n".join(lines))

        except Exception as e:
            QMessageBox.warning(self, "当前局面 DP 计算失败", str(e))

    def start_demo(self) -> None:
        if self.dp_solution is None:
            self.solve_dp()

        if self.dp_solution is None:
            return

        sol = self.dp_solution
        self.demo_timer.stop()
        self.canvas.stop_all_animations()
        self.reset_game()
        self.demo_edges = sol.merge_edge_ids[:]
        self.result_text.append("\\n开始自动演示最优方案...")
        
        self._animate_delete(sol.delete_edge, source="演示", record_undo=False, on_done=self._demo_next_step_animated)

    def start_demo_with_change(self) -> None:
        try:
            changed = solve_polygon_dp_with_one_change(self.raw_values, self.raw_ops)
            sol = changed.base_solution

            self.demo_timer.stop()
            self.canvas.stop_all_animations()
            self.reset_game()

            current_edge_index = self.edge_ids.index(changed.change_edge)
            self.change_edge_spin.setValue(current_edge_index + 1)
            self.change_op_combo.setCurrentText(changed.new_op)
            self.change_edge_symbol()

            self.demo_edges = sol.merge_edge_ids[:]
            self.result_text.setText(
                f"【演示修改一次后的 max】\n"
                f"修改原边 {changed.change_edge + 1}: {changed.old_op} -> {changed.new_op}\n"
                f"最高得分：{changed.max_score}\n"
                f"开始自动演示..."
            )
            
            self._animate_delete(sol.delete_edge, source="演示", record_undo=False, on_done=self._demo_next_step_animated)

        except Exception as e:
            QMessageBox.warning(self, "演示失败", str(e))

    def _demo_next_step_animated(self) -> None:
        # Give a small pause between steps to make the demo feel natural
        QTimer.singleShot(400, self._demo_process_next)

    def _demo_process_next(self) -> None:
        if not self.demo_edges:
            self.demo_timer.stop()
            if self.values:
                self.history.append({
                    "type": "演示结束",
                    "desc": "最优方案演示完成",
                    "result": str(self.values[0]),
                })
                self.refresh_ui()
            return

        target_original_edge = self.demo_edges.pop(0)
        if target_original_edge not in self.edge_ids:
            self.demo_timer.stop()
            QMessageBox.warning(self, "演示错误", f"找不到原边 {target_original_edge + 1}")
            return

        current_index = self.edge_ids.index(target_original_edge)
        self._animate_merge(current_index, source="演示", record_undo=False, on_done=self._demo_next_step_animated)

    def _demo_next_step(self) -> None:
        # Compatibility signature fallback, though now replaced by the animated version above
        self._demo_process_next()

    def refresh_ui(self) -> None:
        self.canvas.set_state(
            self.values,
            self.ops,
            self.edge_ids,
            self.is_chain,
            self.deleted_edge,
        )

        if not self.is_chain:
            self.status_label.setText("当前状态：等待删除一条边")
        elif len(self.values) == 1:
            self.status_label.setText(f"游戏结束：最终得分 = {self.values[0]}")
        else:
            self.status_label.setText("当前状态：请选择一条边合并两端点")

        edge_display = [
            f"{edge_id + 1}:{op}"
            for edge_id, op in zip(self.edge_ids, self.ops)
        ]

        chance = "已使用" if self.change_used else "未使用"
        self.current_label.setText(
            f"当前顶点：{self.values}\n"
            f"当前边：{edge_display if edge_display else '无'}\n"
            f"改符号机会：{chance}"
        )

        self.undo_btn.setEnabled(bool(self.undo_stack))
        self.redo_btn.setEnabled(bool(self.redo_stack))
        self.change_btn.setEnabled((not self.change_used) and bool(self.ops))
        if self.ops:
            self.change_edge_spin.setRange(1, len(self.ops))
        else:
            self.change_edge_spin.setRange(1, 1)
        self._refresh_history_table()

    def _refresh_history_table(self) -> None:
        self.history_table.setRowCount(len(self.history))

        for row, item in enumerate(self.history):
            values = [
                str(row),
                item.get("type", ""),
                item.get("desc", ""),
                item.get("result", ""),
            ]

            for col, text in enumerate(values):
                table_item = QTableWidgetItem(text)
                if col in [0, 3]:
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_table.setItem(row, col, table_item)

        self.history_table.resizeColumnsToContents()
        if self.history:
            self.history_table.scrollToBottom()
