from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from lower_thirds.data_store import DataStore
from lower_thirds.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Lower Thirds")

    store = DataStore()
    window = MainWindow(store)
    window.show()

    return app.exec()
