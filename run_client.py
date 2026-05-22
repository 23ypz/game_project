import sys

from PyQt6.QtWidgets import QApplication

from ui.launcher import LauncherWindow


def main():
    app = QApplication(sys.argv)
    win = LauncherWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
