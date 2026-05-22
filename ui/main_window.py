import random
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
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

from common.dp_solver import current_state_best, solve_polygon_dp, solve_polygon_dp_with_one_change
from common.game_logic import validate_values_ops
from common.protocol import (
    MSG_CHANGE_EDGE,
    MSG_DELETE_EDGE,
    MSG_ERROR,
    MSG_MERGE_EDGE,
    MSG_START_GAME,
    MSG_STATE_UPDATE,
    MSG_WELCOME,
)
from network.client_thread import NetworkThread
from ui.polygon_canvas import PolygonCanvas


class OnlineClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多边形游戏 - 多人联机对战版")
        self.resize(1360, 780)

        self.net: Optional[NetworkThread] = None

        self.room_id = ""
        self.player_id = ""
        self.host_id = ""
        self.players: List[Dict[str, str]] = []
        self.values: List[int] = []
        self.ops: List[str] = []
        self.original_values: List[int] = []
        self.original_ops: List[str] = []
        self.edge_ids: List[int] = []
        self.is_chain = False
        self.deleted_edge: Optional[int] = None
        self.started = False
        self.game_over = False
        self.current_player_id: Optional[str] = None
        self.scores: Dict[str, int] = {}
        self.change_used: Dict[str, bool] = {}
        self.history: List[str] = []

        self._build_ui()
        self._apply_style()
        self._refresh_all()

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
        panel.setFixedWidth(350)

        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        title = QLabel("联机设置")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        layout.addWidget(QLabel("服务器地址"))
        self.server_edit = QLineEdit("ws://127.0.0.1:8765")
        layout.addWidget(self.server_edit)

        layout.addWidget(QLabel("昵称"))
        self.name_edit = QLineEdit(f"玩家{random.randint(1, 99)}")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("房间号：留空则创建新房间"))
        self.room_edit = QLineEdit("")
        layout.addWidget(self.room_edit)

        self.connect_btn = QPushButton("连接 / 创建房间")
        self.connect_btn.clicked.connect(self.connect_server)
        layout.addWidget(self.connect_btn)

        self.room_label = QLabel("房间：-\n身份：-")
        self.room_label.setObjectName("InfoLabel")
        layout.addWidget(self.room_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("Separator")
        layout.addWidget(sep)

        game_title = QLabel("房主设置游戏")
        game_title.setObjectName("PanelTitle")
        layout.addWidget(game_title)

        layout.addWidget(QLabel("顶点值，例如：3,-2,5,4"))
        self.values_edit = QLineEdit("3,-2,5,4")
        layout.addWidget(self.values_edit)

        layout.addWidget(QLabel("边运算符，例如：+,*,+,*"))
        self.ops_edit = QLineEdit("+,*,+,*")
        layout.addWidget(self.ops_edit)

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

        grid.addWidget(QLabel("随机 n"), 0, 0)
        grid.addWidget(self.n_spin, 0, 1)
        grid.addWidget(QLabel("最小值"), 1, 0)
        grid.addWidget(self.min_spin, 1, 1)
        grid.addWidget(QLabel("最大值"), 2, 0)
        grid.addWidget(self.max_spin, 2, 1)
        layout.addLayout(grid)

        self.random_btn = QPushButton("随机填入数据")
        self.random_btn.clicked.connect(self.random_fill)
        layout.addWidget(self.random_btn)

        self.start_btn = QPushButton("开始联机对战")
        self.start_btn.clicked.connect(self.start_game)
        layout.addWidget(self.start_btn)

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

        self.original_dp_btn = QPushButton("原始数据 DP 对比")
        self.original_dp_btn.clicked.connect(self.solve_original_compare)
        layout.addWidget(self.original_dp_btn)

        self.current_hint_btn = QPushButton("当前局面最高分 / 下一步提示")
        self.current_hint_btn.clicked.connect(self.solve_current_hint)
        layout.addWidget(self.current_hint_btn)

        rule = QLabel(
            "规则：当前玩家先删一条边；之后玩家轮流合并边。"
            "每人有一次改符号机会，只能在自己的回合使用，不消耗回合。"
        )
        rule.setWordWrap(True)
        rule.setObjectName("InfoLabel")
        layout.addWidget(rule)
        layout.addStretch()

        return panel

    def _center_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")

        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        self.status_label = QLabel("未连接")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

        self.canvas = PolygonCanvas()
        self.canvas.on_edge_clicked = self.on_edge_clicked
        layout.addWidget(self.canvas, 1)

        self.current_label = QLabel("当前顶点：-\n当前边：-")
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

        players_title = QLabel("玩家与分数")
        players_title.setObjectName("PanelTitle")
        layout.addWidget(players_title)

        self.players_table = QTableWidget(0, 4)
        self.players_table.setHorizontalHeaderLabels(["玩家", "身份", "分数", "改符号机会"])
        self.players_table.horizontalHeader().setStretchLastSection(True)
        self.players_table.verticalHeader().setVisible(False)
        self.players_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.players_table)

        dp_title = QLabel("DP 分析")
        dp_title.setObjectName("PanelTitle")
        layout.addWidget(dp_title)

        self.dp_text = QTextEdit()
        self.dp_text.setReadOnly(True)
        self.dp_text.setMinimumHeight(190)
        self.dp_text.setText("可点击左侧按钮查看原始数据 DP 对比或当前局面提示。")
        layout.addWidget(self.dp_text)

        history_title = QLabel("历史步骤")
        history_title.setObjectName("PanelTitle")
        layout.addWidget(history_title)

        self.history_table = QTableWidget(0, 2)
        self.history_table.setHorizontalHeaderLabels(["步数", "说明"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.history_table, 1)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(105)
        layout.addWidget(self.log_text)

        return panel

    def _apply_style(self) -> None:
        self.setStyleSheet(
            '''
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
            '''
        )

    def connect_server(self) -> None:
        if self.net is not None and self.net.isRunning():
            QMessageBox.information(self, "提示", "已经连接或正在连接服务器")
            return

        url = self.server_edit.text().strip()
        name = self.name_edit.text().strip() or "玩家"
        room_id = self.room_edit.text().strip()

        self.net = NetworkThread(url, name, room_id)
        self.net.message_received.connect(self.on_message)
        self.net.status_changed.connect(self.on_status)
        self.net.start()

        self.connect_btn.setEnabled(False)

    def send(self, data: Dict[str, Any]) -> None:
        if self.net is None:
            QMessageBox.warning(self, "未连接", "请先连接服务器")
            return

        self.net.send_json(data)

    def on_status(self, text: str) -> None:
        self.log_text.append(text)
        if text.startswith("连接结束"):
            self.connect_btn.setEnabled(True)

    def on_message(self, data: Dict[str, Any]) -> None:
        msg_type = data.get("type")

        if msg_type == MSG_WELCOME:
            self.room_id = data["room_id"]
            self.player_id = data["player_id"]
            self.host_id = data["host_id"]
            self.room_edit.setText(self.room_id)
            self.log_text.append(f"已进入房间 {self.room_id}，你的 ID 是 {self.player_id}")
            self._refresh_all()
            return

        if msg_type == MSG_ERROR:
            QMessageBox.warning(self, "服务器提示", data.get("message", "未知错误"))
            return

        if msg_type == MSG_STATE_UPDATE:
            self.room_id = data.get("room_id", self.room_id)
            self.host_id = data.get("host_id", self.host_id)
            self.players = data.get("players", [])
            self.values = data.get("values", [])
            self.ops = data.get("ops", [])
            self.original_values = data.get("original_values", [])
            self.original_ops = data.get("original_ops", [])
            self.edge_ids = data.get("edge_ids", [])
            self.is_chain = data.get("is_chain", False)
            self.deleted_edge = data.get("deleted_edge")
            self.started = data.get("started", False)
            self.game_over = data.get("game_over", False)
            self.current_player_id = data.get("current_player_id")
            self.scores = data.get("scores", {})
            self.change_used = data.get("change_used", {})
            self.history = data.get("history", [])
            self._refresh_all()
            return

    def random_fill(self) -> None:
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

    def start_game(self) -> None:
        if self.player_id != self.host_id:
            QMessageBox.warning(self, "权限不足", "只有房主可以开始游戏")
            return

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

        except Exception as e:
            QMessageBox.warning(self, "输入错误", str(e))
            return

        self.send({
            "type": MSG_START_GAME,
            "values": values,
            "ops": ops,
        })


    def solve_original_compare(self) -> None:
        if not self.original_values or not self.original_ops:
            QMessageBox.information(self, "提示", "游戏尚未开始，暂无原始数据")
            return

        try:
            normal = solve_polygon_dp(self.original_values, self.original_ops)
            changed = solve_polygon_dp_with_one_change(self.original_values, self.original_ops)

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

            self.dp_text.setText("\n".join(lines))

        except Exception as e:
            QMessageBox.warning(self, "DP 计算失败", str(e))

    def solve_current_hint(self) -> None:
        if not self.values:
            QMessageBox.information(self, "提示", "当前没有游戏数据")
            return

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

            self.dp_text.setText("\n".join(lines))

        except Exception as e:
            QMessageBox.warning(self, "当前局面 DP 计算失败", str(e))

    def change_edge_symbol(self) -> None:
        if not self.started:
            QMessageBox.information(self, "提示", "游戏尚未开始")
            return
        if self.game_over:
            QMessageBox.information(self, "提示", "游戏已经结束")
            return
        if self.current_player_id != self.player_id:
            QMessageBox.information(self, "提示", "还没有轮到你")
            return
        if self.change_used.get(self.player_id, False):
            QMessageBox.information(self, "提示", "你已经使用过改符号机会")
            return
        if not self.ops:
            QMessageBox.information(self, "提示", "当前没有可修改的边")
            return

        edge_index = self.change_edge_spin.value() - 1
        new_op = self.change_op_combo.currentText()

        self.send({
            "type": MSG_CHANGE_EDGE,
            "edge_index": edge_index,
            "new_op": new_op,
        })

    def on_edge_clicked(self, edge_index: int) -> None:
        if not self.started:
            QMessageBox.information(self, "提示", "游戏尚未开始")
            return

        if self.game_over:
            QMessageBox.information(self, "提示", "游戏已经结束")
            return

        if self.current_player_id != self.player_id:
            QMessageBox.information(self, "提示", "还没有轮到你")
            return

        if not self.is_chain:
            self.send({
                "type": MSG_DELETE_EDGE,
                "edge_index": edge_index,
            })
        else:
            self.send({
                "type": MSG_MERGE_EDGE,
                "edge_index": edge_index,
            })

    def _name_of(self, player_id: Optional[str]) -> str:
        if player_id is None:
            return "-"

        for player in self.players:
            if player["id"] == player_id:
                return player["name"]

        return player_id

    def _refresh_all(self) -> None:
        self.room_label.setText(
            f"房间：{self.room_id or '-'}\n"
            f"我的身份：{self.player_id or '-'} "
            f"{'(房主)' if self.player_id and self.player_id == self.host_id else ''}"
        )

        if self.game_over:
            best = max(self.scores.values()) if self.scores else 0
            winners = [
                self._name_of(pid)
                for pid, score in self.scores.items()
                if score == best
            ]
            self.status_label.setText(f"游戏结束。胜者：{', '.join(winners)}")
        elif not self.started:
            self.status_label.setText("等待房主开始游戏")
        else:
            action = "删除一条边" if not self.is_chain else "选择一条边合并"
            mine = "，轮到你操作" if self.current_player_id == self.player_id else ""
            self.status_label.setText(
                f"当前玩家：{self._name_of(self.current_player_id)}，请{action}{mine}"
            )

        self.canvas.set_state(
            self.values,
            self.ops,
            self.edge_ids,
            self.is_chain,
            self.deleted_edge,
        )

        edge_display = [
            f"{edge_id + 1}:{op}"
            for edge_id, op in zip(self.edge_ids, self.ops)
        ]

        chance = "已使用" if self.change_used.get(self.player_id, False) else "未使用"
        self.current_label.setText(
            f"当前顶点：{self.values if self.values else '-'}\n"
            f"当前边：{edge_display if edge_display else '-'}\n"
            f"我的改符号机会：{chance}"
        )

        self.start_btn.setEnabled(
            bool(self.player_id)
            and self.player_id == self.host_id
            and not self.started
        )
        self.random_btn.setEnabled(not self.started)

        can_change = (
            self.started
            and not self.game_over
            and self.current_player_id == self.player_id
            and not self.change_used.get(self.player_id, False)
            and bool(self.ops)
        )
        self.change_btn.setEnabled(can_change)
        self.original_dp_btn.setEnabled(self.started and bool(self.original_values))
        self.current_hint_btn.setEnabled(self.started and bool(self.values))
        if self.ops:
            self.change_edge_spin.setRange(1, len(self.ops))
        else:
            self.change_edge_spin.setRange(1, 1)

        self._refresh_players_table()
        self._refresh_history_table()

    def _refresh_players_table(self) -> None:
        self.players_table.setRowCount(len(self.players))

        for row, player in enumerate(self.players):
            pid = player["id"]
            roles = []

            if pid == self.host_id:
                roles.append("房主")
            if pid == self.current_player_id:
                roles.append("当前")
            if pid == self.player_id:
                roles.append("我")

            values = [
                player["name"],
                "/".join(roles) if roles else "玩家",
                str(self.scores.get(pid, 0)),
                "已使用" if self.change_used.get(pid, False) else "未使用",
            ]

            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.players_table.setItem(row, col, item)

        self.players_table.resizeColumnsToContents()

    def _refresh_history_table(self) -> None:
        self.history_table.setRowCount(len(self.history))

        for row, text in enumerate(self.history):
            step_item = QTableWidgetItem(str(row))
            step_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 0, step_item)
            self.history_table.setItem(row, 1, QTableWidgetItem(text))

        self.history_table.resizeColumnsToContents()
        if self.history:
            self.history_table.scrollToBottom()
