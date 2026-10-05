import sys

from PySide6.QtWidgets import QApplication, QLabel


def main() -> int:
    app = QApplication(sys.argv)
    window = QLabel("Aion2 Crafting Calculator")
    window.setWindowTitle("Aion2 Crafting Calculator")
    window.resize(480, 240)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
