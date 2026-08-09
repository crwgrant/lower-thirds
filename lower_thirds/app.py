from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from lower_thirds.data_store import DataStore
from lower_thirds.main_window import MainWindow


def _icon_path() -> Path | None:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[1]

    icon = base / "assets" / "icon.png"
    return icon if icon.exists() else None


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Lower Thirds")

    icon_path = _icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    store = DataStore()
    window = MainWindow(store)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
