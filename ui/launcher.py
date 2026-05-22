from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.main_window import OnlineClientWindow
from ui.single_window import SinglePlayerWindow


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多边形游戏 - 模式选择")
        self.resize(720, 420)

        self.single_window = None
        self.online_window = None

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(34, 34, 34, 34)
        root.setSpacing(22)

        title = QLabel("多边形游戏")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("请选择运行模式")
        subtitle.setObjectName("SubTitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        row = QHBoxLayout()
        row.setSpacing(20)

        single_card = self._make_card(
            "单人模式",
            "本地游玩，支持撤销/重做、历史步骤、动态规划最高分方案和自动演示。",
            "进入单人模式",
            self.open_single_mode,
        )
        online_card = self._make_card(
            "联机模式",
            "多人局域网对战。服务端统一同步状态，玩家轮流删边和合并。",
            "进入联机模式",
            self.open_online_mode,
        )

        row.addWidget(single_card)
        row.addWidget(online_card)
        root.addLayout(row)

        tip = QLabel("提示：联机模式需要先运行 run_server.py，再打开客户端加入房间。")
        tip.setObjectName("Tip")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(tip)

    def _make_card(self, title: str, desc: str, button_text: str, handler) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setObjectName("Desc")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label, 1)

        button = QPushButton(button_text)
        button.clicked.connect(handler)
        layout.addWidget(button)

        return card

    def open_single_mode(self) -> None:
        self.single_window = SinglePlayerWindow()
        self.single_window.show()

    def open_online_mode(self) -> None:
        self.online_window = OnlineClientWindow()
        self.online_window.show()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #e2e8f0;
                font-family: 'Microsoft YaHei', 'PingFang SC', Arial;
            }
            #Title {
                color: #0f172a;
                font-size: 30px;
                font-weight: 800;
            }
            #SubTitle {
                color: #475569;
                font-size: 16px;
            }
            #Card {
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 18px;
            }
            #CardTitle {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
            }
            #Desc {
                color: #475569;
                font-size: 13px;
                line-height: 1.6;
            }
            #Tip {
                color: #64748b;
                font-size: 12px;
            }
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 11px 14px;
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            """
        )
